"""Check a run's published results against the pinned release's own nf-test snapshot.

Usage: python check_nftest_snapshot.py SNAPSHOT RUN_OUTDIR [--test NAME]

An nf-core release commits the expected results of its pipeline test (`tests/*.nf.test.snap`): the
output paths that are stable and the md5 of every file whose content is stable. nf-core's CI checks
each release against it. Running that test through nfclaw and comparing the results with it shows
that nfclaw changed none of them, using upstream's expectations rather than a re-derived oracle.

nf-test names each checksummed file by its basename and hashes the decompressed content of a `.gz`
file, so an entry matches any published file of that name, a `.gz` file by either digest. Every
expected path must exist; extra files are not judged, because the snapshot does not carry the
patterns its test ignores. nfclaw's own `provenance/` and Nextflow's own state (`.nextflow/`,
`.nextflow.log*`) are not published results. Files are hashed in chunks, so a large result is never
read into memory whole. Exits 1 when an expected path is missing or a checksum differs, 2 when the
snapshot or the run cannot be read.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import zlib
from pathlib import Path

_MD5_ENTRY = re.compile(r"^(?P<name>.+):md5,(?P<md5>[0-9a-f]{32})$")


def expectations(snapshot: dict,
                 test: str | None = None) -> tuple[list[str], list[tuple[str, str]]]:
    """The stable paths and the `(basename, md5)` entries the snapshot's `test` records.

    The paths are the content part that lists only plain strings (nf-core's `stable_path`); the
    checksums are every `name:md5,<hash>` string anywhere in the content."""
    if not isinstance(snapshot, dict):
        raise ValueError("the snapshot is not a JSON object of tests")
    if test is None:
        if len(snapshot) != 1:
            raise ValueError(f"the snapshot records {len(snapshot)} tests; name one with --test: "
                             + ", ".join(map(repr, snapshot)))
        test = next(iter(snapshot))
    if test not in snapshot:
        raise ValueError(f"no test {test!r} in the snapshot: " + ", ".join(map(repr, snapshot)))
    content = snapshot[test].get("content") if isinstance(snapshot[test], dict) else None
    if not isinstance(content, list):
        raise ValueError(f"test {test!r} records no content list")
    paths: list[str] = []
    for part in content:
        if (isinstance(part, list) and part and all(isinstance(item, str) for item in part)
                and not any(_MD5_ENTRY.match(item) for item in part)):
            paths.extend(part)
    checksums: list[tuple[str, str]] = []
    pending: list = [content]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and (m := _MD5_ENTRY.match(item)):
            checksums.append((m["name"], m["md5"]))
        elif isinstance(item, list):
            pending.extend(reversed(item))
        elif isinstance(item, dict):
            pending.extend(reversed(list(item.values())))
    return paths, checksums


_CHUNK = 1024 * 1024


def _md5(stream) -> str:
    digest = hashlib.md5()
    for chunk in iter(lambda: stream.read(_CHUNK), b""):
        digest.update(chunk)
    return digest.hexdigest()


def digests(path: Path) -> set[str]:
    """The md5 of a file's bytes and, for a `.gz` file, of its decompressed content."""
    with path.open("rb") as stream:
        found = {_md5(stream)}
    if path.name.endswith(".gz"):
        try:
            with gzip.open(path, "rb") as stream:
                found.add(_md5(stream))
        except (OSError, EOFError, zlib.error):         # not (valid) gzip: its raw bytes only
            pass
    return found


def _published(relative: Path) -> bool:
    """A run result, not nfclaw's provenance bundle or Nextflow's own state in the outdir."""
    head = relative.parts[0]
    return head not in ("provenance", ".nextflow") and not head.startswith(".nextflow.log")


def compare(snapshot: dict, outdir: Path, test: str | None = None) -> dict[str, list[str]]:
    """`missing_paths`, `missing_files`, `different` and `identical`, each a list of names."""
    paths, checksums = expectations(snapshot, test)
    published: dict[str, list[Path]] = {}
    if not outdir.is_dir():
        raise ValueError(f"not a run directory: {outdir}")
    for path in sorted(outdir.rglob("*")):
        relative = path.relative_to(outdir)
        if _published(relative) and path.is_file():
            published.setdefault(path.name, []).append(path)
    hashed: dict[Path, set[str]] = {}

    def matches(path: Path, md5: str) -> bool:
        if path not in hashed:
            hashed[path] = digests(path)
        return md5 in hashed[path]

    result: dict[str, list[str]] = {"missing_paths": [p for p in paths
                                                      if not (outdir / p).exists()],
                                    "missing_files": [], "different": [], "identical": []}
    for name, md5 in checksums:
        candidates = published.get(name, [])
        if not candidates:
            result["missing_files"].append(name)
        elif any(matches(p, md5) for p in candidates):
            result["identical"].append(name)
        else:
            result["different"].append(name)
    result["paths"] = paths
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--test", help="the snapshot's test name, e.g. '-profile test'")
    args = parser.parse_args(argv)
    try:
        result = compare(json.loads(args.snapshot.read_text(encoding="utf-8")), args.outdir,
                         args.test)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    failed = result["missing_paths"] + result["missing_files"] + result["different"]
    paths, present = len(result["paths"]), len(result["paths"]) - len(result["missing_paths"])
    identical = len(result["identical"])
    checksums = identical + len(result["different"]) + len(result["missing_files"])
    print(f"{args.outdir}: {present} of {paths} expected paths present; "
          f"{identical} of {checksums} checksums identical")
    for label in ("missing_paths", "missing_files", "different"):
        for name in result[label]:
            print(f"  {label.replace('_', ' ')}: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
