"""The AI passes: Korean summary (with labels) and Korean translation.

Each is one agent run over a file. The prompt names paths, never content, so a
50,000-character article costs the same prompt as a 2,000-character one and
nothing has to be split. Everything before this point is deterministic
scripting — ``scrap`` makes no model call at all.

Each pass returns the text *and* the route that produced it, because the route
is written into the document's frontmatter.
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Tuple

from . import agent, settings
from .extractors import Article

logger = logging.getLogger(__name__)

# The wiki's closed domain vocabulary. Kept in sync with CLAUDE.md.
DOMAINS = ["ai", "dev", "career", "product", "infra", "misc"]

SOURCE_FILE = "source.md"

_TRANSLATE_SYSTEM = (
    "You are a professional technical translator working on files.\n"
    "Rules:\n"
    "- Preserve the markdown structure exactly: headings, lists, blockquotes, "
    "tables, links, bold/italic.\n"
    "- Never translate the contents of fenced code blocks or inline code. Leave "
    "identifiers, commands and code verbatim.\n"
    "- Keep widely used technical terms in English where a Korean developer "
    "would normally keep them (e.g. embedding, inference, latency).\n"
    "- Translate the ENTIRE document. Never summarize, omit, or stop early. If "
    "it is long, work through it in passes and append.\n"
    "- A line starting with '> 🖼️' marks a figure removed from the archive. "
    "Keep the line and translate its caption, rendering "
    "'[SVG figure omitted]' as '[SVG 도식 생략]' and '[inline image omitted]' "
    "as '[이미지 생략]'.\n"
    "- Write only the translated markdown to the output file. No frontmatter, "
    "no commentary, no code fence around the whole document."
)

_SUMMARY_SYSTEM = (
    "You summarize technical articles for a Korean-reading developer audience, "
    "working on files.\n"
    "Write the summary in Korean, as markdown:\n"
    "- Open with a 2-3 sentence paragraph on what the article is about and why "
    "it matters.\n"
    "- Then '**핵심 내용**' followed by 4-7 bullets covering the concrete "
    "claims, numbers, and architecture decisions — not vague generalities.\n"
    "- Close with '**결론**' and one or two sentences.\n"
    "Keep technical terms and product names in their original form. Do not "
    "invent anything that is not in the source. Write only the summary to the "
    "output file — no frontmatter, no commentary."
)


# --------------------------------------------------------------------------
# output checks
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_HANGUL_RE = re.compile(r"[가-힣]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_HEADING_RE = re.compile(r"^#{1,6} ", re.MULTILINE)


def _looks_untranslated(source: str, output: str) -> bool:
    """True when a route clearly handed back the source instead of Korean.

    Some models echo long inputs rather than translating them, which is worse
    than an error because it looks like success. Two signals catch it without
    tripping on code-heavy sections: the output is the input, or prose went in
    and no Hangul came out.
    """
    src, out = source.strip(), output.strip()
    if not out or out == src:
        return True

    src_prose = _FENCE_RE.sub(" ", src)
    if _HANGUL_RE.search(src_prose):
        return False  # source was already Korean; nothing to compare against
    if len(_LATIN_RE.findall(src_prose)) < 200:
        return False  # too little prose to judge (code listing, link dump)
    return not _HANGUL_RE.search(_FENCE_RE.sub(" ", out))


def _looks_truncated(source: str, output: str) -> bool:
    """True when a translation stopped partway through.

    The nastiest failure mode here: the archive ends up holding half an article
    with nothing to show anything went wrong. Structure is the sharper signal —
    the translator is told to preserve markdown exactly, so a complete pass
    comes back with the same headings.
    """
    src, out = source.strip(), output.strip()
    if not out:
        return True

    src_headings = len(_HEADING_RE.findall(src))
    if src_headings >= 3:
        if len(_HEADING_RE.findall(out)) < src_headings * 0.6:
            return True

    # Backstop for prose with no headings. English→Korean lands around 0.55 by
    # character count and code-heavy text closer to 1.0, so a quarter is well
    # below anything a complete translation produces.
    return len(out) < len(src) * 0.25


# --------------------------------------------------------------------------
# passes
# --------------------------------------------------------------------------

def translate(article: Article) -> Tuple[str, Optional[agent.AgentResult]]:
    """Translate the whole article in one agent run. ``("", None)`` on failure."""
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

    headings = len(_HEADING_RE.findall(source))
    prompt = (
        f"Translate ./{SOURCE_FILE} into Korean and write the result to "
        "./translation.md\n\n"
        f"The source has {headings} markdown headings and {len(source)} characters. "
        "The translation must keep every heading — check the output before you "
        "finish, and continue writing if anything is missing."
    )

    try:
        result = agent.run(
            prompt,
            inputs={SOURCE_FILE: source},
            outputs=["translation.md"],
            system=_TRANSLATE_SYSTEM,
            validate=lambda out: not (
                _looks_untranslated(source, out["translation.md"])
                or _looks_truncated(source, out["translation.md"])
            ),
            **agent.pass_config("translate"),
        )
    except Exception as exc:
        logger.warning("article-archive: translation failed: %s", exc)
        return "", None

    return result.outputs["translation.md"].strip(), result


def summarize(
    article: Article,
) -> Tuple[str, List[str], List[str], Optional[agent.AgentResult]]:
    """Summarize and label in one run. Returns ``(summary, tags, domains, route)``.

    Labels ride along with the summary rather than costing a second call — the
    agent has already read the article by the time it needs to tag it.
    """
    source = (article.content_md or "").strip()
    if not source:
        return "", [], [], None

    prompt = (
        f"Read ./{SOURCE_FILE} and write two files:\n\n"
        "1. ./summary.md — the Korean summary described in your instructions.\n"
        "2. ./labels.json — exactly this shape, nothing else:\n"
        '   {"tags": ["..."], "domains": ["..."]}\n'
        "   tags: 3-6 lowercase hyphenated topic slugs, no '#'. Specific over "
        'generic ("speculative-decoding" beats "ai").\n'
        f"   domains: 1-2 values chosen ONLY from {DOMAINS}."
    )

    try:
        result = agent.run(
            prompt,
            inputs={SOURCE_FILE: source},
            outputs=["summary.md"],
            optional_outputs=["labels.json"],
            system=_SUMMARY_SYSTEM,
            validate=lambda out: bool(out["summary.md"].strip()),
            **agent.pass_config("summary"),
        )
    except Exception as exc:
        logger.warning("article-archive: summary failed: %s", exc)
        return "", [], [], None

    tags, domains = _parse_labels(result.outputs.get("labels.json", ""))
    return result.outputs["summary.md"].strip(), tags, domains, result


def _parse_labels(raw: str) -> Tuple[List[str], List[str]]:
    """Pull tags/domains out of a file that may be fenced or have stray prose."""
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
            slug = re.sub(
                r"[^a-z0-9-]+", "-", str(value).strip().lower().lstrip("#")
            ).strip("-")
            if slug and (allowed is None or slug in allowed) and slug not in out:
                out.append(slug)
        return out

    return _clean(payload.get("tags"))[:6], _clean(payload.get("domains"), set(DOMAINS))[:2]
