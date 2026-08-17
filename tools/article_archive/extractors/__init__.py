"""Extraction layer: URL in, :class:`Article` out.

Routing is deliberately shallow — a per-host table of specialised extractors,
falling back to defuddle for everything else. Adding a site means adding one
module and one table entry; no agent involvement anywhere in this layer.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .. import urls as urlmod

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Normalized extraction result shared by every extractor."""

    url: str
    kind: str = "web"          # "web" | "x"
    title: str = ""
    author: str = ""
    published: str = ""
    site: str = ""
    description: str = ""
    content_md: str = ""
    word_count: int = 0
    image: str = ""
    media: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    extractor: str = ""
    elapsed_ms: int = 0

    @property
    def is_empty(self) -> bool:
        return not (self.content_md or "").strip()


class ExtractionError(RuntimeError):
    """Raised when no extractor could produce usable content."""


def browser_reread(url: str) -> Article:
    """Re-extract *url* with a real browser, whatever the cheap tier produced.

    This is what the 🌐 button runs.  It is deliberately not part of the
    automatic path: a render costs tens of seconds against a script tier that
    costs well under one, and it is only worth that when a reader looks at the
    result and decides it is thin.
    """
    started = time.monotonic()
    canonical = urlmod.canonicalize(url)

    from . import x_article

    if x_article.is_x_article(canonical):
        article = x_article.fetch(canonical, force=True)
    elif urlmod.is_x_url(canonical):
        # A tweet already arrives complete over fxtwitter — including
        # long-form text a browser would have to recover from the DOM — so a
        # render here would be slower and no better.
        raise ExtractionError("X 게시물은 이미 전문을 가져옵니다. 브라우저 재읽기가 필요 없습니다.")
    else:
        from . import generic

        article = generic.extract_rendered(canonical)

    article.elapsed_ms = int((time.monotonic() - started) * 1000)
    if article.is_empty:
        raise ExtractionError(f"브라우저로도 본문을 찾지 못했습니다: {url}")
    return article


def extract(url: str) -> Article:
    """Extract *url* using the best available extractor.

    Raises :class:`ExtractionError` when every path fails.
    """
    started = time.monotonic()
    canonical = urlmod.canonicalize(url)

    if urlmod.is_x_url(canonical):
        from . import x_article, xcom

        # An X Article is not a tweet and has no fxtwitter representation, so
        # it takes the browser path directly rather than discovering that fact
        # after a wasted API call.
        if x_article.is_x_article(canonical):
            article = x_article.fetch(canonical)
        else:
            article = xcom.extract(canonical)
    else:
        from . import generic

        article = generic.extract(canonical)

    article.elapsed_ms = int((time.monotonic() - started) * 1000)
    if article.is_empty:
        raise ExtractionError(f"no content extracted from {url}")
    return article
