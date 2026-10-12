"""Keep execution writes outside the local dependency trees an analysis consumes."""
from __future__ import annotations

import os
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
    destinations = [(label, path.expanduser().resolve(), contains)
                    for label, path, contains in writes]

    def check(path: Path):
        dependency = path.resolve()
        directory = path.is_dir()
        for label, destination, contains in destinations:
            if (dependency == destination
                    or directory and destination.is_relative_to(dependency)
                    or contains and dependency.is_relative_to(destination)):
                raise NfclawError(
                    ErrorCode.ENVIRONMENT,
                    f"{label} {destination} overlaps local dependency {path} "
                    f"(resolved to {dependency}). Execution writes would change its input data.",
                    fix="Keep output and work directories outside input directories, and keep "
                        "input data, configuration and pipeline code outside the output directory.",
                    details={"unsafe_write_boundary": True})

    for source in sources:
        # Judge the named path even if absent; a mandatory missing input must not become an
        # execution destination. Missing optional path parameters retain upstream semantics.
        try:
            check(source)
            inspect_input_paths([source], check)
        except MissingInputSource:
            continue
        except (OSError, RuntimeError) as exc:
            raise NfclawError(ErrorCode.ENVIRONMENT,
                              f"Cannot inspect local dependency boundaries: {source}: {exc}") from exc
