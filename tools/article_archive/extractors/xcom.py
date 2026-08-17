"""X / Twitter extraction via the fxtwitter API, with a DOM tier for threads.

fxtwitter (``api.fxtwitter.com``) is a keyless public JSON mirror of the embed
data — post text, author, timestamps, engagement counts and media. It is one
HTTP request and it returns the **full** text even for long-form posts
(``is_note_tweet``), which is why it stays tier 1: a browser render of the same
post costs ~8 seconds and, measured, carries *less* text (x.com's schema.org
``articleBody`` stops at 280 characters).

What fxtwitter cannot do is look **forward**. It exposes ``replying_to_status``
— the parent of a reply — but nothing about a self-reply chain, so archiving
the head of a six-post thread through it alone saves one post and drops five.
That gap is what the optional browser tier fills: one agent-browser visit reads
the chain's ids out of the status page, then each member's text comes back over
fxtwitter. The browser discovers structure; the API supplies content.

Only the public post URL leaves the machine.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from . import Article, ExtractionError
from .. import settings
from .generic import _agent_browser_bin, _run as _run_cmd

logger = logging.getLogger(__name__)

_API = "https://api.fxtwitter.com"
_TCO_RE = re.compile(r"https://t\.co/\w+")
# x.com/i/article/<id> — X's long-form Article, a different content type from a
# tweet.  fxtwitter's tweet endpoint returns an empty body for it, and the page
# itself is behind a login wall for logged-out clients, so there is nothing to
# archive and saying so beats an empty post.
_X_ARTICLE_RE = re.compile(r"^https?://(?:www\.)?x\.com/i/article/\d+", re.I)
_UA = "Mozilla/5.0 (compatible; hermes-article-archive/1.0)"
_STATUS_RE = re.compile(r"/(?:i/web/)?status(?:es)?/(\d+)")


def _status_id(url: str) -> Optional[str]:
    m = _STATUS_RE.search(url)
    return m.group(1) if m else None


# --------------------------------------------------------------------------
# thread discovery (agent-browser)
# --------------------------------------------------------------------------

_BROWSER_SESSION = "hermes_article_archive_x"

# Thread continuations carry no schema.org microdata — only the page's focal
# post does — so the chain has to be read off the status links.  Returning the
# article index with each one is what makes the walk safe: a genuine
# continuation sits in the articles immediately after the focal post, while
# replies from other people start a different author's run.
_THREAD_JS = r"""
(() => {
  const rows = [];
  document.querySelectorAll('article').forEach((a, i) => {
    const href = [...a.querySelectorAll('a[href*="/status/"]')]
      .map((x) => x.getAttribute('href') || '')
      .find((h) => /^\/[^/]+\/status\/\d+$/.test(h)) || '';
    const m = href.match(/^\/([^/]+)\/status\/(\d+)$/);
    if (m) rows.push({ i: i, handle: m[1], id: m[2] });
  });
  return JSON.stringify({ rows: rows, url: location.href });
})()
"""


def _thread_member_ids(url: str, status_id: str, handle: str, timeout: int) -> list:
    """Ids of the self-reply chain that follows *status_id*, in order.

    Returns [] for anything that is not a thread, and for any page the browser
    could not actually reach — x.com is a single-page app, so ``open`` can
    return while the previous route is still mounted and reading that would
    attribute another page's links to this post.
    """
    binary = _agent_browser_bin()
    if not binary:
        logger.info("article-archive: agent-browser unavailable, skipping X thread expansion")
        return []

    base = [binary, "--session", _BROWSER_SESSION]
    try:
        opened = _run_cmd(base + ["open", url], timeout=timeout)
        if opened.returncode != 0:
            return []
        _run_cmd(base + ["wait", "3500"], timeout=timeout)
        got = _run_cmd(base + ["eval", _THREAD_JS], timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.info("article-archive: agent-browser timed out reading the X thread at %s", url)
        return []
    finally:
        try:
            _run_cmd(base + ["close"], timeout=20)
        except Exception:  # noqa: BLE001 - closing is best effort
            pass

    payload = (got.stdout or "").strip()
    if not payload:
        return []
    try:
        data = json.loads(payload)
        if isinstance(data, str):
            data = json.loads(data)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict) or status_id not in str(data.get("url") or ""):
        return []

    rows = [r for r in (data.get("rows") or []) if isinstance(r, dict)]
    focal = next((r for r in rows if str(r.get("id")) == status_id), None)
    if focal is None:
        return []

    out = []
    for row in rows:
        if int(row.get("i", -1)) <= int(focal.get("i", 0)):
            continue
        # The chain ends at the first article by somebody else: from there on
        # the page is showing replies, not the thread.
        if str(row.get("handle", "")).lower() != handle.lower():
            break
        member = str(row.get("id") or "")
        if member and member != status_id and member not in out:
            out.append(member)
    return out


# fxtwitter reports why it refused in the JSON body, which is far more useful
# to a reader than the bare status code.
_REASONS = {
    "PRIVATE_TWEET": "비공개 계정이거나 보호된 게시물입니다",
    "NOT_FOUND": "삭제되었거나 존재하지 않는 게시물입니다",
    "API_FAIL": "X API가 일시적으로 응답하지 않습니다",
}


def _explain(code: int, body: str) -> str:
    reason = ""
    try:
        payload = json.loads(body)
        reason = str(payload.get("message") or "")
    except (json.JSONDecodeError, AttributeError):
        pass
    friendly = _REASONS.get(reason)
    if friendly:
        return friendly
    return f"X 게시물을 가져오지 못했습니다 (HTTP {code}{f' {reason}' if reason else ''})"


def _fetch(status_id: str, timeout: int) -> Dict[str, Any]:
    req = urllib.request.Request(
        f"{_API}/status/{status_id}",
        headers={"User-Agent": _UA, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed host
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    if not isinstance(payload, dict) or payload.get("code") != 200:
        raise ExtractionError(
            f"fxtwitter returned {payload.get('code')}: {payload.get('message')}"
        )
    tweet = payload.get("tweet")
    if not isinstance(tweet, dict):
        raise ExtractionError("fxtwitter response had no tweet object")
    return tweet


def _iso(tweet: Dict[str, Any]) -> str:
    ts = tweet.get("created_timestamp")
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return str(tweet.get("created_at") or "")


def _media_urls(tweet: Dict[str, Any]) -> list:
    media = tweet.get("media")
    if not isinstance(media, dict):
        return []
    out = []
    for item in media.get("all") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("thumbnail_url")
        if url:
            out.append(str(url))
    return out


def _outbound_url(tweet: Dict[str, Any], timeout: int) -> str:
    """The single link a text-less post carries, resolved past t.co.

    A post that is nothing but a link has ``text == ""`` — the link lives only
    in ``raw_text``.  fxtwitter usually expands links in ``facets``, but not
    always (measured: a post linking an X Article had ``facets: []``), so fall
    back to following the redirect.  When the link is an X Article, fxtwitter
    also surfaces it under ``tweet["article"]["id"]`` even when the t.co
    redirect is dead, so that is checked first.
    """
    # X Article quoted via the article field (most reliable when present).
    article = tweet.get("article")
    if isinstance(article, dict):
        art_id = str(article.get("id") or "").strip()
        if art_id and art_id.isdigit():
            return f"https://x.com/i/article/{art_id}"

    raw = tweet.get("raw_text")
    if isinstance(raw, dict):
        for facet in raw.get("facets") or []:
            if isinstance(facet, dict) and facet.get("type") == "url":
                target = str(facet.get("replacement") or facet.get("original") or "")
                if target and not _TCO_RE.fullmatch(target):
                    return target
        text = str(raw.get("text") or "")
    else:
        text = ""

    match = _TCO_RE.search(text)
    if not match:
        return ""
    try:
        req = urllib.request.Request(match.group(0), method="HEAD", headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed host
            return str(resp.url or "")
    except (urllib.error.URLError, OSError) as exc:
        logger.info("article-archive: could not expand %s: %s", match.group(0), exc)
        return ""


def _render_body(tweet: Dict[str, Any]) -> str:
    """Post text plus the quoted/replied-to context, as markdown."""
    parts = []

    parent = tweet.get("replying_to_status")
    parent_handle = tweet.get("replying_to")
    if parent_handle:
        parts.append(f"↩︎ *reply to @{parent_handle}*")
        if isinstance(parent, dict) and parent.get("text"):
            parts.append(f"> {str(parent['text']).strip()}")

    text = (tweet.get("text") or "").strip()
    if text:
        parts.append(text)

    quote = tweet.get("quote")
    if isinstance(quote, dict):
        q_author = (quote.get("author") or {}).get("screen_name", "")
        q_text = (quote.get("text") or "").strip()
        if q_text:
            header = f"**Quoted @{q_author}**" if q_author else "**Quoted post**"
            quoted = "\n".join(f"> {line}" for line in q_text.splitlines())
            parts.append(f"{header}\n{quoted}")

    note = tweet.get("community_note")
    if isinstance(note, dict) and note.get("text"):
        parts.append(f"**Community Note**\n> {str(note['text']).strip()}")

    return "\n\n".join(parts)


def _render_thread(members: list) -> str:
    """Continuation posts, appended under the head as one numbered run."""
    if not members:
        return ""
    parts = ["---", f"**🧵 스레드 ({len(members) + 1}개)**"]
    for index, tweet in enumerate(members, start=2):
        text = (tweet.get("text") or "").strip()
        if text:
            parts.append(f"**{index}.** {text}")
    return "\n\n".join(parts)


def extract(url: str) -> Article:
    status_id = _status_id(url)
    if not status_id:
        raise ExtractionError(f"could not find a status id in {url}")

    timeout = int(settings.get("fxtwitter_timeout"))
    try:
        tweet = _fetch(status_id, timeout)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        raise ExtractionError(_explain(exc.code, body)) from exc
    except urllib.error.URLError as exc:
        raise ExtractionError(f"fxtwitter unreachable: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise ExtractionError(f"fxtwitter request failed: {exc}") from exc

    author = tweet.get("author") or {}
    handle = str(author.get("screen_name") or "")
    name = str(author.get("name") or handle)
    body = _render_body(tweet)

    # A post with no words of its own is a link the author is passing along.
    # Archiving an empty shell helps nobody — archive what they linked to.
    if not body.strip():
        target = _outbound_url(tweet, timeout)
        if _X_ARTICLE_RE.match(target or ""):
            # The article's own title (from fxtwitter's article field) makes a
            # far better heading than a bare link.
            art_meta = tweet.get("article") or {}
            art_title = str(art_meta.get("title") or "").strip()
            heading = art_title or (f"@{handle}" if handle else "X Article")
            # An X Article quote: do NOT pull the whole article into the thread
            # on archive. A long article (a16z-style) would flood the channel
            # with 10-20+ messages. Stash the article URL and let the reader
            # fetch it on demand through the dedicated "X Article 전문 보기"
            # button instead.
            return Article(
                url=str(tweet.get("url") or url),
                kind="x",
                title=f"X Article: {heading}",
                author=f"{name} (@{handle})" if handle else name,
                published=_iso(tweet),
                site="X",
                description=f"X Article: {target}",
                content_md=(
                    f"**{heading}**\n\n"
                    f"이 트윗은 X Article을 인용합니다:\n<{target}>\n\n"
                    f"전체 내용은 **'X Article 전문 보기'** 버튼으로 읽을 수 있습니다."
                ),
                word_count=0,
                image=str((author.get("avatar_url") or "")),
                media=[],
                extra={
                    "x_article_url": target,
                    "is_x_article_quote": True,
                    "likes": tweet.get("likes"),
                    "retweets": tweet.get("retweets"),
                    "replies": tweet.get("replies"),
                    "quotes": tweet.get("quotes"),
                    "bookmarks": tweet.get("bookmarks"),
                    "views": tweet.get("views"),
                    "lang": tweet.get("lang"),
                },
                extractor="fxtwitter+x-article-quote",
            )
        if target:
            from . import generic

            logger.info("article-archive: %s carries no text, following %s", url, target)
            linked = generic.extract(target)
            linked.extra = dict(linked.extra or {})
            linked.extra["via_x_post"] = str(tweet.get("url") or url)
            linked.extra["via_x_author"] = f"@{handle}" if handle else name
            linked.extractor = f"{linked.extractor}+via-x"
            return linked
        raise ExtractionError("본문도 링크도 없는 게시물입니다 (이미지/영상 전용일 수 있습니다)")

    # Optional second tier.  fxtwitter has no forward-thread field, so the
    # chain is discovered in the DOM and then fetched back over fxtwitter —
    # one browser visit total, not one per post.  Off by default because that
    # visit costs several seconds on every X archive, thread or not.
    members: list = []
    if handle and settings.get("xcom_expand_threads"):
        member_ids = _thread_member_ids(
            str(tweet.get("url") or url), status_id, handle,
            int(settings.get("browser_timeout")),
        )
        for member_id in member_ids[: int(settings.get("xcom_max_thread_posts") or 25)]:
            try:
                members.append(_fetch(member_id, timeout))
            except (ExtractionError, urllib.error.URLError, OSError) as exc:
                logger.info("article-archive: thread member %s unavailable: %s", member_id, exc)
                break
        thread_md = _render_thread(members)
        if thread_md:
            body = f"{body}\n\n{thread_md}"

    return Article(
        url=str(tweet.get("url") or url),
        kind="x",
        title=f"@{handle}" if handle else "X post",
        author=f"{name} (@{handle})" if handle else name,
        published=_iso(tweet),
        site="X",
        description=(tweet.get("text") or "")[:280],
        content_md=body,
        word_count=len(body.split()),
        image=str((author.get("avatar_url") or "")),
        media=_media_urls(tweet),
        extra={
            "likes": tweet.get("likes"),
            "retweets": tweet.get("retweets"),
            "replies": tweet.get("replies"),
            "quotes": tweet.get("quotes"),
            "bookmarks": tweet.get("bookmarks"),
            "views": tweet.get("views"),
            "lang": tweet.get("lang"),
            "is_note_tweet": tweet.get("is_note_tweet"),
            "thread_posts": len(members) + 1 if members else None,
        },
        extractor="fxtwitter+thread" if members else "fxtwitter",
    )
