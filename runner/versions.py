"""Resolve and materialize a *specific* version of a pipeline: a release, or unreleased `dev`.

`nfclaw` pins each pipeline's submodule to its latest release. This module lets a
user run any other published release tag instead: it validates the requested tag
against the real upstream tags, checks it out into a git-ignored per-version cache
(a worktree sharing the submodule's object store), and returns a `SubmoduleStatus`
pointing at that tree — the same value the rest of the runner already consumes for
the pinned version. The default (no version) path is unchanged.

`dev` is the one non-release accepted: every nf-core pipeline develops on a `dev` branch and
releases from it, so it holds the code that is not released yet (Nextflow's `-r dev`). A branch
moves, so it is resolved to its current head commit on every request and materialized as an
immutable per-commit tree (`.versions/dev-<commit>/`): a replay or a concurrent run never sees the
code change under it, and provenance records exactly which commit ran.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

from runner import discovery
from runner import submodule as submod
from runner.errors import ErrorCode, NfclawError
from runner.probes import capture
from runner.settings import seconds
from runner.submodule import SubmoduleStatus

CACHE_DIRNAME = ".versions"
DEV_BRANCH = "dev"
# Where the submodule clone remembers the last `dev` head nfclaw resolved: the conventional
# remote-tracking ref, so `git log origin/dev` works there too. It is the offline fallback.
_DEV_TRACKING_REF = f"refs/remotes/origin/{DEV_BRANCH}"
# A release tag: `X.Y.Z`, or the `X.Y` nf-core used before settling on three parts (fetchngs
# 1.0–1.9, sarek 2.5–2.7, rnaseq 1.0–3.9, …). `dev`, release candidates and other refs are
# not releases.
_RELEASE_TAG = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_GIT_TIMEOUT = 120


# --- discovering which versions exist ---------------------------------------

def _url_for(name: str, repo_root: Path) -> str | None:
    """The submodule's git URL from `.gitmodules` — read offline, no git needed."""
    try:
        text = (repo_root / ".gitmodules").read_text(encoding="utf-8")
    except OSError:
        return None
    section = f'[submodule "pipelines/{name}/upstream"]'
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != section:
            continue
        for follow in lines[i + 1:]:
            s = follow.strip()
            if s.startswith("["):                      # next section — url not in this one
                break
            if s.startswith("url"):
                return s.split("=", 1)[1].strip()
    return None


def remote_tags(url: str) -> list[str]:
    """Tag names published by the upstream remote (empty on any failure — caller falls back)."""
    try:
        r = capture(["git", "ls-remote", "--tags", "--refs", "--", url],
                    timeout=seconds("NFCLAW_GIT_TIMEOUT", 60), env=submod._git_env())
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return []
    if r.returncode != 0:
        return []
    return [line.split("\t")[-1].rsplit("/", 1)[-1] for line in r.stdout.splitlines()]


def _local_tags(upstream: Path) -> list[str]:
    """Tags already present in the (initialized) submodule clone — the offline fallback. None for
    an uninitialised submodule: git run in its empty directory would list nf-claw's own tags."""
    if not submod.is_git_tree(upstream):
        return []
    out = submod._git(upstream, "tag", "--list")
    return out.splitlines() if out else []


def _release_key(tag: str) -> tuple[int, ...]:
    m = _RELEASE_TAG.match(tag)
    return tuple(int(x) for x in m.groups(default="0")) if m else (0, 0, 0)


def release_tags(name: str, *, pipelines_dir: Path, repo_root: Path) -> list[str]:
    """Every release tag (`X.Y.Z` or `X.Y`) for the pipeline, newest first.

    Union of the remote's tags and any already fetched locally, so it still returns
    a useful list when the network is unavailable. Other refs (dev, rc, …) are
    dropped — only immutable releases are runnable as a tag.
    """
    url = _url_for(name, repo_root)
    tags = list(remote_tags(url)) if url else []
    tags += _local_tags(pipelines_dir / name / "upstream")
    releases = {t for t in tags if _RELEASE_TAG.match(t)}
    return sorted(releases, key=_release_key, reverse=True)


