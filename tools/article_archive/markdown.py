"""Markdown-aware splitting.

Chunking exists for two unrelated consumers — an LLM request budget and a chat
platform's message cap — and both break the same way if you cut at a fixed
offset: a seam through a fenced code block turns the rest of the document into
code. Splitting on block boundaries and re-opening fences across the seam is
the shared part, so it lives here rather than in either front end.
"""

from __future__ import annotations

from typing import List, Optional

DEFAULT_LIMIT = 3500


def _fence_token(line: str) -> Optional[str]:
    stripped = line.lstrip()
    if stripped.startswith("```"):
        return stripped
    return None


def _blocks(text: str) -> List[str]:
    """Split markdown into paragraph/code blocks, keeping fences whole."""
    blocks: List[str] = []
    current: List[str] = []
    fence: Optional[str] = None

    for line in (text or "").splitlines():
        token = _fence_token(line)
        if fence is None and token is not None:
            if current:
                blocks.append("\n".join(current))
                current = []
            fence = token
            current.append(line)
            continue
        if fence is not None:
            current.append(line)
            if token is not None and line.strip() == "```":
                blocks.append("\n".join(current))
                current = []
                fence = None
            continue
        if not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)

    if current:
        blocks.append("\n".join(current))
    return blocks


def _split_oversized(block: str, limit: int) -> List[str]:
    """Break a single block that is larger than *limit* on its own."""
    lines = block.splitlines()
    fenced = bool(lines) and lines[0].lstrip().startswith("```")
    opener = lines[0] if fenced else ""
    body = lines[1:-1] if fenced and len(lines) > 1 and lines[-1].strip() == "```" else lines
    overhead = len(opener) + 5 if fenced else 0

    pieces: List[str] = []
    buf: List[str] = []
    size = 0
    for line in body:
        # A single line longer than the budget still has to go somewhere.
        while len(line) + overhead > limit:
            head, line = line[: limit - overhead], line[limit - overhead :]
            if buf:
                pieces.append("\n".join(buf))
                buf, size = [], 0
            pieces.append(head)
        if size + len(line) + 1 + overhead > limit and buf:
            pieces.append("\n".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        pieces.append("\n".join(buf))

    if fenced:
        return [f"{opener}\n{piece}\n```" for piece in pieces]
    return pieces


def split_markdown(text: str, limit: int = DEFAULT_LIMIT) -> List[str]:
    """Pack *text* into ``<= limit`` chunks without breaking markdown blocks."""
    chunks: List[str] = []
    buf: List[str] = []
    size = 0

    for block in _blocks(text):
        if len(block) > limit:
            if buf:
                chunks.append("\n\n".join(buf))
                buf, size = [], 0
            chunks.extend(_split_oversized(block, limit))
            continue
        if size + len(block) + 2 > limit and buf:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(block)
        size += len(block) + 2

    if buf:
        chunks.append("\n\n".join(buf))
    return [c for c in chunks if c.strip()]
