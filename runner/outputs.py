from __future__ import annotations

import errno
import json
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputsReport:
    multiqc_report: Path | None
    files: tuple[str, ...]


def is_nextflow_internal(rel: Path) -> bool:
    """Whether a path (relative to the outdir) is a Nextflow engine internal, not a result.
    When Nextflow launches from the outdir its state lands there: the `.nextflow/` directory and
    `.nextflow.log*` files. Those are never pipeline outputs."""
    head = rel.parts[0] if rel.parts else ""
    return head == ".nextflow" or head.startswith(".nextflow.log")


def is_result(rel: Path) -> bool:
    """Whether a path (relative to the outdir) is one of the run's results: not Nextflow's own state
    and not nfclaw's `provenance/` bundle, which describes the run rather than being part of it."""
    in_bundle = bool(rel.parts) and rel.parts[0] == "provenance"
    return not in_bundle and not is_nextflow_internal(rel)


def result_entries(outdir: Path, only: Path | None = None) -> Iterator[tuple[Path, str]]:
    """Enumerate files and directories, including empty directories, without hiding errors.

    pathlib's recursive glob suppresses directory scan errors on newer Python versions. An
    incomplete inventory must never be reported as a successful scientific comparison.
    Follow published directory symlinks, preserving their result paths, and reject cycles.
    """
    def walk(directory: Path, ancestors: frozenset[Path]) -> Iterator[tuple[Path, str]]:
        real = directory.resolve()
        if real in ancestors:
            raise OSError(errno.ELOOP, "cyclic result directory symlink", str(directory))
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                path = directory / entry.name
                if not is_result(path.relative_to(outdir)):
                    continue
                if entry.is_dir(follow_symlinks=True):
                    yield path, "directory"
                    yield from walk(path, ancestors | {real})
                elif entry.is_file(follow_symlinks=True):
                    yield path, "file"
                else:
                    raise OSError(errno.EINVAL, "result is missing or not a regular file", str(path))

    if only is None:
        yield from walk(outdir, frozenset())
    else:
        if not is_result(only.relative_to(outdir)):
            raise ValueError(f"not a published result: {only}")
        if only.is_dir():
            yield only, "directory"
            yield from walk(only, frozenset())
        elif only.is_file():
            yield only, "file"
        else:
            raise FileNotFoundError(f"result is missing or not a regular file: {only}")


def result_files(outdir: Path) -> Iterator[Path]:
    for path, kind in result_entries(outdir):
        if kind == "file":
            yield path


def snapshot(outdir: Path, hash_file: Callable[[Path], str] | None = None, *, only: Path | None = None
             ) -> tuple[dict[str, str], dict[str, dict], dict[str, dict[str, str]]]:
    """One traversal records the namespace and optionally hashes each resolved data target once.

    Internal link targets are relative to the result root so moving a complete bundle preserves
    its identity. External target identities remain absolute for lineage verification. Comparing
    independently executed runs uses logical paths and types, since task work paths can differ.
    """
    root, real_root = outdir.absolute(), outdir.resolve()

    def target_record(target, raw=None):
        raw = str(target) if raw is None else raw
        if not target.is_absolute():
            return {"scope": "relative", "path": raw}
        for base in (root, real_root):
            prefix = str(base).rstrip("/") + "/"
            if raw == str(base) or raw.startswith(prefix):
                return {"scope": "outdir", "path": raw[len(prefix):] or "."}
        return {"scope": "external", "path": raw}

    hashes, inventory, raw_inventory, digests = {}, {}, {}, {}
    for path, kind in result_entries(outdir, only=only):
        relative = path.relative_to(outdir).as_posix()
        entry = {"type": kind}
        raw_entry = {"type": kind}
        if path.is_symlink():
            raw = os.readlink(path)
            entry["link_target"] = target_record(Path(raw), raw)
            raw_entry["link_target"] = raw
        real = path.resolve()
        if real != real_root / relative:
            entry["resolved_path"] = target_record(real)
        if real != path.absolute():
            raw_entry["resolved_path"] = str(real)
        inventory[relative] = entry
        raw_inventory[str(path.absolute())] = raw_entry
        if hash_file is not None and kind == "file":
            if real not in digests:
                digests[real] = hash_file(real)
            hashes[relative] = digests[real]
    return hashes, inventory, raw_inventory


