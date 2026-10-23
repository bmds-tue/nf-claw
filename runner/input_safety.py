"""Keep execution writes outside the local dependency trees an analysis consumes."""
from __future__ import annotations

import os
import stat
from functools import lru_cache
from pathlib import Path

from runner.errors import ErrorCode, NfclawError
from runner.replay_guard import MissingInputSource, inspect_input_paths


def engine_write_paths(outdir: Path, overlay: dict[str, str]) -> list[tuple[str, Path, bool]]:
    """Nextflow launcher caches and temporary files, before a version probe can bootstrap them.

    Metadata probes run from the caller's directory, while execution runs from the outdir.
    Check both interpretations of a relative cache path, including inherited settings.
    """
    writes = []
    for name in ("NXF_HOME", "NXF_DIST", "NXF_TEMP", "CAPSULE_CACHE_DIR"):
        defaults = str(Path.home() / ".nextflow") if name == "NXF_HOME" else (
            os.environ.get("TMPDIR", "") if name == "NXF_TEMP" else "")
        runtime = overlay.get(name) or os.environ.get(name) or defaults
        values = {runtime} if runtime else set()
        if not overlay.get("NXF_VER"):
            probe = os.environ.get(name) or defaults
            if probe:
                values.add(probe)
        for value in values:
            path = Path(value)
            destinations = [path] if path.is_absolute() else [Path.cwd() / path, outdir / path]
            writes.extend((f"Nextflow {name}", destination, False) for destination in destinations)
    return writes


def check_write_boundaries(sources: list[Path] | tuple[Path, ...],
                           writes: list[tuple[str, Path, bool]]) -> None:
    """Refuse writes beneath any consumed directory, including nested directory aliases.

    The boolean also refuses dependencies inside a destination that can publish arbitrary
    results. Work/cache trees use False: previously computed files there are legitimate
    inputs for a later task, but a whole consumed directory must never acquire new work.
    Inspect metadata only; prelaunch content snapshots remain the source of byte evidence.
    """
    if not sources:
        return
    destinations = [(label, path.expanduser().resolve(), contains)
                    for label, path, contains in writes]
    cached_trees = [destination for _, destination, contains in destinations if not contains]
    physical_writes: dict[tuple[int, int], tuple[str, Path]] = {}
    inspected: set[Path] = set()

    def inspect_writer(label: str, path: Path, recursive: bool) -> None:
        try:
            metadata = path.stat()
        except (FileNotFoundError, NotADirectoryError):
            return  # Missing output slots, including broken links, can be repaired by the run.
        if stat.S_ISREG(metadata.st_mode):
            if metadata.st_nlink > 1 or path.is_symlink():
                physical_writes[(metadata.st_dev, metadata.st_ino)] = label, path
        elif recursive and stat.S_ISDIR(metadata.st_mode):
            root = path.resolve()
            excluded = [cache for cache in cached_trees
                        if cache != root and cache.is_relative_to(root)]
            pending = [root]
            while pending:
                directory = pending.pop()
                resolved = directory.resolve()
                if resolved in inspected:
                    continue
                inspected.add(resolved)
                with os.scandir(directory) as entries:
                    for entry in entries:
                        child = Path(entry.path)
                        target = child.resolve()
                        # Nextflow stages inputs in its work/cache trees. Those declared trees
                        # have a narrower write policy; publication scans must not reinterpret
                        # their existing read aliases as output files.
                        if any(child.is_relative_to(cache) for cache in excluded):
                            continue
                        try:
                            metadata = entry.stat(follow_symlinks=True)
                        except (FileNotFoundError, NotADirectoryError):
                            continue
                        if stat.S_ISDIR(metadata.st_mode):
                            if entry.is_symlink():
                                destinations.append((label, target, True))
                            pending.append(child)
                        elif stat.S_ISREG(metadata.st_mode) and (
                                metadata.st_nlink > 1 or entry.is_symlink()):
                            physical_writes[(metadata.st_dev, metadata.st_ino)] = label, child

    try:
        for label, path, contains in writes:
            inspect_writer(label, path.expanduser(), contains)
    except (OSError, RuntimeError) as exc:
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          f"Cannot inspect execution destination boundaries: {exc}",
                          details={"unsafe_write_boundary": True}) from exc

    def refuse(label: str, destination: Path, path: Path, dependency: Path):
        raise NfclawError(
            ErrorCode.ENVIRONMENT,
            f"{label} {destination} overlaps local dependency {path} "
            f"(resolved to {dependency}). Execution writes would change its input data.",
            fix="Keep output and work directories outside input directories, and keep "
                "input data, configuration and pipeline code outside the output directory.",
            details={"unsafe_write_boundary": True})

    @lru_cache(maxsize=1024)
    def route_parents(parent: Path) -> frozenset[Path]:
        # Retain the containing output slot even when a later directory symlink redirects
        # it elsewhere. Resolving each ancestor also handles OS aliases such as /var on macOS.
        return frozenset(part.resolve() for part in (parent, *parent.parents))

    def check(path: Path):
        dependency = path.resolve()
        logical = Path(os.path.abspath(path.expanduser()))
        parents = route_parents(path.expanduser().absolute().parent)
        directory = path.is_dir()
        for label, destination, contains in destinations:
            if (dependency == destination
                    or directory and destination.is_relative_to(dependency)
                    or contains and (dependency.is_relative_to(destination)
                                     or logical.is_relative_to(destination)
                                     or destination in parents)):
                refuse(label, destination, path, dependency)
        if physical_writes:
            try:
                metadata = path.stat()
            except FileNotFoundError:
                return
            if alias := physical_writes.get((metadata.st_dev, metadata.st_ino)):
                refuse(*alias, path, dependency)

    for source in sources:
        # Judge the named path even if absent; a mandatory missing input must not become an
        # execution destination. Missing optional path parameters retain upstream semantics.
        try:
            check(source)
            inspect_input_paths([source], check)
        except MissingInputSource:
            continue
        except (OSError, RuntimeError) as exc:
            raise NfclawError(
                ErrorCode.ENVIRONMENT,
                f"Cannot inspect local dependency boundaries: {source}: {exc}") from exc
