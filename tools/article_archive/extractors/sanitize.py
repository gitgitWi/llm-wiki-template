"""Strip unreadable binary-ish payloads out of extracted markdown.

defuddle keeps inline ``<svg>`` markup and ``data:`` URIs verbatim. In a
Discord archive they are pure cost: unreadable to a reader, they push the real
prose past the message budget, and they get fed to the translator as tokens
that can only come back as noise.

They are replaced rather than deleted, so the archive still shows that a figure
was there. Most inline SVGs carry a ``<title>`` or ``aria-label`` written for
screen readers — that caption is the best available description, so it rides
along in the placeholder and gets translated with the rest of the article.

Fenced code blocks are left untouched: an article *about* SVG has SVG source as
its actual content.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .. import settings
from .tables import replace_html_tables, replace_pipe_tables

_SVG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_ARIA_LABEL_RE = re.compile(r"""\baria-label\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# ![alt](data:image/png;base64,AAAA…) and bare data: URIs left in link targets.
_DATA_IMG_RE = re.compile(r"!\[([^\]]*)\]\(\s*<?data:[^)\s]+>?\s*\)", re.IGNORECASE)
_DATA_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*<?data:[^)\s]+>?\s*\)", re.IGNORECASE)

# Markers stay in English so the archived original reads as one language; the
# translation pass renders them in Korean along with the caption.
SVG_MARKER = "[SVG figure omitted]"
IMAGE_MARKER = "[inline image omitted]"

# Every placeholder line carries this, in the original and the translation, so
# downstream code can find them without re-parsing the marker text.
PLACEHOLDER_SIGIL = "🖼️"

# Canonical Korean renderings, applied after translation so the marker reads
# the same in every chunk regardless of how each request phrased it.
SVG_MARKER_KO = "[SVG 도식 생략]"
IMAGE_MARKER_KO = "[이미지 생략]"

_FENCE_RE = re.compile(r"^\s*```")


def _caption(svg: str) -> str:
    """Best human-readable description carried inside an ``<svg>`` block."""
    match = _TITLE_RE.search(svg)
    text = match.group(1) if match else ""
    if not text.strip():
        label = _ARIA_LABEL_RE.search(svg)
        text = label.group(1) if label else ""
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()
    return text[:300]


def _placeholder(marker: str, caption: str, *, own_line: bool) -> str:
    """Blockquote when the figure stood alone, inline when it sat in a sentence.

    A ``>`` in the middle of a paragraph is not a blockquote to Discord — it is
    a stray angle bracket — so the form has to follow the position.
    """
    body = f"{marker} {caption}".strip() if caption else marker
    # Both forms carry the sigil so post-translation normalization can find
    # them wherever they ended up.
    return f"> {PLACEHOLDER_SIGIL} *{body}*" if own_line else f"*{PLACEHOLDER_SIGIL} {body}*"


def _starts_line(text: str, index: int) -> bool:
    return index == 0 or text[index - 1] == "\n"


def _split_fences(text: str) -> List[Tuple[bool, str]]:
    """Split into ``(is_code, segment)`` runs so fences can be skipped."""
    segments: List[Tuple[bool, str]] = []
    buf: List[str] = []
    in_code = False

    for line in text.splitlines(keepends=True):
        if _FENCE_RE.match(line):
            buf.append(line)
            if in_code:  # closing fence ends the code run
                segments.append((True, "".join(buf)))
                buf = []
                in_code = False
            else:        # opening fence starts one
                opener = buf.pop()
                if buf:
                    segments.append((False, "".join(buf)))
                buf = [opener]
                in_code = True
            continue
        buf.append(line)

    if buf:
        segments.append((in_code, "".join(buf)))
    return segments


def _sanitize_prose(text: str) -> Tuple[str, int, int]:
    svgs = 0
    images = 0

    def _svg_sub(match: re.Match) -> str:
        nonlocal svgs
        svgs += 1
        return _placeholder(
            SVG_MARKER,
            _caption(match.group(0)),
            own_line=_starts_line(match.string, match.start()),
        )

    def _img_sub(match: re.Match) -> str:
        nonlocal images
        images += 1
        return _placeholder(
            IMAGE_MARKER,
            _WS_RE.sub(" ", match.group(1)).strip(),
            own_line=_starts_line(match.string, match.start()),
        )

    text = _SVG_RE.sub(_svg_sub, text)
    text = _DATA_IMG_RE.sub(_img_sub, text)
    text = _DATA_LINK_RE.sub(_img_sub, text)
    return text, svgs, images


def clean_markdown(text: str) -> Tuple[str, int, int, int]:
    """Return ``(cleaned, svgs_replaced, data_uris_replaced, tables_reformatted)``.

    Idempotent — running it twice replaces nothing the second time.
    """
    if not text:
        return text or "", 0, 0, 0

    lowered = text.lower()
    # Cheap bail-out: most articles have none of these.
    if (
        "<svg" not in lowered
        and "data:" not in text
        and "<table" not in lowered
        and "|" not in text
    ):
        return text, 0, 0, 0

    # Flattening tables into fixed-width grids exists for chat clients that
    # cannot render them. A markdown file can, and flattening throws away the
    # column structure, so it is opt-in here.
    reformat = bool(settings.get("reformat_tables"))

    out: List[str] = []
    svgs = images = tables = 0
    for is_code, segment in _split_fences(text):
        if is_code:
            out.append(segment)
            continue
        cleaned, s, i = _sanitize_prose(segment)
        if reformat:
            cleaned, t1 = replace_html_tables(cleaned)
            cleaned, t2 = replace_pipe_tables(cleaned)
            tables += t1 + t2
        out.append(cleaned)
        svgs += s
        images += i

    result = "".join(out)
    # Placeholders left behind blank-line rubble where a figure used to sit.
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result, svgs, images, tables


# Whatever the translator did to the bracketed marker — kept it English,
# invented its own Korean phrasing — it stayed a bracket group on a line
# carrying the sigil. That is enough to normalize on.
_KO_SVG_RE = re.compile(r"\[\s*SVG[^\]]*\]", re.IGNORECASE)
_KO_IMG_RE = re.compile(r"\[\s*(?:inline\s+)?(?:image|이미지)[^\]]*\]", re.IGNORECASE)


def normalize_translated_markers(text: str) -> str:
    """Force one Korean spelling for every figure marker in a translation."""
    if not text or PLACEHOLDER_SIGIL not in text:
        return text

    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if PLACEHOLDER_SIGIL not in line:
            continue
        replaced, count = _KO_SVG_RE.subn(SVG_MARKER_KO, line, count=1)
        if not count:
            replaced, count = _KO_IMG_RE.subn(IMAGE_MARKER_KO, line, count=1)
        if count:
            lines[i] = replaced
    return "".join(lines)
