"""Read sources.tsv and print the .gitmodules entries and `git submodule add` commands for it."""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    policy: str


_PIPELINE_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")


def valid_pipeline_name(name: str) -> bool:
    """Whether `name` is safe to use as a pipeline slug and path component."""
    return bool(_PIPELINE_NAME_RE.fullmatch(name))


def validate_pipeline_name(name: str) -> str:
    if not valid_pipeline_name(name):
        raise ValueError(
            f"invalid pipeline name {name!r}; use letters, numbers, dot, underscore and dash, "
            "starting and ending with a letter or number"
        )
    return name


def read_sources(tsv: Path) -> list[Source]:
    out: list[Source] = []
    for line_num, line in enumerate(tsv.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            raise ValueError(f"invalid sources.tsv row {line_num}: expected name and url")
        name, url = validate_pipeline_name(parts[0].strip()), parts[1].strip()
        policy = parts[2].strip() if len(parts) > 2 else "latest-release"
        out.append(Source(name, url, policy))
    return out


def gitmodules_text(sources: list[Source]) -> str:
    out: list[str] = []
    for source in sources:
        name = validate_pipeline_name(source.name)
        out.append(
            f'[submodule "pipelines/{name}/upstream"]\n'
            f"\tpath = pipelines/{name}/upstream\n"
            f"\turl = {source.url}\n"
        )
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="librarian.add_pipeline")
    parser.add_argument("--sources", default="sources.tsv")
    args = parser.parse_args(argv)
    srcs = read_sources(Path(args.sources))
    print(gitmodules_text(srcs))
    print(f"# {len(srcs)} pipelines. To materialize each submodule, run:")
    for s in srcs:
        print(f"git submodule add {s.url} pipelines/{s.name}/upstream")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
