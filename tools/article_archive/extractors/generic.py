"""Generic web-article extraction.

Two tiers, cheapest first:

1. **defuddle over plain HTTP** — ``defuddle parse <url> --json --markdown``.
   No browser process, typically well under a second. Handles every
   server-rendered page, which is most of them.
2. **agent-browser re-fetch** — only when tier 1 returns too little text
   (client-rendered SPA, consent interstitial, soft 403). A real Chromium
   renders the page, the DOM is piped back into defuddle via stdin.

Tier 2 is skipped entirely unless tier 1 comes up short, so the common case
never pays for a browser launch.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from . import Article, ExtractionError
from .. import settings
from .sanitize import clean_markdown

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).resolve().parent.parent
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# agent-browser truncates page output by default; articles need the whole DOM.
_MAX_OUTPUT = "8000000"
_BROWSER_SESSION = "hermes_article_archive"


# --------------------------------------------------------------------------
# binary resolution
# --------------------------------------------------------------------------

def _node_bin() -> Optional[str]:
    managed = Path.home() / ".hermes" / "node" / "bin" / "node"
    if managed.exists():
        return str(managed)
    return shutil.which("node")


def _defuddle_bin() -> str:
    local = PLUGIN_DIR / "node_modules" / ".bin" / "defuddle"
    if local.exists():
        return str(local)
    found = shutil.which("defuddle")
    if found:
        return found
    raise ExtractionError(
        "defuddle CLI not found — run `npm install` in "
        f"{PLUGIN_DIR} to install it"
    )


def _agent_browser_bin() -> Optional[str]:
    try:
        from tools.browser_tool import _find_agent_browser

        found = _find_agent_browser()
        if found:
            return found
    except Exception:  # standalone CLI, or Hermes internals moved
        pass

    candidates = [
        Path.home() / ".hermes" / "hermes-agent" / "node_modules" / ".bin" / "agent-browser",
        Path.home() / ".hermes" / "node_modules" / ".bin" / "agent-browser",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return shutil.which("agent-browser")


def _child_env() -> Dict[str, str]:
    """Environment for the Node children.

    The Hermes keyring must not follow a Node process into npm dependency
    land, so only PATH-ish plumbing is forwarded (same rationale as
    ``tools/browser_tool._BROWSER_PASSTHROUGH_KEYS``).
    """
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SystemRoot", "TEMP", "TZ")
    env = {k: v for k, v in os.environ.items() if k in keep}
    node = _node_bin()
    if node:
        env["PATH"] = f"{Path(node).parent}{os.pathsep}{env.get('PATH', '')}"
    return env


def _run(cmd, *, timeout: int, stdin: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_child_env(),
        cwd=str(PLUGIN_DIR),
    )


# --------------------------------------------------------------------------
# defuddle
# --------------------------------------------------------------------------

def _parse_defuddle(source: str, *, stdin_html: Optional[str] = None) -> Dict[str, Any]:
    """Run ``defuddle parse`` and return its JSON payload."""
    cmd = [
        _defuddle_bin(),
        "parse",
        "-" if stdin_html is not None else source,
        "--json",
        "--markdown",
        "--user-agent",
        _UA,
    ]
    timeout = int(settings.get("defuddle_timeout"))
    try:
        proc = _run(cmd, timeout=timeout, stdin=stdin_html)
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError(f"defuddle timed out after {timeout}s") from exc

    out = (proc.stdout or "").strip()
    if not out or out.startswith("Error:"):
        detail = out or (proc.stderr or "").strip() or f"exit {proc.returncode}"
        raise ExtractionError(f"defuddle failed: {detail[:300]}")

    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"defuddle emitted non-JSON output: {out[:200]}") from exc
    if not isinstance(payload, dict):
        raise ExtractionError("defuddle emitted an unexpected JSON shape")
    return payload


# --------------------------------------------------------------------------
# agent-browser
# --------------------------------------------------------------------------

def _render_html(url: str) -> str:
    """Return the rendered DOM for *url*, or "" when the browser is unusable.

    Uses a named session so the Chromium stays warm between archives; the
    session is closed after each page so a stuck tab can't poison the next
    extraction.
    """
    binary = _agent_browser_bin()
    if not binary:
        logger.info("article-archive: agent-browser not available, skipping render tier")
        return ""

    base = [binary, "--session", _BROWSER_SESSION, "--max-output", _MAX_OUTPUT]
    timeout = int(settings.get("browser_timeout"))
    try:
        opened = _run(base + ["open", url], timeout=timeout)
        if opened.returncode != 0:
            logger.info(
                "article-archive: agent-browser open failed for %s: %s",
                url, (opened.stderr or opened.stdout or "").strip()[:200],
            )
            return ""
        got = _run(base + ["get", "html", "html"], timeout=timeout)
        html = (got.stdout or "").strip()
    except subprocess.TimeoutExpired:
        logger.info("article-archive: agent-browser timed out on %s", url)
        return ""
    finally:
        try:
            _run(base + ["close"], timeout=20)
        except Exception:
            pass

    if not html:
        return ""
    # `get html html` returns the innerHTML of <html>; defuddle wants a document.
    return f"<!DOCTYPE html><html>{html}</html>"


# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------

def _to_article(url: str, payload: Dict[str, Any], extractor: str) -> Article:
    content = str(payload.get("content") or "").strip()
    # Sanitize before the word count is taken: inline SVG markup would
    # otherwise inflate it and make a thin, client-rendered page look complete
    # enough to skip the browser tier.
    content, svgs, data_uris, tables = clean_markdown(content)

    extra: Dict[str, Any] = {
        "domain": payload.get("domain"),
        "language": payload.get("language"),
        "parseTime": payload.get("parseTime"),
    }
    if svgs:
        extra["svgs_omitted"] = svgs
    if data_uris:
        extra["data_uris_omitted"] = data_uris
    if tables:
        extra["tables_reformatted"] = tables

    return Article(
        url=url,
        kind="web",
        title=str(payload.get("title") or "").strip(),
        author=str(payload.get("author") or "").strip(),
        published=str(payload.get("published") or "").strip(),
        site=str(payload.get("site") or payload.get("domain") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        content_md=content,
        word_count=len(content.split()),
        image=str(payload.get("image") or "").strip(),
        extra=extra,
        extractor=extractor,
    )


def _thin(article: Optional[Article]) -> bool:
    if article is None or article.is_empty:
        return True
    return article.word_count < int(settings.get("min_word_count"))


def extract_rendered(url: str) -> Article:
    """Tier 2 on its own — always render, never try plain HTTP first.

    ``extract`` only reaches the browser when the cheap path comes up short.
    A reader who presses the button has already decided the cheap path was
    wrong, so this skips straight to the render.
    """
    html = _render_html(url)
    if not html:
        raise ExtractionError("브라우저로 페이지를 렌더링하지 못했습니다")
    return _to_article(url, _parse_defuddle(url, stdin_html=html), "defuddle:browser")


def extract(url: str) -> Article:
    direct: Optional[Article] = None
    direct_error: Optional[str] = None

    try:
        direct = _to_article(url, _parse_defuddle(url), "defuddle:http")
    except ExtractionError as exc:
        direct_error = str(exc)
        logger.info("article-archive: direct defuddle failed for %s: %s", url, exc)

    if not _thin(direct):
        return direct  # type: ignore[return-value]

    if not settings.get("browser_fallback"):
        if direct is not None:
            return direct
        raise ExtractionError(direct_error or f"could not extract {url}")

    html = _render_html(url)
    if html:
        try:
            rendered = _to_article(url, _parse_defuddle(url, stdin_html=html), "defuddle:browser")
            # Keep whichever tier actually found more of the article.
            if direct is None or rendered.word_count >= direct.word_count:
                return rendered
            return direct
        except ExtractionError as exc:
            logger.info("article-archive: rendered defuddle failed for %s: %s", url, exc)

    if direct is not None and not direct.is_empty:
        return direct
    raise ExtractionError(direct_error or f"could not extract {url}")
