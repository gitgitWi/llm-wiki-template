"""Run one agent task in a disposable workspace.

The AI passes used to work by stuffing article text into a prompt, which meant
chunking it to fit an output ceiling, which meant one request per chunk — each
an independent session that could not see the others' word choices. This
replaces all of that with: put the source in a scratch directory, tell the
agent to read it and write its answer next to it, read the answer back.

The prompt carries paths, not content. The agent handles a long document the
way a person would, and there is nothing to split or stitch.

Isolation is the reason the scratch copy exists rather than pointing the agent
at the wiki. ``--auto-approve`` has to be on for a non-interactive run, so the
agent gets a directory containing exactly what it needs and nothing it could
damage. It never sees the repo.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import settings

logger = logging.getLogger(__name__)

_ROUTE_COOLDOWN = 600.0
_blocked_until: dict = {}

THINKING_LEVELS = ("none", "low", "medium", "high", "xhigh")


class AgentUnavailable(RuntimeError):
    """Raised when no route could complete the task."""


@dataclass(frozen=True)
class Route:
    provider: str = ""
    model: str = ""

    def label(self) -> str:
        return f"{self.provider or 'auto'}/{self.model or 'auto'}"


@dataclass
class AgentResult:
    """Which route did the work, and what it said about doing it.

    Written into the document's frontmatter — a summary should carry the model
    that wrote it.
    """

    provider: str = ""
    model: str = ""
    backend: str = "cline"
    thinking: str = ""
    iterations: int = 0
    outputs: Dict[str, str] = field(default_factory=dict)


def binary() -> Optional[str]:
    return shutil.which(str(settings.get("agent_bin") or "cline"))


def available() -> bool:
    return binary() is not None


def routes() -> List[Route]:
    """Preferred route, then fallbacks. All run through the same agent CLI."""
    out: List[Route] = []
    entries = [str(settings.get("agent_model") or "")]
    entries += [str(e) for e in (settings.get("agent_fallbacks") or [])]

    default_provider = str(settings.get("agent_provider") or "")
    for entry in entries:
        text = entry.strip()
        if not text:
            continue
        # "<provider>|<model>" pins a provider; a bare value is a model id on
        # the default provider. Model ids contain slashes and colons, so those
        # cannot be the separator.
        provider, sep, model = text.partition("|")
        route = (
            Route(provider.strip(), model.strip())
            if sep
            else Route(default_provider, text)
        )
        if route not in out:
            out.append(route)
    return out


def _blocked(route: Route) -> bool:
    return _blocked_until.get(route, 0.0) > time.monotonic()


def _block(route: Route) -> None:
    _blocked_until[route] = time.monotonic() + _ROUTE_COOLDOWN


def _parse(stdout: str) -> tuple[str, str, int]:
    """``(final_text, finish_reason, iterations)`` from cline's JSONL stream."""
    text = finish = ""
    iterations = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "run_result":
            text = str(event.get("text") or "")
            finish = str(event.get("finishReason") or "")
            iterations = int(event.get("iterations") or 0)
    return text, finish, iterations


def run(
    prompt: str,
    *,
    inputs: Dict[str, str],
    outputs: List[str],
    optional_outputs: Optional[List[str]] = None,
    system: str = "",
    thinking: str = "",
    model: str = "",
    validate: Optional[Callable[[Dict[str, str]], bool]] = None,
) -> AgentResult:
    """Run *prompt* in a scratch dir seeded with *inputs*; return *outputs*.

    ``inputs`` and ``outputs`` are file names relative to that directory — the
    prompt refers to them by those names, so it stays short no matter how long
    the article is.

    A missing entry in ``outputs`` fails the route. Put anything the run can
    usefully skip in ``optional_outputs`` instead — throwing away a good
    summary because a side file was not written would be its own bug.
    """
    binary_path = binary()
    if not binary_path:
        raise AgentUnavailable(
            f"{settings.get('agent_bin')} is not on PATH — the AI passes need it"
        )

    ladder = routes()
    if model:
        ladder = [Route(str(settings.get("agent_provider") or ""), model)] + ladder
    live = [r for r in ladder if not _blocked(r)]
    if not live:  # everything on cooldown — better to try than to give up
        live = ladder

    timeout = float(settings.get("agent_timeout"))
    last: Optional[Exception] = None

    for route in live:
        workspace = Path(tempfile.mkdtemp(prefix="article-archive-"))
        try:
            for name, body in inputs.items():
                (workspace / name).write_text(body, encoding="utf-8")

            argv = [binary_path, "--json", "--auto-approve", "true"]
            if system:
                argv += ["-s", system]
            if route.provider:
                argv += ["-P", route.provider]
            if route.model:
                argv += ["-m", route.model]
            if thinking in THINKING_LEVELS:
                argv += ["--thinking", thinking]
            argv += [prompt]

            try:
                proc = subprocess.run(  # noqa: S603 - argv built here, no shell
                    argv,
                    cwd=str(workspace),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired as exc:
                last = exc
                _block(route)
                logger.info(
                    "article-archive: route %s timed out after %.0fs", route.label(), timeout
                )
                continue

            text, finish, iterations = _parse(proc.stdout or "")
            produced: Dict[str, str] = {}
            missing = []
            for name in [*outputs, *(optional_outputs or [])]:
                path = workspace / name
                if path.is_file():
                    produced[name] = path.read_text(encoding="utf-8")
                elif name in outputs:
                    missing.append(name)

            if missing:
                last = RuntimeError(f"agent did not write {', '.join(missing)}")
                _block(route)
                logger.info(
                    "article-archive: route %s wrote no %s (finish=%s, exit=%s): %s",
                    route.label(), ", ".join(missing), finish, proc.returncode,
                    (text or (proc.stderr or ""))[-300:],
                )
                continue

            if validate is not None and not validate(produced):
                last = RuntimeError("agent output failed validation")
                _block(route)
                logger.info(
                    "article-archive: route %s produced unusable output", route.label()
                )
                continue

            return AgentResult(
                provider=route.provider,
                model=route.model,
                thinking=thinking,
                iterations=iterations,
                outputs=produced,
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    raise AgentUnavailable(f"every route failed: {last}")


def pass_config(name: str) -> dict:
    """``{"model": ..., "thinking": ...}`` for one pass."""
    return {
        "model": str(settings.get(f"{name}_model") or ""),
        "thinking": str(settings.get(f"{name}_thinking") or ""),
    }