def read_inventory(path: Path, checksums: dict[str, str]) -> dict[str, dict]:
    """Require a complete, internally consistent recorded result namespace."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate inventory key {key!r} in {path}")
            value[key] = item
        return value

    record = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if (not isinstance(record, dict) or set(record) != {"version", "entries"}
            or type(record["version"]) is not int or record["version"] != 1
            or not isinstance(record["entries"], dict)):
        raise ValueError(f"invalid output inventory in {path}")
    inventory = record["entries"]

    def relative_name(name):
        return (isinstance(name, str) and bool(name) and "\x00" not in name
                and not any(part in ("", ".", "..") for part in name.split("/")))

    for name, entry in inventory.items():
        if (not relative_name(name) or not is_result(Path(name)) or not isinstance(entry, dict)
                or entry.get("type") not in ("file", "directory")
                or set(entry) - {"type", "link_target", "resolved_path"}):
            raise ValueError(f"invalid output inventory entry {name!r} in {path}")
        for key in ("link_target", "resolved_path"):
            if key not in entry:
                continue
            target = entry[key]
            if (not isinstance(target, dict) or set(target) != {"scope", "path"}
                    or target["scope"] not in ("relative", "outdir", "external")
                    or not isinstance(target["path"], str) or not target["path"]
                    or "\x00" in target["path"]
                    or (target["scope"] == "external" and not Path(target["path"]).is_absolute())
                    or (target["scope"] == "relative" and (key == "resolved_path"
                                                         or Path(target["path"]).is_absolute()))
                    or (target["scope"] == "outdir"
                        and (Path(target["path"]).is_absolute() or
                             (key == "resolved_path" and target["path"] != "."
                              and not relative_name(target["path"]))))):
                raise ValueError(f"invalid output inventory target for {name!r} in {path}")
        for parent in Path(name).parents:
            if parent == Path("."):
                break
            parent_entry = inventory.get(parent.as_posix())
            if not isinstance(parent_entry, dict) or parent_entry.get("type") != "directory":
                raise ValueError(f"missing output inventory parent {parent} in {path}")
    if {name for name, entry in inventory.items() if entry["type"] == "file"} != checksums.keys():
        raise ValueError(f"output inventory disagrees with its file checksums in {path}")
    return inventory


def namespace_difference(expected: dict, current: dict) -> str:
    missing = sorted(expected.keys() - current.keys())
    extra = sorted(current.keys() - expected.keys())
    changed = sorted(name for name in expected.keys() & current.keys() if expected[name] != current[name])
    return f"missing: {missing}; extra: {extra}; type or link changed: {changed}"


def recorded_inventory(outdir: Path, checksums: dict[str, str]) -> dict | None:
    """Older file-only chains keep their checksum checks; declared new records stay mandatory."""
    path = outdir / "provenance/outputs.inventory.json"
    manifest = json.loads((outdir / "provenance/run_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("invalid run manifest")
    if "output_inventory_version" in manifest and (
            type(manifest["output_inventory_version"]) is not int or manifest["output_inventory_version"] != 1):
        raise ValueError("unsupported output inventory version")
    if not path.exists() and "output_inventory_version" not in manifest:
        return None
    return read_inventory(path, checksums)


def collect(outdir: Path) -> OutputsReport:
    paths = sorted(result_files(outdir))
    mqc = next((p for p in paths if p.name == "multiqc_report.html"), None)
    return OutputsReport(multiqc_report=mqc,
                         files=tuple(p.relative_to(outdir).as_posix() for p in paths))
