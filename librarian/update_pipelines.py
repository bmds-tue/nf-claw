# librarian/update_pipelines.py
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from librarian import write_skill
from librarian.add_pipeline import read_sources, validate_pipeline_name
from runner import submodule as submod

_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def select_latest(tags: list[str]) -> str | None:
    parsed = [(tuple(int(x) for x in m.groups()), t)
              for t in tags if (m := _SEMVER.match(t))]
    return max(parsed)[1] if parsed else None


def remote_tags(url: str) -> list[str]:
    r = subprocess.run(["git", "ls-remote", "--tags", "--refs", "--", url],
                       capture_output=True, text=True, timeout=60, check=True)
    return [line.split("\t")[-1].rsplit("/", 1)[-1] for line in r.stdout.splitlines()]


def bump(name: str, url: str, repo_root: Path) -> str | None:
    name = validate_pipeline_name(name)
    latest = select_latest(remote_tags(url))
    if latest is None:
        return None
    up = repo_root / "pipelines" / name / "upstream"
    # Run in an uninitialised submodule's directory, the fetch and checkout below would act on the
    # nf-claw repository itself — fetching (shallowly) into it and checking the tag out over it.
    if not submod.is_git_tree(up):
        raise RuntimeError(f"pipelines/{name}/upstream is not initialised; run "
                           f"`git submodule update --init pipelines/{name}/upstream` first")
    subprocess.run(["git", "-C", str(up), "fetch", "--tags", "--depth", "1",
                    "origin", f"refs/tags/{latest}:refs/tags/{latest}"], check=True)
    subprocess.run(["git", "-C", str(up), "checkout", f"tags/{latest}"], check=True)
    # Record the gitlink at the tag we just checked out, so the committed pin IS the release
    # and a later `git submodule update` cannot reset the working tree off it. (Matches
    # discover_pipelines.add_one; keeps `git describe --tags` clean for the drift gate.)
    subprocess.run(["git", "-C", str(repo_root), "add",
                    f"pipelines/{name}/upstream"], check=True)
    write_skill.generate(name, pipelines_dir=repo_root / "pipelines")
    return latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="librarian.update_pipelines")
    parser.add_argument("--sources", default="sources.tsv")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    # Resolve a relative --sources against --repo-root (not the CWD), so `bump` — which builds every
    # path from `root` — and the source list always refer to the same repo. Matches discover_pipelines.
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
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
