"""article-archive — URL in, markdown in the wiki out.

Front-end agnostic on purpose. The Hermes/Discord plugin drives this over the
CLI in ``cli.py``; ``/ingest`` in Claude Code drives the same entry points.
Nothing in this package knows what a channel or a button is.
"""

__all__ = ["agent", "documents", "extractors", "passes", "settings", "vcs"]
