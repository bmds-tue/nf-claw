"""Keep execution writes outside the local dependency trees an analysis consumes."""
from __future__ import annotations

from pathlib import Path

from runner.errors import ErrorCode, NfclawError
from runner.replay_guard import MissingInputSource, inspect_input_paths


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
