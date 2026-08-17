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
    # Default visibility written into new files.
    #
    # raw stays private always — an external article's full text is not ours to
    # republish. Digests are our own writing and this repo exists to collect
    # them, so they default to public. Set one to private by hand and it stops
    # being pushed (see git_require_public); that is the escape hatch for a
    # summary that turns out to be too personal to share.
    #
    # A private fork flips digest_visibility back to private and turns
    # git_require_public off — there, nothing is published by being committed.
    "raw_visibility": "private",
    "digest_visibility": "public",

    # ---- git --------------------------------------------------------------
    # An archive that only exists on one laptop is half an archive, so every
    # pass commits what it wrote. Push integrates first: fetch, rebase, and
    # only then push — a diverged remote leaves the commit local rather than
    # forcing anything.
    "git_autocommit": True,
    "git_push": True,
    # In a public repo, committing a file *is* publishing it — more directly
    # than the web app would. So a document marked `visibility: private` is not
    # committed at all. Turn this off in a private fork, where the repo itself
    # is the boundary and everything belongs in it.
    "git_require_public": True,
    "git_remote": "origin",
    "git_branch": "",  # empty = whatever branch is checked out
    "git_timeout": 120,

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

    # ---- AI passes --------------------------------------------------------
    # Every AI pass is one agent run over files in a scratch directory. There
    # is no chunking and no token budget here: the prompt carries paths, the
    # agent reads and writes the documents itself.
    "agent_bin": "cline",
    "agent_provider": "cline",
    "agent_model": "cline:deepseek/deepseek-v4-flash",
    # Tried in order when the preferred route fails. "<provider>|<model>" pins
    # a provider; a bare value is a model id on agent_provider. The separator
    # is "|" because model ids contain both "/" and ":".
    "agent_fallbacks": [],
    # A full-article translation is minutes, not seconds — a 12k-character
    # article measured ~2m15s, and killing a long one halfway wastes the work
    # already done.
    "agent_timeout": 1800,

    # Refuse a source that cannot finish inside agent_timeout, rather than
    # spending the whole budget to fail at the end. Measured ~22s per 1,000
    # characters, so 80k is ~29 minutes — keep these two in step if either
    # moves.
    "translate_max_chars": 80000,

    # Per-pass model and reasoning effort. Empty model = agent_model.
    #   translate — mechanical work over a long document; effort buys latency
    #               more than quality.
    #   summary   — one run per article, and the piece that gets published.
    "translate_model": "",
    "translate_thinking": "low",
    "summary_model": "",
    "summary_thinking": "high",
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
