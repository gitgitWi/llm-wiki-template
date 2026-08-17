"""X Article extraction through a browser that holds an X session.

An X Article (``x.com/i/article/<id>``) is not a tweet: fxtwitter's endpoint
returns an empty body for one, and the page shows a login wall to logged-out
clients.  So unlike every other extractor here, this one needs credentials —
which is why it is **off by default** and why it keeps them in a browser
profile used for nothing else.

The browser is launched on demand and stopped again when the read finishes.
Nothing stays running between archives, and the profile keeps the session so
the login is a one-time step.  Every other X URL still goes through fxtwitter
in a fraction of a second; only ``/i/article/`` pays for this.

One-time setup::

    /Applications/Dia.app/Contents/MacOS/Dia \\
        --user-data-dir=~/.hermes/cache/x-browser --remote-debugging-port=9333

then sign in to x.com in that window and close it.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from . import Article, ExtractionError
from .. import settings

logger = logging.getLogger(__name__)

ARTICLE_RE = re.compile(r"^https?://(?:www\.)?x\.com/(?:i|[^/]+)/article/(\d+)", re.I)
_SCRIPT = Path(__file__).with_name("x_article.js")


def is_x_article(url: str) -> bool:
    return bool(ARTICLE_RE.match(url or ""))


def _browser_binary() -> Optional[str]:
    configured = str(settings.get("x_browser_binary") or "").strip()
    if configured:
        return configured if Path(configured).exists() else None
    for candidate in (
        "/Applications/Dia.app/Contents/MacOS/Dia",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ):
        if Path(candidate).exists():
            return candidate
    return shutil.which("chromium") or shutil.which("google-chrome")


def _profile_dir() -> Path:
    raw = str(settings.get("x_browser_profile") or "~/.hermes/cache/x-browser")
    return Path(os.path.expanduser(raw))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_cdp(port: int, deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/version", timeout=2
            ) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)
    return False


def _node_bin() -> Optional[str]:
    managed = Path.home() / ".hermes" / "node" / "bin" / "node"
    if managed.exists():
        return str(managed)
    return shutil.which("node")


def _node_modules() -> Optional[Path]:
    """Where the ``ws`` module lives.  It ships with agent-browser's tree."""
    for candidate in (
        Path.home() / ".hermes" / "hermes-agent" / "node_modules",
        Path(__file__).resolve().parent.parent / "node_modules",
    ):
        if (candidate / "ws").exists():
            return candidate
    return None


def fetch(url: str, *, force: bool = False) -> Article:
    """Launch the browser, read the article, stop the browser.

    ``force`` is what the action button passes: pressing it is the explicit
    consent that the setting otherwise stands in for.
    """
    if not force and not settings.get("x_article_browser"):
        raise ExtractionError(
            "X 아티클은 로그인이 필요합니다. "
            "settings.json의 x_article_browser를 켜면 전용 브라우저로 읽습니다: " + url
        )

    binary = _browser_binary()
    if not binary:
        raise ExtractionError("X 아티클용 브라우저를 찾을 수 없습니다 (settings의 x_browser_binary)")
    node = _node_bin()
    modules = _node_modules()
    if not node or not modules:
        raise ExtractionError("node 또는 ws 모듈을 찾을 수 없어 X 아티클을 읽을 수 없습니다")

    profile = _profile_dir()
    if not (profile / "Default" / "Cookies").exists():
        raise ExtractionError(
            f"X 전용 브라우저 프로필이 없습니다 ({profile}). README의 1회 로그인 절차를 먼저 실행하세요."
        )

    timeout = int(settings.get("x_article_timeout") or 90)
    port = _free_port()
    proc = subprocess.Popen(
        [
            binary,
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={port}",
            "--no-first-run", "--no-default-browser-check",
            "--headless=new",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        if not _wait_for_cdp(port, time.monotonic() + 25):
            raise ExtractionError("X 아티클용 브라우저가 기동하지 않았습니다")

        env = dict(os.environ)
        env["NODE_PATH"] = str(modules)
        result = subprocess.run(
            [node, str(_SCRIPT), str(port), url, str(timeout * 1000)],
            capture_output=True, text=True, timeout=timeout + 30,
            stdin=subprocess.DEVNULL, env=env, cwd=str(modules.parent),
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError("X 아티클 읽기 시간 초과") from exc
    finally:
        # The browser is only ever up for the duration of one read.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    out = (result.stdout or "").strip()
    if not out:
        raise ExtractionError(f"X 아티클 리더가 응답하지 않았습니다: {(result.stderr or '')[:160]}")
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"X 아티클 리더 출력이 JSON이 아닙니다: {out[:160]}") from exc
    if not payload.get("ok"):
        raise ExtractionError(f"X 아티클을 읽지 못했습니다: {payload.get('error')}")

    text = str(payload.get("text") or "").strip()
    if not text:
        raise ExtractionError("X 아티클 본문이 비어 있습니다")

    title = str(payload.get("title") or "X Article").strip()
    return Article(
        url=str(payload.get("url") or url),
        kind="x-article",
        title=title,
        author="",
        published="",
        site="X",
        description=text[:280],
        content_md=text,
        word_count=len(text.split()),
        image="",
        media=[],
        extra={"x_article": True},
        extractor="x-article-browser",
    )
