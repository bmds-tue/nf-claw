"""Bump every `latest-release` pipeline in sources.tsv to its newest upstream release tag."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from librarian import write_skill
from librarian.add_pipeline import read_sources, validate_pipeline_name
from runner import submodule as submod
from runner import budget, execution
from runner.provenance import _atomic_bytes
from runner.probes import capture
from runner.settings import seconds

_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def select_latest(tags: list[str]) -> str | None:
    parsed = [(tuple(int(x) for x in m.groups()), t)
              for t in tags if (m := _SEMVER.match(t))]
    return max(parsed)[1] if parsed else None


def remote_tags(url: str) -> list[str]:
    r = capture(["git", "ls-remote", "--tags", "--refs", "--", url],
                timeout=seconds("NFCLAW_GIT_TIMEOUT", 60), env=submod._git_env())
    r.check_returncode()
    return [line.split("\t")[-1].rsplit("/", 1)[-1] for line in r.stdout.splitlines()]


def _run(args: list[str], *, check: bool = False, timeout: float = 120):
    result = capture(args, timeout=seconds("NFCLAW_GIT_TIMEOUT", timeout),
                     env=submod._git_env())
    if check:
        result.check_returncode()
    return result


def bump(name: str, url: str, repo_root: Path) -> str | None:
    name = validate_pipeline_name(name)
    with execution.stop_on_signals(), submod._init_lock(repo_root):
        return _bump(name, url, repo_root)


def _bump(name: str, url: str, repo_root: Path) -> str | None:
    up = repo_root / "pipelines" / name / "upstream"
    # Run in an uninitialised submodule's directory, the fetch and checkout below would act on the
    # nf-claw repository itself — fetching (shallowly) into it and checking the tag out over it.
    if not submod.is_git_tree(up):
        raise RuntimeError(f"pipelines/{name}/upstream is not initialised; run "
                           f"`git submodule update --init pipelines/{name}/upstream` first")
    if not submod.is_git_tree(repo_root):
        raise RuntimeError("update root is not the repository root")
    entry = up.parent
    if (up.is_symlink() or entry.is_symlink()
            or not up.resolve().is_relative_to(repo_root.resolve())):
        raise RuntimeError(f"{entry}: pipeline directory aliases are not safe to update")
    relative = f"pipelines/{name}/upstream"
    indexed = _run(["git", "-C", str(repo_root), "ls-files", "--stage", "-z", "--", relative],
                   check=True).stdout
    match = re.fullmatch(r"160000 ([0-9a-f]{40,64}) 0\t" + re.escape(relative) + "\x00", indexed)
    before = submod._own_head(up)
    if not match or match[1] != before:
        raise RuntimeError(f"{relative}: checkout must match its unstaged, recorded gitlink")
    registered = _run(["git", "-C", str(repo_root), "config", "-f", ".gitmodules", "--get",
                       f"submodule.{relative}.url"], check=True).stdout.strip()
    if registered != url:
        raise RuntimeError(f"{relative}: source URL does not match the registered submodule")
    docs = [f"pipelines/{name}/skill.md", f"pipelines/{name}/reference.md"]
    for path, paths in ((repo_root, [relative, *docs]), (up, [])):
        dirty = _run(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all",
                      "--ignored=matching", "--", *paths], check=True).stdout
        if dirty:
            raise RuntimeError(f"{path}: local changes must be committed or preserved "
                               f"before updating {name}")
    saved = {}
    for filename in ("skill.md", "reference.md"):
        path = entry / filename
        if (path.is_symlink() or (path.exists()
                                 and (not path.is_file() or path.stat().st_nlink != 1))):
            raise RuntimeError(f"{path}: generated context must be a regular file")
        saved[path] = (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
    branch = _run(["git", "-C", str(up), "symbolic-ref", "-q", "--short", "HEAD"])
    if branch.returncode not in (0, 1):
        raise RuntimeError(f"{relative}: cannot establish the original checkout")
    original = branch.stdout.strip() if branch.returncode == 0 else before
    latest = select_latest(remote_tags(url))
    if latest is None:
        return None
    # Fetch only from the registered source. Until this completes no checkout, index or context
    # file has changed, so a new user edit must be preserved rather than "rolled back" over.
    _run(["git", "-C", str(up), "fetch", "--tags", "--depth", "1", "--", url,
          f"refs/tags/{latest}:refs/tags/{latest}"], check=True, timeout=300)
    for path, paths in ((repo_root, [relative, *docs]), (up, [])):
        if _run(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all",
                 "--ignored=matching", "--", *paths], check=True).stdout:
            raise RuntimeError(f"{path}: local work appeared during fetch; preserved unchanged")
    if submod._own_head(up) != before:
        raise RuntimeError(f"{relative}: checkout changed during fetch; preserved unchanged")
    for path, content in saved.items():
        current = ((path.read_bytes(), path.stat().st_mode & 0o777)
                   if path.exists() and not path.is_symlink() else None)
        if current != content:
            raise RuntimeError(f"{path}: context changed during fetch; preserved unchanged")
    try:
        _run(["git", "-C", str(up), "checkout", "--detach", f"tags/{latest}"], check=True)
        _run(["git", "-C", str(repo_root), "add", "--", relative], check=True)
        write_skill.generate(name, pipelines_dir=repo_root / "pipelines")
    except BaseException as exc:
        # Restore only the checkout, gitlink and generated files owned by this update; never
        # reset the repository or discard an unrelated staged change from another pipeline.
        rollback_errors = []
        actions = [lambda: _run(["git", "-C", str(up), "checkout", original], check=True),
                   lambda: _run(["git", "-C", str(repo_root), "update-index", "--cacheinfo",
                                  f"160000,{match[1]},{relative}"], check=True)]
        for path, content in saved.items():
            actions.append(lambda p=path, c=content: p.unlink(missing_ok=True) if c is None
                           else _atomic_bytes(p, c[0], mode=c[1]))
        for action in actions:
            try:
                with budget.suspend():
                    action()
            except BaseException as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            exc.add_note("Rollback needs attention: " + "; ".join(rollback_errors))
        raise
    return latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="librarian.update_pipelines")
    parser.add_argument("--sources", default="sources.tsv")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    # Resolve a relative --sources against --repo-root (not the CWD), so `bump` — which builds every
    # path from `root` — and the source list always refer to the same repo.
    # Matches discover_pipelines.
    sources_path = Path(args.sources)
    if not sources_path.is_absolute():
        sources_path = root / sources_path
    failures = 0
    for src in read_sources(sources_path):
        if src.policy != "latest-release":
            # Only "latest-release" pipelines are auto-bumped; anything else (e.g. a pinned
            # version) is left untouched so the policy column in sources.tsv is honoured.
            print(f"{src.name}: skipped (policy={src.policy}; not auto-bumped)")
            continue
        try:
            up = root / "pipelines" / validate_pipeline_name(src.name) / "upstream"
            before = submod._own_head(up)
            tag = bump(src.name, src.url, root)
            # Say what changed: a pipeline already at its latest release is checked, not bumped.
            if tag is None:
                outcome = "no release tag found"
            elif before is not None and submod._own_head(up) != before:
                outcome = f"bumped to {tag}"
            else:
                outcome = f"already at {tag}"
            print(f"{src.name}: {outcome}")
        except Exception as exc:                          # one failure never blocks others
            print(f"{src.name}: ERROR {exc}")
            if detail := getattr(exc, "stderr", None):
                print(detail.strip())
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
