"""Commit and push what a pass just wrote.

The archive is only useful if it survives the laptop, so writing a file and
leaving it uncommitted is half a job. This runs after each write.

Order is deliberate: **commit first, then integrate, then push.** Pulling into
a dirty tree is how you lose a file you just generated; committing first means
the worst case is a local commit that has not been pushed yet, which is
recoverable by hand and by the next run.

Nothing here is allowed to fail the pass. The document is already on disk —
a network outage or a diverged branch is a warning, not a lost archive.
"""

from __future__ import annotations

import fcntl
import logging
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import settings

logger = logging.getLogger(__name__)


class _GitError(RuntimeError):
    pass


def _run(args: List[str], *, root: Path, check: bool = True) -> str:
    proc = subprocess.run(  # noqa: S603 - argv built here, no shell
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=float(settings.get("git_timeout")),
    )
    if check and proc.returncode != 0:
        raise _GitError(
            f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()[:300]}"
        )
    return (proc.stdout or "").strip()


@contextmanager
def _lock(root: Path):
    """Serialize concurrent archives.

    Two passes finishing at once would race on the index and one would die on
    `index.lock`. flock releases on process exit, so a crash cannot wedge it.
    """
    path = root / ".git" / "article-archive.lock"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w")
    except OSError:
        yield  # not a git repo, or unwritable — the caller will find out
        return
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            handle.close()


def _is_private(path: Path) -> bool:
    """Whether *path* opts out of being published by being committed.

    Only consulted when ``git_require_public`` is on, i.e. in a repo where
    pushing means publishing. Unreadable or frontmatter-less files count as
    private — the fail-safe direction.
    """
    if not settings.get("git_require_public"):
        return False
    from . import documents

    try:
        meta, _ = documents.split_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return True
    return str(meta.get("visibility") or "private").strip() != "public"


def _committable(root: Path, paths: List[Path]) -> tuple[List[str], List[str]]:
    """``(addable, why_not)`` as repo-relative paths and human reasons.

    Dropping files is the *normal* case here, not an error — in the public
    template `raw/` is gitignored, so scrap and translate write nothing
    committable. `git add` on an ignored path fails loudly, so they are
    filtered out before it rather than tried and apologised for. The reasons
    are kept because "왜 안 올라갔지" is the first question a skipped push
    raises, and "gitignored" and "marked private" call for different answers.
    """
    relative: List[str] = []
    why_not: List[str] = []
    for path in paths:
        try:
            rel = str(path.resolve().relative_to(root))
        except ValueError:
            why_not.append(f"{path.name}: outside the repo")
            continue
        if _is_private(path):
            why_not.append(f"{rel}: marked private")
            continue
        relative.append(rel)
    if not relative:
        return [], why_not

    proc = subprocess.run(  # noqa: S603
        ["git", "check-ignore", "--", *relative],
        cwd=str(root), capture_output=True, text=True, timeout=60,
    )
    ignored = set((proc.stdout or "").split("\n"))
    why_not += [f"{p}: gitignored" for p in relative if p in ignored]
    return [p for p in relative if p not in ignored], why_not


_GITHUB_RE = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")


def remote_slug(root: Path, remote: str) -> str:
    """``owner/repo`` for *remote*, or "" when it is not a GitHub remote.

    Derived rather than configured so a private fork reports GitHub links
    without anyone remembering to set the repo name.
    """
    url = _run(["remote", "get-url", remote], root=root, check=False)
    match = _GITHUB_RE.search(url.strip())
    return f"{match['owner']}/{match['repo']}" if match else ""


def _branch(root: Path) -> str:
    configured = str(settings.get("git_branch") or "").strip()
    if configured:
        return configured
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], root=root)


def _integrate(root: Path, remote: str, branch: str) -> Optional[str]:
    """Fetch and rebase onto the remote. Returns a reason to skip pushing.

    A conflict leaves the repo mid-rebase, which would break every later run,
    so it is always aborted. The local commit stays — it just does not go out
    until a human resolves the divergence.
    """
    _run(["fetch", remote, branch], root=root)

    behind = _run(
        ["rev-list", "--count", f"HEAD..{remote}/{branch}"], root=root, check=False
    )
    if behind in ("", "0"):
        return None

    proc = subprocess.run(  # noqa: S603
        ["git", "pull", "--rebase", remote, branch],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=float(settings.get("git_timeout")),
    )
    if proc.returncode == 0:
        return None

    subprocess.run(  # noqa: S603 - best effort; leaving a rebase open is worse
        ["git", "rebase", "--abort"],
        cwd=str(root), capture_output=True, text=True, timeout=60,
    )
    detail = (proc.stderr or proc.stdout).strip().splitlines()
    return f"remote diverged and rebase failed: {detail[-1] if detail else 'conflict'}"


def sync(paths: List[Path], message: str) -> Dict[str, Any]:
    """Stage *paths*, commit, integrate, push. Never raises."""
    result: Dict[str, Any] = {"enabled": bool(settings.get("git_autocommit"))}
    if not result["enabled"]:
        return result

    root = settings.wiki_root()
    tracked = [p for p in paths if p.exists()]
    if not tracked:
        result["committed"] = False
        result["reason"] = "nothing written"
        return result

    try:
        with _lock(root):
            _run(["rev-parse", "--git-dir"], root=root)

            addable, why_not = _committable(root, tracked)
            if not addable:
                result["committed"] = False
                result["reason"] = "; ".join(why_not) or "nothing committable"
                return result
            if why_not:
                result["skipped"] = why_not
            _run(["add", "--", *addable], root=root)

            staged = _run(["diff", "--cached", "--name-only", "--", *addable], root=root)
            if not staged:
                result["committed"] = False
                result["reason"] = "unchanged"
                return result

            # Pathspec on the commit, not just the add. Whatever else happens
            # to be staged — a half-finished edit, another tool's work — is not
            # this archive's business to publish.
            _run(["commit", "-m", message, "--", *addable], root=root)
            result["committed"] = True
            result["files"] = staged.splitlines()

            if not settings.get("git_push"):
                result["pushed"] = False
                result["reason"] = "push disabled"
                return result

            remote = str(settings.get("git_remote") or "origin")
            branch = _branch(root)

            blocked = _integrate(root, remote, branch)
            if blocked:
                result["pushed"] = False
                result["reason"] = blocked
                logger.warning("article-archive: not pushing — %s", blocked)
                return result

            _run(["push", remote, f"HEAD:{branch}"], root=root)
            result["pushed"] = True
            result["branch"] = branch
            slug = remote_slug(root, remote)
            if slug:
                # Only set once the push succeeded — a blob URL for a commit
                # that never left the laptop is a 404 with extra steps.
                result["blob_base"] = f"https://github.com/{slug}/blob/{branch}"
    except (_GitError, subprocess.SubprocessError, OSError) as exc:
        # The file is written; git trouble must not look like a failed archive.
        result.setdefault("committed", False)
        result["error"] = str(exc)[:300]
        logger.warning("article-archive: git sync failed: %s", exc)

    return result
