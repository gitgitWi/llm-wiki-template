"""LLM access with pluggable backends.

Three ways to get a completion, tried in this order unless ``llm_backend``
pins one:

1. **cline** — the ``cline`` CLI as an agent harness. Preferred: it carries a
   free tier, exposes reasoning effort as ``--thinking``, and takes a system
   prompt directly. Costs ~4.5k input tokens of agent scaffolding per call,
   which is why it is worth having only where that is free.
2. **hermes** — ``agent.auxiliary_client``, available when this runs on
   Hermes' interpreter. Keeps the auxiliary client's own provider ladder.
3. **openai** — any OpenAI-compatible ``/v1/chat/completions`` over stdlib
   urllib. Covers Ollama and OpenRouter, and needs no Hermes around.

The primary backend is tried with its own model; if it fails, ``llm_fallbacks``
is walked on whichever API backend is available. A refused route goes on a
10-minute cooldown, because one long article fans out into many chunk calls and
without the memo a dead provider is re-probed once per chunk.

Running an *agent* to transform text needs one precaution: cline is invoked
with ``--cwd`` pointed at a throwaway directory, so auto-approved tool use can
never reach the wiki.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional

from . import settings

logger = logging.getLogger(__name__)

_ROUTE_COOLDOWN = 600.0
_blocked_until: dict = {}

THINKING_LEVELS = ("none", "low", "medium", "high", "xhigh")


class LLMUnavailable(RuntimeError):
    """Raised when no backend could produce a completion."""


@dataclass(frozen=True)
class Route:
    backend: str
    provider: str = ""
    model: str = ""

    def label(self) -> str:
        return f"{self.backend}:{self.provider or 'auto'}/{self.model or 'auto'}"


@dataclass
class LLMResult:
    """A completion plus which route actually produced it.

    The route is not diagnostics — it gets written into the document's
    frontmatter, so a summary carries the model that wrote it.
    """

    content: str
    provider: str = ""
    model: str = ""
    backend: str = ""
    thinking: str = ""


# --------------------------------------------------------------------------
# backend availability
# --------------------------------------------------------------------------

def _cline_bin() -> Optional[str]:
    return shutil.which(str(settings.get("cline_bin") or "cline"))


def _hermes_available() -> bool:
    try:
        from agent.auxiliary_client import call_llm  # noqa: F401
    except Exception:
        return False
    return True


def _openai_available() -> bool:
    return bool(str(settings.get("openai_base_url") or "").strip())


def _api_backend() -> Optional[str]:
    """The non-agent backend to use for fallbacks."""
    if _hermes_available():
        return "hermes"
    if _openai_available():
        return "openai"
    return None


def backend_name() -> str:
    """Which backend a call will start on, for logs and ``--json`` output."""
    pinned = str(settings.get("llm_backend") or "auto").strip().lower()
    if pinned != "auto":
        return pinned
    if _cline_bin():
        return "cline"
    return _api_backend() or "none"


# --------------------------------------------------------------------------
# backends
# --------------------------------------------------------------------------

def _messages_to_prompt(messages: List[dict]) -> tuple[str, str]:
    """Split chat messages into ``(system, prompt)`` for a CLI that takes both."""
    system = "\n\n".join(
        str(m.get("content") or "") for m in messages if m.get("role") == "system"
    )
    prompt = "\n\n".join(
        str(m.get("content") or "") for m in messages if m.get("role") != "system"
    )
    return system.strip(), prompt.strip()


_CLINE_GUARD = (
    "This is a pure text transformation task. Do not read, write, or search "
    "files. Do not run commands. Do not use any tools. Reply with the result "
    "text only."
)


def _call_cline(
    messages: List[dict], route: Route, *, max_tokens: int, temperature: float, thinking: str
) -> str:
    binary = _cline_bin()
    if not binary:
        raise LLMUnavailable("cline is not on PATH")

    system, prompt = _messages_to_prompt(messages)
    system = f"{system}\n\n{_CLINE_GUARD}" if system else _CLINE_GUARD

    argv = [binary, "--json", "--auto-approve", "true", "-s", system]
    if route.provider:
        argv += ["-P", route.provider]
    if route.model:
        argv += ["-m", route.model]
    if thinking in THINKING_LEVELS:
        argv += ["--thinking", thinking]
    argv += [prompt]

    timeout = float(settings.get("cline_timeout"))
    # An auto-approving agent gets a throwaway cwd, never the wiki. Even a
    # well-behaved run should have nothing reachable to damage.
    scratch = tempfile.mkdtemp(prefix="article-archive-cline-")
    try:
        proc = subprocess.run(  # noqa: S603 - argv is built here, no shell
            argv,
            cwd=scratch,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMUnavailable(f"cline timed out after {timeout:.0f}s") from exc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return _parse_cline(proc.stdout or "", proc.stderr or "", proc.returncode)


def _parse_cline(stdout: str, stderr: str, returncode: int) -> str:
    """Pull the final answer out of cline's JSONL event stream."""
    text = ""
    finish = ""
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
        elif event.get("type") == "agent_event":
            inner = event.get("event") or {}
            if inner.get("type") == "done" and not text:
                text = str(inner.get("text") or "")
                finish = str(inner.get("reason") or "")

    if not text:
        detail = (stderr or stdout)[-400:].strip()
        raise LLMUnavailable(f"cline returned no text (exit {returncode}): {detail}")
    if finish and finish != "completed":
        logger.info("article-archive: cline finished as %s", finish)
    return text.strip()