def available(name: str, *, pipelines_dir: Path, repo_root: Path) -> list[tuple[str, bool]]:
    """`(tag, is_pin)` for every release, newest first. The pin is the committed
    (latest) version from the pipeline's skill.md — known offline, no init required."""
    pipeline = discovery.find(name, pipelines_dir)             # 404 if unknown
    pin = pipeline.frontmatter.get("version", "").lstrip("v")
    tags = release_tags(name, pipelines_dir=pipelines_dir, repo_root=repo_root)
    return [(t, t.lstrip("v") == pin) for t in tags]


# --- resolving a requested version to a canonical tag -----------------------

def _match_tag(version: str, tags: list[str]) -> str | None:
    """The actual tag matching the user's input, tolerating a leading 'v' on either side."""
    want = version.strip().lstrip("v")
    for tag in tags:
        if tag.lstrip("v") == want:
            return tag
    return None


def resolve(name: str, version: str, *, pipelines_dir: Path, repo_root: Path) -> str:
    """Validate `version` against the real release tags, returning the canonical tag.
    Raises VERSION_NOT_FOUND (listing what is available) for anything else."""
    tags = release_tags(name, pipelines_dir=pipelines_dir, repo_root=repo_root)
    match = _match_tag(version, tags)
    if match is None:
        raise NfclawError(
            ErrorCode.VERSION_NOT_FOUND,
            f"'{version}' is not a released version of nf-core/{name}.",
            fix=f"Pick an available version (see `nfclaw versions {name}`), use "
                f"`{DEV_BRANCH}` for the unreleased development branch, "
                "or omit --pipeline-version to use the pinned latest.",
            details={"available": tags or ["(none found — check network connectivity)"]},
        )
    return match


# --- the unreleased development branch (`dev`) --------------------------------

class RemoteUnavailable(Exception):
    """The upstream remote could not be queried (network, DNS, proxy, missing git)."""


def is_dev_request(version: str | None) -> bool:
    """True when `--pipeline-version` asks for the development branch rather than a release."""
    return version is not None and version.strip().lower() == DEV_BRANCH


def dev_label(commit: str) -> str:
    """The cache directory name of one `dev` commit. Keyed by commit, not by branch, so a tree is
    immutable once materialized: a later `dev` head lands beside it instead of replacing it."""
    return f"{DEV_BRANCH}-{commit[:12]}"


def remote_branch_head(url: str, branch: str) -> str | None:
    """The commit `branch` points at on the remote, or None when the remote has no such branch.
    Raises RemoteUnavailable when the remote cannot be queried — distinct from "no branch", so a
    network failure is never reported as a missing `dev` branch (or the reverse)."""
    try:
        r = capture(["git", "ls-remote", "--heads", "--", url, f"refs/heads/{branch}"],
                    timeout=seconds("NFCLAW_GIT_TIMEOUT", 60), env=submod._git_env())
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        raise RemoteUnavailable(str(exc)) from exc
    if r.returncode != 0:
        raise RemoteUnavailable(r.stderr.strip() or f"git ls-remote exited {r.returncode}")
    for line in r.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.strip() == f"refs/heads/{branch}" and _COMMIT.match(sha.strip()):
            return sha.strip()
    return None


def _local_dev_head(upstream: Path) -> str:
    """The last `dev` head nfclaw fetched into the submodule clone ("" if none).

    Only asked of an initialized clone: in an empty submodule directory git would walk up and
    answer for the enclosing nf-claw repository, whose `origin/dev` is not the pipeline's."""
    if not submod.is_git_tree(upstream):
        return ""
    sha = submod._git(upstream, "rev-parse", "-q", "--verify", f"{_DEV_TRACKING_REF}^{{commit}}")
    return sha if _COMMIT.match(sha) else ""


