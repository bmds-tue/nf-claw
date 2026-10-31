"""Discover nf-core pipelines not yet in the library and scaffold them.

Reads the public nf-core pipeline index (no token required), finds pipelines
with a stable release that are not already in `sources.tsv`, and for each one:
adds the upstream submodule pinned to its latest release, generates the agent
context (`skill.md` / `reference.md`), and appends a `latest-release` row to
`sources.tsv`. A failed pipeline is rolled back and never blocks the others.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from librarian import write_skill
from librarian.add_pipeline import read_sources, valid_pipeline_name, validate_pipeline_name
from runner import execution, submodule
from runner.probes import capture
from runner.atomic import write_bytes

NFCORE_PIPELINES_JSON = "https://nf-co.re/pipelines.json"
_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def latest_stable(releases: list[dict]) -> str | None:
    """Highest semver tag among a pipeline's releases (ignores `dev`, rc, etc.)."""
    parsed = [
        (tuple(int(x) for x in m.groups()), r.get("tag_name", ""))
        for r in releases
        if (m := _SEMVER.match(r.get("tag_name", "")))
    ]
    return max(parsed)[1] if parsed else None


def fetch_catalog() -> list[dict]:
    """Fetch the public nf-core pipeline index (no token required)."""
    req = urllib.request.Request(NFCORE_PIPELINES_JSON, headers={"User-Agent": "nf-claw-discover"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # a fixed https URL
        return json.load(resp).get("remote_workflows", [])


def candidates(workflows: list[dict]) -> list[tuple[str, str, str]]:
    """(name, git url, latest stable tag) for live, runnable pipelines.

    Only DSL2 pipelines are eligible: DSL1 was removed in Nextflow 22.12, so a
    DSL1 pipeline cannot run on any supported engine and has no place in an
    agent-runnable library.
    """
    out: list[tuple[str, str, str]] = []
    for wf in workflows:
        if wf.get("archived") or wf.get("disabled"):
            continue
        if wf.get("is_DSL2") is False:  # DSL1 — not runnable on a modern Nextflow
            continue
        name = wf.get("name")
        tag = latest_stable(wf.get("releases", []))
        if not name or not valid_pipeline_name(str(name)) or not tag:
            continue
        name = str(name)
        # The discovery feed is metadata, not an authority to select an arbitrary repository.
        # nf-claw only wraps nf-core pipelines, so derive the origin from the validated slug
        # instead of trusting a mutable `full_name` field from the remote JSON.
        out.append((name, f"https://github.com/nf-core/{name}.git", tag))
    return sorted(out)


def new_pipelines(
    workflows: list[dict], existing: set[str]
) -> list[tuple[str, str, str]]:
    """Candidates whose name is not already tracked in sources.tsv."""
    return [c for c in candidates(workflows) if c[0] not in existing]


def _run(args: list[str], *, check: bool = False,
         timeout: float = 60) -> subprocess.CompletedProcess:
    result = capture(args, timeout=timeout, env=submodule._git_env())
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, args,
                                            output=result.stdout, stderr=result.stderr)
    return result


def _rollback(name: str, repo_root: Path) -> None:
    name = validate_pipeline_name(name)
    rel = f"pipelines/{name}/upstream"
    _run(["git", "-C", str(repo_root), "submodule", "deinit", "-f", rel])
    _run(["git", "-C", str(repo_root), "rm", "-f", rel])
    shutil.rmtree(repo_root / "pipelines" / name, ignore_errors=True)
    # `.git` is a file in a linked worktree. Ask Git for the real administrative path so failed
    # discovery is cleaned up correctly for both ordinary clones and agent worktrees.
    git_path = _run(["git", "-C", str(repo_root), "rev-parse", "--git-path",
                     f"modules/{rel}"])
    if git_path.returncode == 0 and git_path.stdout.strip():
        modules_dir = Path(git_path.stdout.strip())
        if not modules_dir.is_absolute():
            modules_dir = repo_root / modules_dir
        shutil.rmtree(modules_dir, ignore_errors=True)


@dataclass(frozen=True)
class _GitmodulesSnapshot:
    content: bytes | None
    permissions: int | None
    indexed: tuple[str, str] | None
    assume_unchanged: bool = False
    skip_worktree: bool = False
    intent_to_add: bool = False


def _gitmodules_snapshot(repo_root: Path) -> _GitmodulesSnapshot:
    path = repo_root / ".gitmodules"
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        content, permissions = None, None
    else:
        if not stat.S_ISREG(mode):
            raise ValueError(".gitmodules must be a regular file before discovery")
        content, permissions = path.read_bytes(), stat.S_IMODE(mode)
    result = _run(["git", "-C", str(repo_root), "ls-files", "--stage", "-z", "--", ".gitmodules"],
                  check=True)
    entries = [entry for entry in result.stdout.split("\0") if entry]
    if not entries:
        return _GitmodulesSnapshot(content, permissions, None)
    if len(entries) != 1:
        raise ValueError(".gitmodules has unresolved index entries")
    mode, digest, stage = entries[0].partition("\t")[0].split()
    if stage != "0" or mode not in {"100644", "100755"}:
        raise ValueError(".gitmodules has an unsupported index entry")
    indexed = mode, digest
    flags = _run(["git", "-C", str(repo_root), "ls-files", "-v", "-z", "--", ".gitmodules"],
                 check=True).stdout
    if flags not in {f"{tag} .gitmodules\0" for tag in "HhSs"}:
        raise ValueError("cannot inspect .gitmodules index flags")
    diffs = [_run(["git", "-C", str(repo_root), "diff", "--cached", "--raw", "-z",
                   "--no-ext-diff", "--no-textconv", f"--ita-{visibility}-in-index", "--",
                   ".gitmodules"],
                  check=True).stdout for visibility in ("visible", "invisible")]
    return _GitmodulesSnapshot(content, permissions, indexed, flags[0].islower(),
                               flags[0].upper() == "S", diffs[0] != diffs[1])


def _restore_gitmodules(repo_root: Path, snapshot: _GitmodulesSnapshot) -> None:
    path = repo_root / ".gitmodules"
    if snapshot.content is None:
        path.unlink(missing_ok=True)
    else:
        write_bytes(path, snapshot.content, mode=snapshot.permissions)
    # Restore only this index entry, preserving other staged files and the distinction
    # between the original staged metadata and its possibly different working bytes.
    if snapshot.indexed is None:
        _run(["git", "-C", str(repo_root), "update-index", "--force-remove", "--", ".gitmodules"],
             check=True)
    else:
        mode, digest = snapshot.indexed
        _run(["git", "-C", str(repo_root), "update-index", "--add", "--cacheinfo",
              f"{mode},{digest},.gitmodules"], check=True)
        if snapshot.intent_to_add:
            _run(["git", "-C", str(repo_root), "reset", "-N", "--", ".gitmodules"], check=True)
        for flag, enabled in (("assume-unchanged", snapshot.assume_unchanged),
                              ("skip-worktree", snapshot.skip_worktree)):
            _run(["git", "-C", str(repo_root), "update-index",
                  "--" + ("" if enabled else "no-") + flag, "--", ".gitmodules"], check=True)


def add_one(name: str, url: str, tag: str, repo_root: Path) -> bool:
    """Add one pipeline submodule pinned to `tag` and generate its context."""
    name = validate_pipeline_name(name)
    try:
        # Share the runner's lock: discovery and on-demand initialization both mutate Git's
        # submodule configuration. Recheck ownership while holding it through rollback.
        with execution.stop_on_signals(), submodule._init_lock(repo_root):
            return _add_one(name, url, tag, repo_root)
    except Exception as exc:
        print(f"{name}: ERROR {exc}; discovery did not complete")
        return False


def _add_one(name: str, url: str, tag: str, repo_root: Path) -> bool:
    name = validate_pipeline_name(name)
    entry = repo_root / "pipelines" / name
    # A failed add rolls back only a tree this invocation owns. Discovery can encounter
    # orphaned entries absent from sources.tsv; never remove their research data or links.
    if entry.exists() or entry.is_symlink():
        print(f"{name}: ERROR pipeline entry already exists: {entry}; preserved without changes")
        return False
    relative = f"pipelines/{name}/upstream"
    if entry.parent.is_symlink():
        raise ValueError(f"pipeline parent is a symlink: {entry.parent}; preserved without changes")
    own_root = _run(["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"], check=True)
    if Path(own_root.stdout.rstrip("\n")).resolve() != repo_root.resolve():
        raise ValueError(f"discovery root is not the repository root: {repo_root}")
    git_path = _run(["git", "-C", str(repo_root), "rev-parse", "--git-path",
                     f"modules/{relative}"], check=True)
    administrative = Path(git_path.stdout.rstrip("\n"))
    if not administrative.is_absolute():
        administrative = repo_root / administrative
    indexed = _run(["git", "-C", str(repo_root), "ls-files", "-z", "--", relative], check=True)
    registered = _run(["git", "-C", str(repo_root), "config", "-z", "-f", ".gitmodules",
                       "--get-regexp", r"^submodule\..*\.path$"])
    if registered.returncode not in (0, 1):
        raise ValueError("cannot inspect existing submodule registrations")
    registered_path = False
    for record in registered.stdout.split("\0"):
        if not record:
            continue
        _, separator, value = record.partition("\n")
        if not separator:
            raise ValueError("cannot parse existing submodule registrations")
        if (repo_root / value).resolve() == (entry / "upstream").resolve():
            registered_path = True
    named_registration = False
    pattern = r"^submodule\." + re.escape(relative) + r"\."
    for scope in (("-f", ".gitmodules"), ("--local",)):
        result = _run(["git", "-C", str(repo_root), "config", "-z", *scope,
                       "--get-regexp", pattern])
        if result.returncode not in (0, 1):
            raise ValueError("cannot inspect existing named submodule configuration")
        named_registration |= result.returncode == 0
    if (administrative.exists() or administrative.is_symlink() or indexed.stdout
            or registered_path or named_registration):
        print(f"{name}: ERROR existing submodule registration, index or object store; "
              "preserved without changes")
        return False
    # Exclusive creation prevents another owner appearing between the filesystem check and
    # Git's add. Only after reserving this entry may failure cleanup remove it.
    metadata = _gitmodules_snapshot(repo_root)
    entry.mkdir(parents=True, exist_ok=False)
    up = entry / "upstream"
    try:
        _run(
            ["git", "-C", str(repo_root), "submodule", "add", "--force", url,
             f"pipelines/{name}/upstream"],
            check=True, timeout=300,
        )
        _run(["git", "-C", str(up), "fetch", "--tags", "--depth", "1", "origin",
              f"refs/tags/{tag}:refs/tags/{tag}"], check=True, timeout=300)
        _run(["git", "-C", str(up), "checkout", f"tags/{tag}"], check=True)
        # `submodule add` records the gitlink at the default branch HEAD; re-stage it at the
        # tag we just checked out so the pin IS the release. Otherwise a later
        # `git submodule update` resets the working tree off the tag, `git describe --tags`
        # returns `<tag>-N-g<hash>`, and the drift gate flags the generated context as stale.
        _run(["git", "-C", str(repo_root), "add", f"pipelines/{name}/upstream"], check=True)
        write_skill.generate(name, pipelines_dir=repo_root / "pipelines")
        return True
    except BaseException as exc:
        print(f"{name}: ERROR {exc or type(exc).__name__}; rolling back")
        try:
            _rollback(name, repo_root)
        finally:
            _restore_gitmodules(repo_root, metadata)
        if not isinstance(exc, Exception):
            raise
        return False


def _remove_source(sources_path: Path, name: str) -> None:
    """Drop the row for `name` from sources.tsv (keeps comments and others)."""
    name = validate_pipeline_name(name)
    if not sources_path.exists():
        return
    kept = [
        line for line in sources_path.read_text(encoding="utf-8").splitlines()
        if not (line.strip() and not line.startswith("#")
                and (line.split("\t")[0] if "\t" in line else line.split()[0]).strip() == name)
    ]
    sources_path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def remove_one(name: str, repo_root: Path, sources_path: Path) -> None:
    """Completely remove a pipeline: its submodule, generated files and source row."""
    name = validate_pipeline_name(name)
    with execution.stop_on_signals(), submodule._init_lock(repo_root):
        _rollback(name, repo_root)
        _run(["git", "-C", str(repo_root), "config", "-f", ".gitmodules",
              "--remove-section", f"submodule.pipelines/{name}/upstream"])
        _run(["git", "-C", str(repo_root), "add", ".gitmodules"])
        _remove_source(sources_path, name)


def _append_source(sources_path: Path, name: str, url: str) -> None:
    name = validate_pipeline_name(name)
    text = sources_path.read_text(encoding="utf-8")
    sep = "" if text.endswith("\n") or not text else "\n"
    with sources_path.open("a", encoding="utf-8") as f:
        f.write(f"{sep}{name}\t{url}\tlatest-release\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="librarian.discover_pipelines")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--sources", default="sources.tsv")
    parser.add_argument("--limit", type=int, default=12,
                        help="max new pipelines to add per run (0 = no limit)")
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be added without changing anything")
    parser.add_argument("--rollback", nargs="+", metavar="NAME",
                        help="remove the named pipeline(s) entirely, then exit")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    sources_path = Path(args.sources)
    if not sources_path.is_absolute():
        sources_path = root / sources_path

    if args.rollback:
        for name in args.rollback:
            remove_one(name, root, sources_path)
            print(f"{name}: removed")
        return 0

    existing = {s.name for s in read_sources(sources_path)}
    fresh = new_pipelines(fetch_catalog(), existing)
    if args.limit > 0:
        fresh = fresh[: args.limit]

    if not fresh:
        print("No new nf-core pipelines to add.")
        return 0

    print(f"{len(fresh)} new pipeline(s) to add:")
    for name, url, tag in fresh:
        print(f"  {name}\t{tag}\t{url}")
    if args.dry_run:
        return 0

    added = 0
    for name, url, tag in fresh:
        if add_one(name, url, tag, root):
            _append_source(sources_path, name, url)
            added += 1
            print(f"{name}: added at {tag}")
    print(f"Added {added}/{len(fresh)} pipeline(s).")
    return 0 if added == len(fresh) else 1


if __name__ == "__main__":
    raise SystemExit(main())