def _call_hermes(
    messages: List[dict], route: Route, *, max_tokens: int, temperature: float, thinking: str
) -> str:
    from agent.auxiliary_client import call_llm

    response = call_llm(
        task=str(settings.get("aux_task")),
        provider=route.provider or None,
        model=route.model or None,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=float(settings.get("request_timeout")),
    )
    return (response.choices[0].message.content or "").strip()


def _call_openai(
    messages: List[dict], route: Route, *, max_tokens: int, temperature: float, thinking: str
) -> str:
    base = str(settings.get("openai_base_url") or "").rstrip("/")
    if not base:
        raise LLMUnavailable("openai_base_url is not configured")

    key = os.getenv(str(settings.get("openai_api_key_env")) or "", "").strip()
    payload = json.dumps({
        "model": route.model or route.provider,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(
        f"{base}/chat/completions", data=payload, headers=headers, method="POST"
    )
    with urllib.request.urlopen(  # noqa: S310 - configured host
        req, timeout=float(settings.get("request_timeout"))
    ) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return (body["choices"][0]["message"]["content"] or "").strip()


_BACKENDS = {"cline": _call_cline, "hermes": _call_hermes, "openai": _call_openai}


# --------------------------------------------------------------------------
# route ladder
# --------------------------------------------------------------------------

def _routes(model: str = "") -> List[Route]:
    """The primary route, then the API fallbacks.

    *model* overrides the primary route's model — that is how a pass picks a
    different model from the default without a second ladder.
    """
    routes: List[Route] = []
    primary = backend_name()

    if primary == "cline":
        routes.append(Route(
            "cline",
            str(settings.get("cline_provider") or ""),
            model or str(settings.get("cline_model") or ""),
        ))
    elif primary in ("hermes", "openai"):
        routes.append(Route(
            primary,
            str(settings.get("llm_provider") or ""),
            model or str(settings.get("llm_model") or ""),
        ))

    api = _api_backend()
    if api:
        for entry in settings.get("llm_fallbacks") or []:
            text = str(entry).strip()
            if not text:
                continue
            provider, _, name = text.partition("/")
            route = Route(api, provider.strip(), name.strip())
            if route not in routes:
                routes.append(route)
    return routes


def _blocked(route: Route) -> bool:
    return _blocked_until.get(route, 0.0) > time.monotonic()


def _block(route: Route) -> None:
    _blocked_until[route] = time.monotonic() + _ROUTE_COOLDOWN


def call(
    messages: List[dict],
    *,
    max_tokens: int,
    temperature: float = 0.2,
    thinking: str = "",
    model: str = "",
    validate: Optional[Callable[[str], bool]] = None,
) -> LLMResult:
    """Run *messages* through the first route that answers acceptably."""
    routes = _routes(model)
    if not routes:
        raise LLMUnavailable(
            "no LLM backend: install cline, run under Hermes' interpreter, or "
            "set ARTICLE_ARCHIVE_OPENAI_BASE_URL"
        )

    live = [r for r in routes if not _blocked(r)]
    if not live:  # everything on cooldown — better to try than to give up
        live = routes

    last: Optional[Exception] = None
    for route in live:
        invoke = _BACKENDS.get(route.backend)
        if invoke is None:
            continue
        try:
            content = invoke(
                messages,
                route,
                max_tokens=max_tokens,
                temperature=temperature,
                thinking=thinking,
            )
        except Exception as exc:
            last = exc
            _block(route)
            logger.info(
                "article-archive: route %s failed (cooling down %ds): %s",
                route.label(), int(_ROUTE_COOLDOWN), str(exc)[:200],
            )
            continue

        if not content:
            last = RuntimeError("empty completion")
            continue

        if validate is not None and not validate(content):
            last = RuntimeError("route returned unusable output")
            _block(route)
            logger.info(
                "article-archive: route %s returned unusable output, cooling down %ds",
                route.label(), int(_ROUTE_COOLDOWN),
            )
            continue

        return LLMResult(
            content=content,
            provider=route.provider,
            model=route.model,
            backend=route.backend,
            thinking=thinking if route.backend == "cline" else "",
        )

    raise LLMUnavailable(f"every route failed: {last}")


def pass_config(name: str) -> dict:
    """``{"model": ..., "thinking": ...}`` for one pass.

    Empty model means "the backend default" — most passes want that, and only
    the ones worth spending a better model on set it.
    """
    return {
        "model": str(settings.get(f"{name}_model") or ""),
        "thinking": str(settings.get(f"{name}_thinking") or ""),
    }
