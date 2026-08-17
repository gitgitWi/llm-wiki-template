"""The AI passes: tags, Korean summary, Korean translation.

Everything before this point is deterministic scripting. Each pass returns the
text *and* the route that produced it, because the route is written into the
document's frontmatter — a summary six months from now should say which model
wrote it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import List, Optional, Tuple

from . import llm, settings
from .extractors import Article
from .extractors.sanitize import normalize_translated_markers
from .markdown import split_markdown

logger = logging.getLogger(__name__)

# The wiki's closed domain vocabulary. Kept in sync with CLAUDE.md.
DOMAINS = ["ai", "dev", "career", "product", "infra", "misc"]

_TRANSLATE_SYSTEM = (
    "You are a professional technical translator. Translate the user's markdown "
    "into natural, fluent Korean.\n"
    "Rules:\n"
    "- Preserve the markdown structure exactly: headings, lists, blockquotes, "
    "tables, links, bold/italic.\n"
    "- Never translate the contents of fenced code blocks or inline code. Leave "
    "identifiers, commands and code verbatim.\n"
    "- Keep widely used technical terms in English where a Korean developer "
    "would normally keep them (e.g. embedding, inference, latency).\n"
    "- Do not summarize, omit, or add commentary. Translate everything you are "
    "given.\n"
    "- A line starting with '> 🖼️' marks a figure that was removed from the "
    "archive. Keep the line and translate its caption, rendering "
    "'[SVG figure omitted]' as '[SVG 도식 생략]' and '[inline image omitted]' "
    "as '[이미지 생략]'.\n"
    "- Output only the translation."
)

_SUMMARY_SYSTEM = (
    "You summarize technical articles for a Korean-reading developer audience.\n"
    "Write the summary in Korean, as markdown:\n"
    "- Open with a 2-3 sentence paragraph on what the article is about and why "
    "it matters.\n"
    "- Then '**핵심 내용**' followed by 4-7 bullets covering the concrete "
    "claims, numbers, and architecture decisions — not vague generalities.\n"
    "- Close with '**결론**' and one or two sentences.\n"
    "Keep technical terms and product names in their original form. Do not "
    "invent anything that is not in the source. Output only the summary."
)

_LABEL_SYSTEM = (
    "You label archived technical articles for a personal wiki.\n"
    "Given the title and opening text, reply with JSON only:\n"
    '{"tags": ["..."], "domains": ["..."]}\n'
    "- tags: 3 to 6 lowercase topic slugs, hyphenated, no '#'. Specific over "
    "generic (\"speculative-decoding\" beats \"ai\").\n"
    f"- domains: 1 to 2 values, chosen ONLY from {DOMAINS}.\n"
    "Output the JSON object and nothing else."
)


# --------------------------------------------------------------------------
# translation quality check
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_HANGUL_RE = re.compile(r"[가-힣]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _looks_untranslated(source: str, output: str) -> bool:
    """True when a route clearly handed back the source instead of Korean.

    Some open-weight models silently echo long inputs rather than translating
    them, which is worse than an error because it looks like a success. Two
    signals catch it without tripping on code-heavy sections: the output is the
    input, or prose went in and no Hangul came out.
    """
    src, out = source.strip(), output.strip()
    if not out:
        return True
    if out == src:
        return True

    src_prose = _FENCE_RE.sub(" ", src)
    if _HANGUL_RE.search(src_prose):
        return False  # source was already Korean; nothing to compare against
    if len(_LATIN_RE.findall(src_prose)) < 200:
        return False  # too little prose to judge (code listing, link dump)
    return not _HANGUL_RE.search(_FENCE_RE.sub(" ", out))


# --------------------------------------------------------------------------
# passes
# --------------------------------------------------------------------------

async def make_labels(article: Article) -> Tuple[List[str], List[str], Optional[llm.LLMResult]]:
    """Return ``(tags, domains, route)``. Empty lists when the pass fails."""
    head = (article.content_md or "")[:1200]
    prompt = f"Title: {article.title}\nSite: {article.site}\n\n{head}"
    try:
        result = await asyncio.to_thread(
            llm.call,
            [
                {"role": "system", "content": _LABEL_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.3,
        )
    except Exception as exc:
        logger.info("article-archive: label generation failed: %s", exc)
        return [], [], None

    tags, domains = _parse_labels(result.content)
    return tags, domains, result


def _parse_labels(raw: str) -> Tuple[List[str], List[str]]:
    """Pull tags/domains out of a model reply that may be fenced or chatty."""
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return [], []
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return [], []

    def _clean(values, allowed=None):
        out = []
        for value in values if isinstance(values, list) else []:
            slug = re.sub(r"[^a-z0-9-]+", "-", str(value).strip().lower().lstrip("#")).strip("-")
            if slug and (allowed is None or slug in allowed) and slug not in out:
                out.append(slug)
        return out

    return _clean(payload.get("tags"))[:6], _clean(payload.get("domains"), set(DOMAINS))[:2]


async def summarize(article: Article) -> Tuple[str, Optional[llm.LLMResult]]:
    """A Korean summary of *article*, or ``("", None)`` when every route refused.

    One request regardless of article length: the source is truncated to a
    front slice big enough to carry the argument, since a summary does not need
    the tail of a reference list.
    """
    source = (article.content_md or "").strip()
    if not source:
        return "", None

    budget = int(settings.get("summary_source_chars"))
    excerpt = source[:budget]
    if len(source) > budget:
        excerpt += "\n\n[… truncated for summarization …]"

    header = f"Title: {article.title}\nSource: {article.url}\nSite: {article.site}"
    try:
        result = await asyncio.to_thread(
            llm.call,
            [
                {"role": "system", "content": _SUMMARY_SYSTEM},
                {"role": "user", "content": f"{header}\n\n{excerpt}"},
            ],
            max_tokens=int(settings.get("summary_max_tokens")),
            temperature=0.3,
        )
    except Exception as exc:
        logger.warning("article-archive: summary failed: %s", exc)
        return "", None
    return result.content, result


async def _translate_chunk(
    chunk: str, sem: asyncio.Semaphore, index: int, total: int
) -> Tuple[str, Optional[llm.LLMResult]]:
    async with sem:
        marker = f"(part {index + 1}/{total})" if total > 1 else ""
        try:
            result = await asyncio.to_thread(
                llm.call,
                [
                    {"role": "system", "content": _TRANSLATE_SYSTEM},
                    {"role": "user", "content": chunk},
                ],
                # Korean output runs longer than English source; give it room.
                max_tokens=max(1024, int(len(chunk) / 1.4)),
                validate=lambda out, src=chunk: not _looks_untranslated(src, out),
            )
        except llm.LLMUnavailable:
            raise
        except Exception as exc:
            logger.warning("article-archive: translation chunk %s failed: %s", marker, exc)
            # A failed slice must not sink the whole archive — keep the source.
            return chunk, None
        return result.content, result


async def translate(article: Article) -> Tuple[str, Optional[llm.LLMResult]]:
    """Return ``(korean_markdown, route)``."""
    source = (article.content_md or "").strip()
    if not source:
        return "", None

    max_chars = int(settings.get("translate_max_chars"))
    if len(source) > max_chars:
        logger.info(
            "article-archive: skipping translation, %d chars over the %d limit",
            len(source), max_chars,
        )
        return "", None

    chunks = split_markdown(source, limit=int(settings.get("translate_chunk_chars")))
    if not chunks:
        return "", None

    sem = asyncio.Semaphore(max(1, int(settings.get("translate_concurrency"))))

    # Translate the first chunk alone before fanning out. A refused route then
    # lands in the cooldown memo once, instead of every chunk racing into the
    # same dead provider simultaneously.
    try:
        first, route = await _translate_chunk(chunks[0], sem, 0, len(chunks))
        rest = await asyncio.gather(
            *(_translate_chunk(c, sem, i, len(chunks)) for i, c in enumerate(chunks[1:], 1))
        )
    except llm.LLMUnavailable as exc:
        logger.warning("article-archive: translation unavailable: %s", exc)
        return "", None

    parts = [first, *(text for text, _ in rest)]
    route = route or next((r for _, r in rest if r is not None), None)
    korean = "\n\n".join(p for p in parts if p.strip())
    # Each chunk was translated by its own request, so figure markers can come
    # back phrased differently. Settle on one spelling across the article.
    return normalize_translated_markers(korean), route