def dev_head(name: str, *, pipelines_dir: Path, repo_root: Path) -> tuple[str | None, bool]:
    """`(commit, fresh)` for the pipeline's `dev` branch.

    `fresh` is True when the remote answered: `commit` is then its current head, or None when the
    pipeline has no `dev` branch at all. When the remote cannot be reached, `fresh` is False and
    `commit` is the last head nfclaw fetched (None if it never fetched one) — the offline fallback,
    mirroring Nextflow, which runs its local copy of a revision when it cannot reach the remote."""
    url = _url_for(name, repo_root)
    if url:
        try:
            return remote_branch_head(url, DEV_BRANCH), True
        except RemoteUnavailable:
            pass
    return _local_dev_head(pipelines_dir / name / "upstream") or None, False


def _has_commit(upstream: Path, sha: str) -> bool:
    return bool(submod._git(upstream, "rev-parse", "-q", "--verify", f"{sha}^{{commit}}"))


def _fetch_dev(upstream: Path) -> None:
    """Fetch the remote's current `dev` head (one commit deep) into the tracking ref."""
    result = capture(
        ["git", "-C", str(upstream), "fetch", "--depth", "1", "origin",
         f"+refs/heads/{DEV_BRANCH}:{_DEV_TRACKING_REF}"],
        timeout=seconds("NFCLAW_GIT_TIMEOUT", _GIT_TIMEOUT), env=submod._git_env())
    result.check_returncode()


def _record_dev_head(upstream: Path, sha: str) -> None:
    """Remember `sha` as the last-resolved `dev` head (the offline fallback). Best effort: the
    tree is already materialized, so failing to record it must not fail the run."""
    capture(["git", "-C", str(upstream), "update-ref", _DEV_TRACKING_REF, sha],
            timeout=seconds("NFCLAW_GIT_TIMEOUT", 30), env=submod._git_env())


def _dev_advisory(name: str, commit: str) -> str:
    return (f"nf-core/{name}@{DEV_BRANCH} is unreleased development code (commit {commit}). "
            f"The `{DEV_BRANCH}` branch moves, so a later `--pipeline-version {DEV_BRANCH}` run "
            "may execute different code; provenance records this commit and `commands.sh` replays "
            "exactly it. Use a release for results you need to reproduce from a version number.")


def materialize_dev(name: str, *, pipelines_dir: Path, repo_root: Path) -> SubmoduleStatus:
    """Resolve the pipeline's `dev` branch to a commit and ensure that commit is checked out at
    `cache_dir(name, dev_label(commit))/upstream`. Returns its status, labelled `dev`, with the
    advisories a caller must surface (unreleased code; stale head when offline)."""
    upstream = pipelines_dir / name / "upstream"
    _require_own_clone(name, upstream, f"nf-core/{name}@{DEV_BRANCH}")
    commit, fresh = dev_head(name, pipelines_dir=pipelines_dir, repo_root=repo_root)
    if commit is None:
        if fresh:
            raise NfclawError(
                ErrorCode.VERSION_NOT_FOUND,
                f"nf-core/{name} has no '{DEV_BRANCH}' branch to run.",
                fix=f"Pick a release (see `nfclaw versions {name}`), or omit --pipeline-version "
                    "to use the pinned latest.")
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Could not reach the nf-core/{name} remote to resolve its '{DEV_BRANCH}' branch, and "
            "no development commit has been fetched before.",
            fix="Check git/network access (the remote is in .gitmodules) and retry; once one "
                f"`--pipeline-version {DEV_BRANCH}` run has fetched it, later runs work offline.")
    try:
        with submod._init_lock(repo_root):
            dest = cache_dir(name, dev_label(commit), pipelines_dir) / "upstream"
            st = submod.resolve_at(name, dest)
            if not st.complete:
                if not _has_commit(upstream, commit):
                    _fetch_dev(upstream)
                    fetched = _local_dev_head(upstream)
                    if fetched and fetched != commit:
                        # `dev` moved between resolving it and fetching it: the fetched head is the
                        # newer development code that was asked for, so run that one.
                        commit = fetched
                        dest = cache_dir(name, dev_label(commit), pipelines_dir) / "upstream"
                        st = submod.resolve_at(name, dest)
                if not st.complete:
                    _add_worktree(upstream, dest, commit)
                    st = submod.resolve_at(name, dest)
            if st.complete:
                _check_cache_commit(st, commit, f"{DEV_BRANCH} commit {commit}")
            if fresh and st.complete:
                _record_dev_head(upstream, commit)
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Could not materialize nf-core/{name}@{DEV_BRANCH} (commit {commit}).",
            fix="Check git/network access and retry; the version cache is safe to recreate.",
            details={"git_error": detail.strip()},
        ) from exc
    if not st.complete:
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Materialized tree for nf-core/{name}@{DEV_BRANCH} (commit {commit}) is incomplete.",
            fix="The development branch may be mid-restructure; use a release instead.",
            details={"missing": list(st.missing_files)})
    notes = [_dev_advisory(name, st.commit or commit)]
    if not fresh:
        notes.insert(0, f"could not reach the nf-core/{name} remote to resolve the current "
                        f"'{DEV_BRANCH}' head; running the last one fetched ({commit[:12]}), "
                        "which may be behind the remote.")
    return replace(st, version=DEV_BRANCH, notes=tuple(notes))


