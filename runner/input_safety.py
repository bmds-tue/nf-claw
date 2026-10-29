"""Keep execution writes outside the local dependency trees an analysis consumes."""
from __future__ import annotations

import os
from pathlib import Path

from runner.errors import ErrorCode, NfclawError
from runner.replay_guard import check_write_boundaries as _check_write_boundaries


def engine_write_paths(outdir: Path, overlay: dict[str, str]) -> list[tuple[str, Path, bool]]:
    """Nextflow launcher caches and temporary files, before a version probe can bootstrap them.

    Metadata probes run from the caller's directory, while execution runs from the outdir.
    Check both interpretations of a relative cache path, including inherited settings.
    """
    writes = []
    for name in ("NXF_HOME", "NXF_DIST", "NXF_TEMP", "NXF_CACHE_DIR", "CAPSULE_CACHE_DIR"):
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
    """Share the standalone replay's filesystem boundary checks with ordinary runs."""
    try:
        _check_write_boundaries(sources, writes)
    except (ValueError, OSError, RuntimeError) as exc:
        # A path that could not be inspected is not an overlap: say what would let it be checked.
        # Either way nothing is written, since no separation could be established.
        inspection = (OSError, RuntimeError)
        uninspected = isinstance(exc if isinstance(exc, inspection) else exc.__cause__, inspection)
        raise NfclawError(
            ErrorCode.ENVIRONMENT, str(exc),
            fix=("Make the input, output and work paths readable and every directory above them "
                 "searchable, then retry." if uninspected else
                 "Keep output and work directories outside input directories, and keep "
                 "input data, configuration and pipeline code outside the output directory."),
            details={"unsafe_write_boundary": True}) from exc
