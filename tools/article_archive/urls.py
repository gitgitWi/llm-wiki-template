"""URL detection for the article-archive trigger.

The plugin only takes over a message when it is *nothing but* a link. Anything
with prose around the URL is a question for the agent, not an archive request,
and falls through to normal dispatch.
"""

from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

# Discord lets users write <https://…> to suppress the embed; strip the guards.
_ANGLE = re.compile(r"^<(.+)>$")
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# Tracking junk that changes the URL without changing the article.
_STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "utm_social", "utm_social-type",
    "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref_src", "ref_url",
    "s", "t", "cxrecs_s",
}

X_HOSTS = {
    "x.com", "www.x.com", "mobile.x.com",
    "twitter.com", "www.twitter.com", "mobile.twitter.com",
    "fxtwitter.com", "vxtwitter.com", "fixupx.com",
}


def _normalize_token(token: str) -> str:
    token = token.strip()
    m = _ANGLE.match(token)
    if m:
        token = m.group(1).strip()
    # Trailing punctuation people type after a pasted link.
    return token.rstrip(").,;:!?'\"")


def extract_urls(text: str) -> List[str]:
    """Return every http(s) URL in *text*, de-duplicated, in order."""
    found: List[str] = []
    seen = set()
    for raw in _URL_RE.findall(text or ""):
        url = _normalize_token(raw)
        if url and url not in seen:
            seen.add(url)
            found.append(url)
    return found


def url_only_message(text: str) -> Optional[str]:
    """Return the archive target when *text* is a bare link, else ``None``.

    Bare means: after removing the URLs and Discord's ``<>`` embed guards,
    nothing but whitespace is left. A trailing note like ``"read later"``
    disqualifies the message so the agent handles it instead.
    """
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None

    urls = extract_urls(stripped)
    if not urls:
        return None

    remainder = _URL_RE.sub(" ", stripped)
    remainder = remainder.replace("<", " ").replace(">", " ")
    if remainder.strip():
        return None

    return urls[0]


def canonicalize(url: str) -> str:
    """Drop tracking params and normalize the host casing."""
    try:
        parts = urlparse(url)
    except ValueError:
        return url
    if not parts.scheme or not parts.netloc:
        return url

    query = "&".join(
        piece
        for piece in parts.query.split("&")
        if piece and piece.split("=", 1)[0].lower() not in _STRIP_PARAMS
    )
    return urlunparse(
        (parts.scheme, parts.netloc.lower(), parts.path, parts.params, query, "")
    )


def host_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except ValueError:
        return ""


def is_x_url(url: str) -> bool:
    return host_of(url) in X_HOSTS