# --- materializing a version into the per-version cache ---------------------

def _require_own_clone(name: str, upstream: Path, what: str) -> None:
    """Refuse a pinned tree that is not its own git clone. Every version cache — a release or a
    `dev` commit — is a worktree of that clone, and in a tree that is not one (copied files) every
    git command would act on the enclosing nf-claw checkout: fetch into it, shallow it, and
    register the cache as a worktree of it."""
    if not submod.is_git_tree(upstream):
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"pipelines/{name}/upstream is not a git checkout, so {what} cannot be "
            "fetched from it.",
            fix=f"Re-initialise it: git submodule update --init pipelines/{name}/upstream")


def cache_dir(name: str, tag: str, pipelines_dir: Path) -> Path:
    return pipelines_dir / name / CACHE_DIRNAME / tag


def is_cached(st: SubmoduleStatus) -> bool:
    """True when the status points at a materialized version, not the pinned submodule."""
    return CACHE_DIRNAME in st.path.parts


def _has_tag(upstream: Path, tag: str) -> bool:
    return bool(submod._git(upstream, "rev-parse", "-q", "--verify", f"refs/tags/{tag}"))


def _fetch_tag(upstream: Path, tag: str) -> None:
    result = capture(
        ["git", "-C", str(upstream), "fetch", "--depth", "1", "origin",
         f"refs/tags/{tag}:refs/tags/{tag}"],
        timeout=seconds("NFCLAW_GIT_TIMEOUT", _GIT_TIMEOUT), env=submod._git_env())
    result.check_returncode()


def _add_worktree(upstream: Path, dest: Path, rev: str) -> None:
    """Check `rev` (a `tags/<tag>` or a commit) out at `dest` as a detached worktree."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    capture(["git", "-C", str(upstream), "worktree", "prune"],
            timeout=seconds("NFCLAW_GIT_TIMEOUT", 30), env=submod._git_env())
    if dest.exists():                                          # stale/partial — start clean
        shutil.rmtree(dest)
    result = capture(
        ["git", "-C", str(upstream), "worktree", "add", "--force", "--detach",
         str(dest), rev],
        timeout=seconds("NFCLAW_GIT_TIMEOUT", _GIT_TIMEOUT), env=submod._git_env())
    result.check_returncode()


def _check_cache_commit(st: SubmoduleStatus, expected: str, label: str) -> None:
    """A complete cache is reusable only when its own Git HEAD is the requested revision.
    Preserve a mismatched tree: replacing it could discard the user's local changes."""
    if not expected or st.commit != expected:
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Version cache {st.path} does not match nf-core/{st.name}@{label}: "
            f"expected {expected or '(unresolved commit)'}, found {st.commit or '(no Git HEAD)'}.",
            fix="Preserve any local changes, move this version's cache directory aside, then "
                "retry. nfclaw will recreate the requested revision without overwriting that tree.")


