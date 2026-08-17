"""Turn an :class:`Article` into files in the wiki, and report where they went.

Three destinations, and which one a pass writes to follows the repo's
ownership rule rather than convenience:

- ``raw/articles/<stem>.md`` — the extracted original. Immutable once written;
  only a browser re-read replaces it, and that is a better capture of the same
  source, not an edit.
- ``raw/articles/<stem>.ko.md`` — the full Korean translation. A complete
  derivative of someone else's article, so it sits with the source and stays
  out of the published build for the same copyright reason the original does.
- ``wiki/digests/<stem>.md`` — the summary. This one is ours, so it is the
  piece that can be published.

No YAML dependency: the frontmatter written here is a fixed shape, and the
reader only ever has to parse files this module wrote.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import settings
from .extractors import Article


@dataclass
class Written:
    """Where one file landed."""

    kind: str      # "raw" | "translation" | "digest"
    path: Path
    rel: str       # repo-relative, always POSIX
    uri: str       # path or GitHub blob URL, per settings

    def as_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "path": str(self.path), "rel": self.rel, "uri": self.uri}


# --------------------------------------------------------------------------
# naming
# --------------------------------------------------------------------------

MAX_SLUG = 60


def slugify(text: str) -> str:
    """ASCII kebab-case slug, or "" when *text* carries no ASCII."""
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9]+", "-", folded).strip("-").lower())
    if len(slug) > MAX_SLUG:
        # Cut on a word boundary — "…pelicans-on-bicyc" reads like a typo, and
        # the slug is what shows up in the URL.
        head = slug[:MAX_SLUG]
        slug = head.rsplit("-", 1)[0] if "-" in head else head
    return slug.strip("-")


def make_stem(article: Article, *, today: Optional[str] = None) -> str:
    """``YYYY-MM-DD-<slug>``.

    The wiki keeps filenames ASCII so URLs stay stable and links do not break
    on percent-encoding, but plenty of titles are Korean and transliterate to
    nothing. Those fall back to the host plus a short digest of the URL, which
    is stable for the same article and still readable at a glance.
    """
    date = today or datetime.now().strftime("%Y-%m-%d")
    slug = slugify(article.title)
    if len(slug) < 3:
        host = slugify(article.site or urlparse(article.url or "").netloc)
        digest = hashlib.sha1((article.url or "").encode("utf-8")).hexdigest()[:8]
        slug = f"{host}-{digest}" if host else f"article-{digest}"
    return f"{date}-{slug}"


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------

_PLAIN_RE = re.compile(r"^[A-Za-z0-9가-힣][^:#\n]*$")


def _scalar(value: Any) -> str:
    text = str(value if value is not None else "").replace("\r", "").replace("\n", " ").strip()
    if not text:
        return '""'
    if _PLAIN_RE.match(text) and not text.endswith(" "):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _seq(values: Optional[List[str]]) -> str:
    return "[" + ", ".join(_scalar(v) for v in (values or [])) + "]"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _route_lines(prefix: str, route: Any, *, indent: str = "  ") -> List[str]:
    """`updated` plus which model produced this pass."""
    lines = [f"{indent}updated: {_now()}"]
    for field in ("provider", "model", "backend", "thinking"):
        value = getattr(route, field, "") or ""
        if value:
            lines.append(f"{indent}{field}: {_scalar(value)}")
    return lines


def _frontmatter(
    article: Article,
    *,
    doc_type: str,
    visibility: str,
    tags: Optional[List[str]] = None,
    domains: Optional[List[str]] = None,
    title: Optional[str] = None,
    extra_blocks: Optional[Dict[str, List[str]]] = None,
    related: Optional[List[str]] = None,
    created: str = "",
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "---",
        f"title: {_scalar(title or article.title or article.url)}",
        f"type: {doc_type}",
        f"visibility: {visibility}",
        f"domains: {_seq(domains or [])}",
        f"tags: {_seq(tags or [])}",
        "status: living",
        f"created: {created or today}",
        f"updated: {today}",
        "source:",
        f"  url: {_scalar(article.url)}",
    ]
    if article.author:
        lines.append(f"  author: {_scalar(article.author)}")
    if article.site:
        lines.append(f"  site: {_scalar(article.site)}")
    if article.published:
        lines.append(f"  published: {_scalar(article.published[:10])}")
    lines.append(f"  captured: {today}")
    if article.word_count:
        lines.append(f"  word_count: {article.word_count}")
    if article.extractor:
        lines.append(f"  extractor: {_scalar(article.extractor)}")

    for key, block in (extra_blocks or {}).items():
        lines.append(f"{key}:")
        lines.extend(block)

    lines.append(f"related: {_seq(related or [])}")
    lines.append("---")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# reading back
# --------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Parse the flat subset of YAML this module writes. Nested keys are kept
    under their parent as a dict; everything else is a string or list."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    head, body = text[3:end], text[end + 4 :].lstrip("\n")

    data: Dict[str, Any] = {}
    parent: Optional[str] = None
    for line in head.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indented = line.startswith(("  ", "\t"))
        key, _, raw = line.strip().partition(":")
        key, raw = key.strip(), raw.strip()
        if indented and parent:
            bucket = data.setdefault(parent, {})
            if isinstance(bucket, dict):
                bucket[key] = _unscalar(raw)
            continue
        if not raw:
            parent = key
            data.setdefault(key, {})
            continue
        parent = None
        data[key] = _unscalar(raw)
    return data, body


def _unscalar(raw: str) -> Any:
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_unscalar(part.strip()) for part in inner.split(",")]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return raw


def read_article(stem: str) -> Optional[Article]:
    """Rebuild an :class:`Article` from a previously written raw file.

    Lets ``summarize``/``translate`` run later without re-fetching the source —
    the point of archiving it in the first place.
    """
    path = raw_dir() / f"{stem}.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = split_frontmatter(text)
    source = meta.get("source") if isinstance(meta.get("source"), dict) else {}

    # Drop the leading "# title" the writer added, so content_md round-trips.
    body = re.sub(r"\A#\s+[^\n]*\n+", "", body.lstrip())
    return Article(
        url=str(source.get("url") or ""),
        title=str(meta.get("title") or ""),
        author=str(source.get("author") or ""),
        published=str(source.get("published") or ""),
        site=str(source.get("site") or ""),
        content_md=body,
        word_count=int(source.get("word_count") or 0) or len(body.split()),
        extractor=str(source.get("extractor") or ""),
    )


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------

def prior_meta(path: Path) -> Dict[str, Any]:
    """Frontmatter already on disk at *path*, or ``{}``.

    Re-running a pass rewrites the whole file, which would otherwise silently
    undo a ``/publish`` — the digest would drop back to private, and the
    original capture date would be lost.
    """
    try:
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    return meta


def raw_dir() -> Path:
    return settings.wiki_root() / str(settings.get("raw_dir"))


def digest_dir() -> Path:
    return settings.wiki_root() / str(settings.get("digest_dir"))


def resolve_uri(rel: str) -> str:
    """How to refer to *rel* for whoever asked — a path, or a GitHub URL.

    The template reports paths because it is the repo you are standing in; a
    private fork sets ``uri_mode: github`` so a Discord card can link straight
    into the file.
    """
    if str(settings.get("uri_mode")) == "github":
        repo = str(settings.get("github_repo") or "").strip("/")
        branch = str(settings.get("github_branch") or "main")
        if repo:
            return f"https://github.com/{repo}/blob/{branch}/{rel}"
    return rel


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    tmp.replace(path)


def _written(kind: str, path: Path) -> Written:
    rel = path.relative_to(settings.wiki_root()).as_posix()
    return Written(kind=kind, path=path, rel=rel, uri=resolve_uri(rel))


def write_raw(
    article: Article,
    *,
    stem: str,
    tags: Optional[List[str]] = None,
    domains: Optional[List[str]] = None,
) -> Written:
    path = raw_dir() / f"{stem}.md"
    prior = prior_meta(path)
    front = _frontmatter(
        article,
        doc_type="source",
        visibility=str(settings.get("raw_visibility")),
        # A browser re-read replaces the text, not the day it was captured.
        created=str(prior.get("created") or ""),
        tags=tags,
        domains=domains,
    )
    heading = f"# {article.title}" if article.title else ""
    body = "\n\n".join(p for p in (front, heading, article.content_md.strip()) if p.strip())
    _write(path, body)
    return _written("raw", path)


def write_translation(article: Article, korean: str, *, stem: str, route: Any = None) -> Written:
    front = _frontmatter(
        article,
        doc_type="source",
        visibility=str(settings.get("raw_visibility")),
        title=f"{article.title} (한국어)" if article.title else None,
        extra_blocks={"translation": _route_lines("translation", route)},
        related=[f"[[{stem}]]"],
    )
    body = "\n\n".join(
        p for p in (front, "# 🌐 한국어 번역", (korean or "").strip()) if p.strip()
    )
    path = raw_dir() / f"{stem}.ko.md"
    _write(path, body)
    return _written("translation", path)


def write_digest(
    article: Article,
    summary: str,
    *,
    stem: str,
    route: Any = None,
    tags: Optional[List[str]] = None,
    domains: Optional[List[str]] = None,
) -> Written:
    path = digest_dir() / f"{stem}.md"
    prior = prior_meta(path)
    front = _frontmatter(
        article,
        doc_type="source",
        # A published digest stays published across a re-summarize.
        visibility=str(prior.get("visibility") or settings.get("digest_visibility")),
        created=str(prior.get("created") or ""),
        tags=tags,
        domains=domains,
        extra_blocks={"summary": _route_lines("summary", route)},
        # No wikilink back to the raw file on purpose. A digest is the one
        # publishable piece, the raw source never is, and a public page linking
        # a private one is exactly what /publish rejects. Provenance is already
        # carried by source.url — which is where you would actually navigate —
        # and by the archive path in the body.
        related=[],
    )
    heading = f"# {article.title}" if article.title else ""
    tail = f"> 원문: <{article.url}>\n> 아카이브: `{raw_dir().name}/{stem}.md`"
    body = "\n\n".join(
        p for p in (front, heading, (summary or "").strip(), tail) if p.strip()
    )
    _write(path, body)
    return _written("digest", path)
