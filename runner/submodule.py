from __future__ import annotations

import contextlib
import hashlib
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

from runner import budget
from runner.errors import ErrorCode, NfclawError
from runner.probes import capture
from runner.settings import seconds

try:
    import fcntl                                  # POSIX file locks (macOS/Linux)
except ImportError:                              # pragma: no cover — Windows has no fcntl
    fcntl = None

REQUIRED_FILES = ("main.nf", "nextflow.config", "nextflow_schema.json")
_GIT_TIMEOUT = 30
_INIT_TIMEOUT = 300
_HEX_RE = re.compile(r"^[0-9a-f]{7,40}$")
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock(key: str) -> threading.Lock:
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _lock_path(repo_root: Path) -> Path:
    """Where the submodule lock lives: in the repository's own git directory, which every process
    initialising this clone's submodules writes to anyway. Never the shared temp directory, where a
    file another user left blocked every first-time run and a planted symlink could redirect it."""
    common = _git(repo_root, "rev-parse", "--git-common-dir")
    if common:
        git_dir = Path(common)
        if not git_dir.is_absolute():
            git_dir = repo_root / git_dir
        if git_dir.is_dir():
            return git_dir / "nfclaw-submodule.lock"
    # Not a git checkout (submodule init will then fail on its own): a per-user temp lock.
    key = hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:16]
    uid = os.getuid() if hasattr(os, "getuid") else 0
    return Path(tempfile.gettempdir()) / f"nfclaw-submodule-{uid}-{key}.lock"


@contextlib.contextmanager
def _init_lock(repo_root: Path):
    """Serialize `git submodule update` across concurrent nfclaw processes on the same repo.
    Without it, parallel inits race on `.git/config` ("could not lock config file"). The lock is an
    flock on a file in the repository's git directory (see `_lock_path`) — it never touches the
    working tree, and it is opened without following symlinks or truncating anything. Thread-only
    where flock is unavailable (Windows)."""
    key = hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:16]
    lock = _thread_lock(key)
    if budget.remaining() is None:
        lock.acquire()
    else:
        while not lock.acquire(timeout=budget.remaining(0.1)):
            budget.check()
    try:
        budget.check()
        if fcntl is None:
            yield
            return
        lock_path = _lock_path(repo_root)
        try:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o666)
        except OSError as exc:
            raise NfclawError(
                ErrorCode.ENVIRONMENT,
                f"Could not open the submodule lock file {lock_path}: {exc.strerror or exc}",
                fix="If no other nfclaw process is running, remove it (it must be a regular file "
                    "you can write), then retry.") from exc
        try:
            if budget.remaining() is None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            else:
                while True:
                    budget.check()
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        time.sleep(budget.remaining(0.1))
            try:
                budget.check()
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    finally:
        lock.release()


@dataclass(frozen=True)
class SubmoduleStatus:
    name: str
    path: Path
    initialized: bool
    complete: bool
    version: str
    commit: str
    missing_files: tuple[str, ...]
    # Advisories about how this tree was resolved (e.g. it is unreleased `dev` code), surfaced to
    # the caller as run warnings. Empty for the pinned release and for any other release tag.
    notes: tuple[str, ...] = ()