def materialize(name: str, tag: str, *, pipelines_dir: Path, repo_root: Path) -> SubmoduleStatus:
    """Ensure `tag` is checked out at `cache_dir(name, tag)/upstream` and return its status.
    Reuses the submodule's object store; fetches the tag only if it isn't present yet."""
    upstream = pipelines_dir / name / "upstream"
    dest = cache_dir(name, tag, pipelines_dir) / "upstream"
    _require_own_clone(name, upstream, f"nf-core/{name}@{tag}")
    # Reuse the repository-wide git mutation lock: parallel agents may ask for the same release,
    # and git worktree registration plus cache replacement are not safe to race. Rebuild any
    # partial cache rather than treating the presence of main.nf alone as proof it is complete.
    try:
        with submod._init_lock(repo_root):
            st = submod.resolve_at(name, dest)
            if not _has_tag(upstream, tag):
                _fetch_tag(upstream, tag)
            expected = submod._git(upstream, "rev-parse", "-q", "--verify",
                                   f"refs/tags/{tag}^{{commit}}")
            if not st.complete:
                _add_worktree(upstream, dest, f"tags/{tag}")
                st = submod.resolve_at(name, dest)
            if st.complete:
                _check_cache_commit(st, expected, tag)
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Could not materialize nf-core/{name}@{tag}.",
            fix="Check git/network access and retry; the version cache is safe to recreate.",
            details={"git_error": detail.strip()},
        ) from exc
    if not st.complete:
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            f"Materialized tree for nf-core/{name}@{tag} is incomplete.",
            fix="The release may be missing required files; try a different version.",
            details={"missing": list(st.missing_files)})
    return replace(st, version=tag)                           # the tag is the authoritative version


# --- the single entry point the runner uses --------------------------------

def ensure(name: str, version: str | None, *, pipelines_dir: Path,
           repo_root: Path) -> SubmoduleStatus:
    """Status for the tree to run: the pinned submodule when `version` is None or equals
    the pin, the current `dev` head when `version` is `dev`, otherwise the requested release
    materialized into the cache."""
    if version is None:
        return submod.ensure_initialized(name, pipelines_dir, repo_root)
    # The pinned clone is the object store every other version's worktree shares, so it is
    # initialized first for a release and for `dev` alike.
    base = submod.ensure_initialized(name, pipelines_dir, repo_root)
    if is_dev_request(version):
        return materialize_dev(name, pipelines_dir=pipelines_dir, repo_root=repo_root)
    if (_RELEASE_TAG.fullmatch(version)
            and version.lstrip("v") == base.version.lstrip("v")):
        return base  # ensure_initialized already verified the local documented pin
    tag = resolve(name, version, pipelines_dir=pipelines_dir, repo_root=repo_root)
    if tag.lstrip("v") == base.version.lstrip("v"):
        return base                                            # requested == pin → no cache needed
    return materialize(name, tag, pipelines_dir=pipelines_dir, repo_root=repo_root)


# --- on-demand docs for a materialized version -----------------------------

def generate_docs(st: SubmoduleStatus, *, dest_dir: Path) -> tuple[Path, Path]:
    """Write `skill.md`/`reference.md` for a version's tree, reusing the librarian's
    renderer. Imported lazily so the runtime never hard-depends on the librarian."""
    from librarian import write_skill  # lazy: avoid runner→librarian coupling
    version = st.version if is_cached(st) else None  # version-aware commands only for a cache
    skill_text, ref_text = write_skill.render_status(st, pipeline_version=version)
    dest_dir.mkdir(parents=True, exist_ok=True)
    skill_path = dest_dir / "skill.md"
    ref_path = dest_dir / "reference.md"
    skill_path.write_text(skill_text, encoding="utf-8")
    ref_path.write_text(ref_text, encoding="utf-8")
    return skill_path, ref_path
