"""Command line entry point — the whole interface any front end needs.

    python tools/article_archive/cli.py scrap <url> --json
    python tools/article_archive/cli.py summarize <stem> --json
    python tools/article_archive/cli.py translate <stem> --json
    python tools/article_archive/cli.py browser <stem> --json
    python tools/article_archive/cli.py show <url>

``--json`` prints one object on stdout and nothing else, which is the contract
the Hermes plugin parses. Human output goes to stderr so the two never mix.

The AI passes need a backend: run this with Hermes' interpreter to reuse its
auxiliary client, or set ``ARTICLE_ARCHIVE_OPENAI_BASE_URL`` for any
OpenAI-compatible endpoint. ``scrap`` and ``show`` work without either.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

if __package__ in (None, ""):
    # Run directly as a script: make the package importable so the relative
    # imports below resolve (PEP 366).
    import importlib
    import pathlib

    _pkg_dir = pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(_pkg_dir.parent))
    __package__ = _pkg_dir.name
    importlib.import_module(__package__)

from . import agent, documents, passes
from .extractors import Article, ExtractionError, browser_reread, extract


def _emit(payload: Dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("ok") else 1

    if not payload.get("ok"):
        print(f"error: {payload.get('error')}", file=sys.stderr)
        return 1
    for file in payload.get("files") or []:
        print(f"{file['kind']:<12} {file['uri']}", file=sys.stderr)
    return 0


def _article_fields(article: Article) -> Dict[str, Any]:
    return {
        "url": article.url,
        "title": article.title,
        "site": article.site,
        "author": article.author,
        "word_count": article.word_count,
        "extractor": article.extractor,
        "elapsed_ms": article.elapsed_ms,
        # Front ends decide which follow-up actions apply from this — e.g.
        # whether the post quotes an X Article worth pulling in full.
        "extra": article.extra or {},
    }


def _load(stem_or_url: str) -> tuple[Optional[Article], Optional[str], Optional[str]]:
    """Resolve an argument that may be a stored stem or a fresh URL."""
    if stem_or_url.startswith(("http://", "https://")):
        try:
            article = extract(stem_or_url)
        except ExtractionError as exc:
            return None, None, str(exc)
        return article, documents.make_stem(article), None

    article = documents.read_article(stem_or_url)
    if article is None:
        return None, None, f"no archived article for stem '{stem_or_url}'"
    return article, stem_or_url, None


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------

def _do_scrap(url: str) -> Dict[str, Any]:
    """Extraction only — no model call. Tags arrive with the summary."""
    try:
        article = extract(url)
    except ExtractionError as exc:
        return {"ok": False, "action": "scrap", "url": url, "error": str(exc)}
    except Exception as exc:  # a broken extractor must not look like a bad URL
        return {"ok": False, "action": "scrap", "url": url, "error": repr(exc)}

    stem = documents.make_stem(article)
    written = documents.write_raw(article, stem=stem)
    return {
        "ok": True,
        "action": "scrap",
        "stem": stem,
        "files": [written.as_dict()],
        **_article_fields(article),
    }


def _do_summarize(target: str) -> Dict[str, Any]:
    article, stem, error = _load(target)
    if article is None:
        return {"ok": False, "action": "summarize", "error": error}

    summary, tags, domains, route = passes.summarize(article)
    if not summary:
        return {
            "ok": False,
            "action": "summarize",
            "stem": stem,
            "error": "summary unavailable — every agent route failed",
        }

    written = documents.write_digest(
        article, summary, stem=stem, route=route, tags=tags, domains=domains
    )
    return {
        "ok": True,
        "action": "summarize",
        "stem": stem,
        "summary": summary,
        "tags": tags,
        "domains": domains,
        "provider": getattr(route, "provider", ""),
        "model": getattr(route, "model", ""),
        "files": [written.as_dict()],
        **_article_fields(article),
    }


def _do_translate(target: str) -> Dict[str, Any]:
    article, stem, error = _load(target)
    if article is None:
        return {"ok": False, "action": "translate", "error": error}

    korean, route = passes.translate(article)
    if not korean:
        return {
            "ok": False,
            "action": "translate",
            "stem": stem,
            "error": "translation unavailable — every agent route failed, or "
                     "the source is over the size limit",
        }

    written = documents.write_translation(article, korean, stem=stem, route=route)
    return {
        "ok": True,
        "action": "translate",
        "stem": stem,
        "chars": len(korean),
        "provider": getattr(route, "provider", ""),
        "model": getattr(route, "model", ""),
        "files": [written.as_dict()],
        **_article_fields(article),
    }


def _do_browser(target: str) -> Dict[str, Any]:
    previous, stem, error = _load(target)
    if previous is None:
        return {"ok": False, "action": "browser", "error": error}

    try:
        fresh = browser_reread(previous.url)
    except ExtractionError as exc:
        return {"ok": False, "action": "browser", "stem": stem, "error": str(exc)}

    # Replacing the raw file is a better capture of the same source, not an
    # edit of it — the reader looked at a thin extraction and rejected it.
    written = documents.write_raw(fresh, stem=stem)
    return {
        "ok": True,
        "action": "browser",
        "stem": stem,
        "gained_words": fresh.word_count - previous.word_count,
        "files": [written.as_dict()],
        **_article_fields(fresh),
    }


def _do_xarticle(url: str, *, stem: Optional[str]) -> Dict[str, Any]:
    """Pull an X Article in full.

    Separate from ``browser`` because the URL being fetched is usually not the
    URL that was archived — a tweet quoting an Article is archived as the
    tweet, and this pulls the thing it points at.
    """
    from .extractors import x_article

    try:
        fresh = x_article.fetch(url, force=True)
    except ExtractionError as exc:
        return {"ok": False, "action": "xarticle", "url": url, "error": str(exc)}

    stem = stem or documents.make_stem(fresh)
    written = documents.write_raw(fresh, stem=stem)
    return {
        "ok": True,
        "action": "xarticle",
        "stem": stem,
        "files": [written.as_dict()],
        **_article_fields(fresh),
    }


def _do_show(url: str) -> Dict[str, Any]:
    try:
        article = extract(url)
    except ExtractionError as exc:
        return {"ok": False, "action": "show", "url": url, "error": str(exc)}
    return {
        "ok": True,
        "action": "show",
        "content_md": article.content_md,
        "files": [],
        **_article_fields(article),
    }


# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="article-archive")
    parser.add_argument("--json", action="store_true", help="emit one JSON object")
    sub = parser.add_subparsers(dest="action", required=True)

    # Accept --json on either side of the subcommand. SUPPRESS keeps the
    # subparser from resetting a flag the top level already set.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    scrap = sub.add_parser("scrap", parents=[common], help="extract a URL into raw/articles")
    scrap.add_argument("url")

    for name, help_text in (
        ("summarize", "write a Korean summary into wiki/digests"),
        ("translate", "write a full Korean translation next to the source"),
        ("browser", "re-extract through a real browser and replace the raw file"),
    ):
        node = sub.add_parser(name, parents=[common], help=help_text)
        node.add_argument("target", help="stem of an archived article, or a URL")

    xarticle = sub.add_parser(
        "xarticle", parents=[common], help="pull an X Article in full"
    )
    xarticle.add_argument("target", help="the x.com/i/article/<id> URL")
    xarticle.add_argument(
        "--stem", default=None, help="overwrite this archived stem instead of a new one"
    )

    show = sub.add_parser(
        "show", parents=[common], help="extract and print without writing anything"
    )
    show.add_argument("url")

    args = parser.parse_args(argv)

    if args.action == "scrap":
        payload = _do_scrap(args.url)
    elif args.action == "summarize":
        payload = _do_summarize(args.target)
    elif args.action == "translate":
        payload = _do_translate(args.target)
    elif args.action == "browser":
        payload = _do_browser(args.target)
    elif args.action == "xarticle":
        payload = _do_xarticle(args.target, stem=args.stem)
    else:
        payload = _do_show(args.url)

    if args.action == "show" and not args.json and payload.get("ok"):
        print(payload.pop("content_md", ""))

    return _emit(payload, args.json)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