def _git_env() -> dict[str, str]:
    """Git setup must fail rather than wait for an interactive credential prompt."""
    return {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def _git(path: Path, *args: str) -> str:
    try:
        out = capture(["git", *args], cwd=str(path), text=False,
                      timeout=seconds("NFCLAW_GIT_TIMEOUT", _GIT_TIMEOUT), env=_git_env())
        out.check_returncode()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""
    return os.fsdecode(out.stdout).rstrip("\n")


def _own_head(path: Path) -> str | None:
    """HEAD of the git repository whose working tree is exactly `path`, or None if there is none.

    An uninitialised submodule is a directory inside the nf-claw checkout, and git run there acts on
    nf-claw itself: its HEAD, its tags, its object store. Any git command aimed at a pipeline tree
    must first confirm the tree is its own repository (a cloned submodule or a version worktree)."""
    if not path.is_dir():
        return None
    # The final LF separates HEAD from the full path, which can itself contain separators.
    out = _git(path, "rev-parse", "--show-toplevel", "HEAD").rsplit("\n", 1)
    if len(out) != 2:
        return None
    try:
        own = Path(out[0]).resolve() == path.resolve()
    except OSError:
        return None
    return out[1] if own else None


def is_git_tree(path: Path) -> bool:
    """Whether `path` is the top of its own git working tree (see `_own_head`)."""
    return _own_head(path) is not None


def resolve_at(name: str, path: Path) -> SubmoduleStatus:
    """Status of a checked-out pipeline tree at an explicit path — works for the pinned
    submodule and for any materialized version worktree alike. The commit and version come only
    from the tree's own repository: a tree that is not one has neither (never nf-claw's)."""
    initialized = path.is_dir() and any(path.iterdir())
    missing = tuple(f for f in REQUIRED_FILES if not (path / f).exists())
    commit = (_own_head(path) or "") if initialized else ""
    version = _git(path, "describe", "--tags", "--always") if commit else ""
    return SubmoduleStatus(
        name=name, path=path, initialized=initialized,
        complete=initialized and not missing,
        version=version, commit=commit, missing_files=missing,
    )


def resolve(name: str, pipelines_dir: Path) -> SubmoduleStatus:
    st = resolve_at(name, pipelines_dir / name / "upstream")
    pinned = _committed_pin(pipelines_dir / name / "skill.md")
    if (pinned and st.commit and st.commit == pinned.get("commit")
            and _looks_like_commit_version(st.version, st.commit)):
        # A shallow clone without its tag describes itself by commit; the committed docs name
        # the release that commit is.
        return replace(st, version=pinned["version"])
    return st


def _looks_like_commit_version(version: str, commit: str) -> bool:
    return bool(version and _HEX_RE.match(version) and commit.startswith(version))


def _committed_pin(skill_md: Path) -> dict[str, str] | None:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    frontmatter = text.split("---", 2)[1]
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() in {"version", "commit"}:
            data[key.strip()] = value.strip()
    return data if data.get("version") and data.get("commit") else None


def modified_files(path: Path) -> list[str]:
    """Tracked files of the tree's own repository whose working bytes differ from its HEAD.

    Empty for a tree that is not its own git repository (a copied fixture has no HEAD to differ
    from; provenance still hashes its bytes). Raises NfclawError when git cannot answer, so an
    unverifiable tree is never treated as unmodified."""
    if _own_head(path) is None:
        return []
    try:
        result = capture(["git", "status", "--porcelain=v1", "-z", "--untracked-files=no",
                          "--ignore-submodules=all"], cwd=str(path),
                         timeout=seconds("NFCLAW_GIT_TIMEOUT", _GIT_TIMEOUT), env=_git_env())
        result.check_returncode()
        out = result.stdout
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Could not check {path} for local modifications: {exc}",
            fix="Make sure git works in that directory, then retry.") from exc
    files: list[str] = []
    entries = iter(out.split("\x00"))
    for entry in entries:
        if not entry:
            continue
        files.append(entry[3:])
        if entry[0] in "RC":                      # a rename/copy carries its source path next
            next(entries, None)
    return files


def tree_issues(st: SubmoduleStatus, pin_doc: Path | None) -> list[str]:
    """Why the tree `st` is not the unmodified code its label (and its docs) claim, or [].

    The pinned submodule must sit at the commit its committed `skill.md` (`pin_doc`) documents: a
    `git pull` that moves the pin without `git submodule update` otherwise runs a different release
    than the one the agent read about — under the old release's schema, silently. Any tree nfclaw
    runs — the pin, a release cache, a `dev` commit — must also be free of local edits to tracked
    files, because provenance names it by its release and commit."""
    issues: list[str] = []
    pinned = _committed_pin(pin_doc) if pin_doc is not None else None
    actual_head = _own_head(st.path)
    if st.commit and actual_head != st.commit:
        issues.append(f"{st.path}: pipeline code identity changed or cannot be verified; "
                      f"resolved {st.commit}, current Git HEAD {actual_head or 'unavailable'}")
    elif pinned and not actual_head:
        issues.append(f"{st.path}: cannot verify the Git identity of the documented pipeline code")
    if pinned and st.commit and st.commit != pinned["commit"]:
        found = _git(st.path, "describe", "--tags", "--always") or st.commit[:12]
        issues.append(
            f"pipelines/{st.name}/upstream is checked out at {found} ({st.commit[:12]}), but this "
            f"nf-claw checkout pins nf-core/{st.name} {pinned['version']} "
            f"({pinned['commit'][:12]}) — the release its skill.md and reference.md describe")
    if changed := modified_files(st.path):
        shown = ", ".join(changed[:5]) + (f" and {len(changed) - 5} more"
                                          if len(changed) > 5 else "")
        issues.append(f"{st.path} has local modifications to tracked pipeline files ({shown}); "
                      f"nfclaw runs releases unmodified")
    return issues


def ensure_initialized(name: str, pipelines_dir: Path, repo_root: Path) -> SubmoduleStatus:
    st = resolve(name, pipelines_dir)
    if not st.complete:
        rel = f"pipelines/{name}/upstream"
        with _init_lock(repo_root):
            st = resolve(name, pipelines_dir)  # re-check: another run may have just done it
            if not st.complete:
                try:
                    result = capture(
                        ["git", "submodule", "update", "--init", "--depth", "1", rel],
                        cwd=str(repo_root), timeout=seconds("NFCLAW_INIT_TIMEOUT", _INIT_TIMEOUT),
                        env=_git_env(),
                    )
                    result.check_returncode()
                except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
                    detail = getattr(exc, "stderr", "") or str(exc)
                    raise NfclawError(
                        ErrorCode.SUBMODULE_INCOMPLETE,
                        f"Could not initialize pipeline '{name}' submodule.",
                        fix=f"Check network access, then run: git submodule update --init {rel}",
                        details={"git_error": detail.strip()},
                    ) from exc
                st = resolve(name, pipelines_dir)
    if not st.complete:
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Pipeline '{name}' submodule is incomplete.",
            fix=f"Run: git submodule update --init pipelines/{name}/upstream",
            details={"missing": list(st.missing_files)},
        )
    return st
