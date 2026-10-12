# librarian/discover_pipelines.py
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
import subprocess
import urllib.request
from pathlib import Path

from librarian import write_skill
from librarian.add_pipeline import read_sources, valid_pipeline_name, validate_pipeline_name

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


def fetch_catalog(url: str = NFCORE_PIPELINES_JSON) -> list[dict]:
    """Fetch the public nf-core pipeline index (no token required)."""
    req = urllib.request.Request(url, headers={"User-Agent": "nf-claw-discover"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (fixed https URL)
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


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kw)


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


def add_one(name: str, url: str, tag: str, repo_root: Path) -> bool:
    """Add one pipeline submodule pinned to `tag` and generate its context."""
    name = validate_pipeline_name(name)
    entry = repo_root / "pipelines" / name
    # A failed add rolls back only a tree this invocation owns. Discovery can encounter
    # orphaned entries absent from sources.tsv; never remove their research data or links.
    if entry.exists() or entry.is_symlink():
        print(f"{name}: ERROR pipeline entry already exists: {entry}; preserved without changes")
        return False
    up = entry / "upstream"
    try:
        _run(
            ["git", "-C", str(repo_root), "submodule", "add", "--force", url,
             f"pipelines/{name}/upstream"],
            check=True,
        )
        _run(["git", "-C", str(up), "fetch", "--tags", "--depth", "1", "origin",
              f"refs/tags/{tag}:refs/tags/{tag}"])
        _run(["git", "-C", str(up), "checkout", f"tags/{tag}"], check=True)
        # `submodule add` records the gitlink at the default branch HEAD; re-stage it at the
        # tag we just checked out so the pin IS the release. Otherwise a later
        # `git submodule update` resets the working tree off the tag, `git describe --tags`
        # returns `<tag>-N-g<hash>`, and the drift gate flags the generated context as stale.
        _run(["git", "-C", str(repo_root), "add", f"pipelines/{name}/upstream"], check=True)
        write_skill.generate(name, pipelines_dir=repo_root / "pipelines")
        return True
    except Exception as exc:  # one failure never blocks the others
        print(f"{name}: ERROR {exc}; rolling back")
        _rollback(name, repo_root)
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
