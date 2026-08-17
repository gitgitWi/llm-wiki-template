"""LLM access with a pluggable backend.

The pipeline used to call ``agent.auxiliary_client.call_llm`` directly, which
tied every AI pass to running inside Hermes. Two backends are tried in order
of preference so the same code works in both places:

1. **hermes** — ``agent.auxiliary_client`` when it is importable, i.e. when
   Hermes invoked this tool with its own interpreter. Keeps the auxiliary
   client's provider ladder underneath this module's own.
2. **openai** — any OpenAI-compatible ``/v1/chat/completions`` endpoint over
   stdlib urllib. Covers Ollama, OpenRouter, and friends, and is what makes
   the tool usable from a plain `python3` with no Hermes around.

On top of whichever backend answers, a route ladder with a cooldown memo: a
long article fans out into many chunk calls, and without the memo a refused
route (403 subscription / 402 credit / 429 quota) would be re-probed once per
chunk.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from . import settings

logger = logging.getLogger(__name__)

_ROUTE_COOLDOWN = 600.0
_blocked_until: dict = {}


class LLMUnavailable(RuntimeError):
    """Raised when no backend could produce a completion."""


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


# --------------------------------------------------------------------------
# backends
# --------------------------------------------------------------------------

def _hermes_available() -> bool:
    try:
        from agent.auxiliary_client import call_llm  # noqa: F401
    except Exception:
        return False
    return True


def _call_hermes(
    messages: List[dict], provider: str, model: str, *, max_tokens: int, temperature: float
) -> str:
    from agent.auxiliary_client import call_llm

    response = call_llm(
        task=str(settings.get("aux_task")),
        provider=provider or None,
        model=model or None,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=float(settings.get("translate_timeout")),
    )
    return (response.choices[0].message.content or "").strip()


def _call_openai(
    messages: List[dict], provider: str, model: str, *, max_tokens: int, temperature: float
) -> str:
    base = str(settings.get("openai_base_url") or "").rstrip("/")
    if not base:
        raise LLMUnavailable("openai_base_url is not configured")

    key = os.getenv(str(settings.get("openai_api_key_env")) or "", "").strip()
    payload = json.dumps({
        "model": model or provider,
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
    timeout = float(settings.get("translate_timeout"))
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - configured host
        body = json.loads(resp.read().decode("utf-8"))
    return (body["choices"][0]["message"]["content"] or "").strip()


def backend_name() -> str:
    """Which backend this process will use, for logs and `--json` output."""
    if _hermes_available():
        return "hermes"
    if str(settings.get("openai_base_url") or "").strip():
        return "openai"
    return "none"


# --------------------------------------------------------------------------
# route ladder
# --------------------------------------------------------------------------

def _routes() -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = [
        (str(settings.get("llm_provider") or ""), str(settings.get("llm_model") or ""))
    ]
    for entry in settings.get("llm_fallbacks") or []:
        text = str(entry).strip()
        if not text:
            continue
        provider, _, model = text.partition("/")
        pairs.append((provider.strip(), model.strip()))

    out: List[Tuple[str, str]] = []
    for pair in pairs:
        if pair != ("", "") and pair not in out:
            out.append(pair)
    return out


def _blocked(route: Tuple[str, str]) -> bool:
    return _blocked_until.get(route, 0.0) > time.monotonic()


def _block(route: Tuple[str, str]) -> None:
    _blocked_until[route] = time.monotonic() + _ROUTE_COOLDOWN


def call(
    messages: List[dict],
    *,
    max_tokens: int,
    temperature: float = 0.2,
    validate: Optional[Callable[[str], bool]] = None,
) -> LLMResult:
    """Run *messages* through the first route that answers acceptably."""
    backend = backend_name()
    if backend == "none":
        raise LLMUnavailable(
            "no LLM backend: run under Hermes' interpreter, or set "
            "ARTICLE_ARCHIVE_OPENAI_BASE_URL"
        )
    invoke = _call_hermes if backend == "hermes" else _call_openai

    routes = _routes()
    live = [r for r in routes if not _blocked(r)]
    if not live:  # everything on cooldown — better to try than to give up
        live = routes

    last: Optional[Exception] = None
    for route in live:
        provider, model = route
        try:
            content = invoke(
                messages, provider, model, max_tokens=max_tokens, temperature=temperature
            )
        except Exception as exc:
            last = exc
            _block(route)
            logger.info(
                "article-archive: route %s/%s failed (cooling down %ds): %s",
                provider or "auto", model or "auto", int(_ROUTE_COOLDOWN), str(exc)[:200],
            )
            continue

        if not content:
            last = RuntimeError("empty completion")
            continue

        if validate is not None and not validate(content):
            last = RuntimeError("route returned unusable output")
            _block(route)
            logger.info(
                "article-archive: route %s/%s returned unusable output, cooling down %ds",
                provider or "auto", model or "auto", int(_ROUTE_COOLDOWN),
            )
            continue

        return LLMResult(content=content, provider=provider, model=model, backend=backend)

    raise LLMUnavailable(f"every route failed: {last}")
