"""Settings for the article-archive tool.

Defaults live here; ``config.json`` next to this file overrides them (it is
gitignored so a private fork can point at its own repo without conflicting
with template merges); ``ARTICLE_ARCHIVE_<KEY>`` environment variables override
that.

Deliberately carries no Discord keys — channel ids, button sets and inline
message budgets belong to whatever front end drives this tool, not to the
extraction pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

TOOL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TOOL_DIR / "config.json"

# tools/article_archive/ -> tools/ -> repo root
DEFAULT_WIKI_ROOT = TOOL_DIR.parent.parent

DEFAULTS: Dict[str, Any] = {
    # ---- output -----------------------------------------------------------
    # Repo the markdown lands in. Defaults to the repo this tool ships inside,
    # so a plain clone needs no configuration at all.
    "wiki_root": str(DEFAULT_WIKI_ROOT),
    "raw_dir": "raw/articles",
    "digest_dir": "wiki/digests",
    # How the tool reports where it put a file.
    #   "path"   -> repo-relative path (this template)
    #   "github" -> https://github.com/<repo>/blob/<branch>/<path> (private fork)
    "uri_mode": "path",
    "github_repo": "",
    "github_branch": "main",
    # Default visibility written into new files. private is the fail-safe;
    # an external article's full text is never public.
    "raw_visibility": "private",
    "digest_visibility": "private",

    # ---- extraction -------------------------------------------------------
    # Below this word count the page is assumed client-rendered and
    # agent-browser re-fetches it with a real Chromium.
    "min_word_count": 120,
    "browser_fallback": True,
    "defuddle_timeout": 60,
    "browser_timeout": 90,
    "fxtwitter_timeout": 20,
    "xcom_expand_threads": False,
    "xcom_max_thread_posts": 25,
    "x_article_browser": False,
    "x_browser_profile": "~/.hermes/cache/x-browser",
    "x_browser_binary": "",
    "x_article_timeout": 90,
    # Discord cannot render tables, so the Hermes plugin used to flatten them
    # into fixed-width grids. A markdown file renders pipe tables fine, and
    # flattening loses structure, so it is off here.
    "reformat_tables": False,

    # ---- LLM passes -------------------------------------------------------
    "summary_source_chars": 24000,
    "summary_max_tokens": 1200,
    "translate_max_chars": 120000,
    # Source characters per translation request. Chunking exists because a
    # response has an output ceiling — an agent harness does not lift that, it
    # just truncates silently, which is why passes.py checks for it.
    #
    # Sized for an agent/large-context backend: fewer, bigger calls keep
    # terminology consistent (each chunk is an independent session that cannot
    # see the others' word choices) and stop paying agent scaffolding per
    # chunk. Lower it for a small local model.
    "translate_chunk_chars": 12000,
    "translate_concurrency": 3,
    "request_timeout": 240,

    # Which backend answers. "auto" prefers the cline agent harness when it is
    # on PATH, then Hermes' auxiliary client, then an OpenAI-compatible URL.
    "llm_backend": "auto",

    # cline agent harness. Carries a free tier and exposes reasoning effort
    # directly, which is why it is the default. It is invoked in a throwaway
    # cwd — see llm.py — so auto-approved tool use cannot reach the wiki.
    "cline_bin": "cline",
    "cline_provider": "cline",
    "cline_model": "cline:deepseek/deepseek-v4-flash",
    "cline_timeout": 600,

    # Route for the hermes/openai backends when one of them is primary.
    "llm_provider": "copilot",
    "llm_model": "claude-haiku-4.5",
    # Tried in order after the primary backend fails, on whichever API backend
    # is available. "<provider>/<model>" — only the first slash separates, so
    # "openrouter/anthropic/claude-opus-4.8" works.
    "llm_fallbacks": [
        "copilot/claude-haiku-4.5",
        "copilot/gpt-4.1",
    ],

    # Per-pass model and reasoning effort. Empty model = the backend default.
    # Effort is applied on the cline backend (--thinking); the API backends
    # have no equivalent knob and ignore it.
    #   labels    — 3~6 tags from an opening slice. Nothing to reason about.
    #   translate — mechanical, and it fans out into one call per chunk, so
    #               effort here buys latency more than quality.
    #   summary   — one call per article and the piece that gets published.
    "labels_model": "",
    "labels_thinking": "none",
    "translate_model": "",
    "translate_thinking": "low",
    "summary_model": "",
    "summary_thinking": "high",

    # Auxiliary task key used when the Hermes backend is available.
    "aux_task": "article_archive_translate",
    # OpenAI-compatible HTTP backend. Works with Ollama, OpenRouter, or
    # anything speaking /v1/chat/completions.
    "openai_base_url": "",
    "openai_api_key_env": "ARTICLE_ARCHIVE_API_KEY",
}

_ENV_PREFIX = "ARTICLE_ARCHIVE_"
_lock = threading.Lock()
_cache: Dict[str, Any] | None = None
_cache_mtime: float = -1.0


def _mtime() -> float:
    try:
        return CONFIG_PATH.stat().st_mtime
    except OSError:
        return -1.0


def _coerce(default: Any, raw: str) -> Any:
    if isinstance(default, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        try:
            return int(raw)
        except ValueError:
            return default
    if isinstance(default, list):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return raw


def load(refresh: bool = False) -> Dict[str, Any]:
    """Effective settings (defaults < config.json < env)."""
    global _cache, _cache_mtime
    with _lock:
        current = _mtime()
        if _cache is not None and not refresh and current == _cache_mtime:
            return _cache

        merged = dict(DEFAULTS)
        try:
            if CONFIG_PATH.exists():
                stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    merged.update(stored)
        except Exception as exc:  # never let bad config break extraction
            logger.warning("article-archive: could not read config.json: %s", exc)

        for key, default in DEFAULTS.items():
            raw = os.getenv(_ENV_PREFIX + key.upper())
            if raw is not None:
                merged[key] = _coerce(default, raw)

        _cache = merged
        _cache_mtime = current
        return merged


def get(key: str) -> Any:
    return load().get(key, DEFAULTS.get(key))


def wiki_root() -> Path:
    return Path(str(get("wiki_root"))).expanduser().resolve()
