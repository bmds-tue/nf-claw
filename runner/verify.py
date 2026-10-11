from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from runner import provenance
from runner.errors import ErrorCode, NfclawError


@dataclass(frozen=True)
class Comparison:
    """How a replay's outputs compare to the run they reproduce."""

    identical: list[str] = field(default_factory=list)   # same path, same bytes
    changed: list[str] = field(default_factory=list)     # same path, different bytes
    missing: list[str] = field(default_factory=list)     # in the original, absent from the replay
    extra: list[str] = field(default_factory=list)       # in the replay, absent from the original

    @property
    def structurally_equal(self) -> bool:
        """The replay has the same file identities and multiplicities, regardless of contents."""
        return not self.missing and not self.extra

    @property
    def byte_identical(self) -> bool:
        """Every paired file has the same bytes and no file is missing or extra."""
        return self.structurally_equal and not self.changed


def _read(outdir: Path, *, recorded: bool) -> dict[str, str]:
    """What a run directory produced, as {relative path: hash}.

    The original's recorded snapshot is the reference. The replay is always measured live, even
    when it has a bundle: otherwise a stale manifest hides changed, removed or added results.
    Without an original snapshot, both directories are measured live.
    """
    checksums = outdir / "provenance" / "outputs.sha256"
    try:
        if recorded and checksums.exists():
            return provenance.read_checksums(checksums)
        if not outdir.is_dir():
            raise NfclawError(
                ErrorCode.ENVIRONMENT, f"not a run directory: {outdir}",
                fix="Pass the --outdir of a run (the replay's target, and the original it "
                    "reproduces).")
        return provenance.output_checksums(outdir)
    except ValueError as exc:
        raise NfclawError(
            ErrorCode.ENVIRONMENT, f"cannot read checksum manifest {checksums}: {exc}",
            fix="Restore a valid outputs.sha256 from the original run; do not discard records.") from exc
    except OSError as exc:
        where = getattr(exc, "filename", None) or checksums
        reason = getattr(exc, "strerror", None) or exc
        raise NfclawError(
            ErrorCode.ENVIRONMENT, f"cannot read the run in {outdir}: {reason} ({where})",
            fix="Make every file of both runs readable, then retry.") from exc


def compare(original: Path, replay: Path) -> Comparison:
    """Compare a replay's outputs against the run it reproduces, by path.

    Comparing the raw `outputs.sha256` lines instead — the obvious thing to do — is misleading: a
    file whose *content* differs has a different `hash  path` line, so it shows up as both "missing"
    from the replay and "extra" in it, and one changed file is counted twice. Keying on the path
    separates the two questions that matter: did the replay produce the same *files* (structural),
    and did any of them come out different (content).
    """
    before = _read(original, recorded=True)
    after = _read(replay, recorded=False)
    identical, changed = [], []
    # File paths are part of the inventory. Metadata renames are reported for explicit
    # classification, never silently equated with an identical directory structure.
    for path in sorted(before.keys() & after.keys()):
        (identical if after.pop(path) == before.pop(path) else changed).append(path)
    return Comparison(
        identical=identical,
        changed=changed,
        missing=sorted(before),
        extra=sorted(after),
    )


def report(cmp: Comparison) -> str:
    lines = [
        f"identical : {len(cmp.identical)}",
        f"changed   : {len(cmp.changed)}   (same file, different bytes)",
        f"missing   : {len(cmp.missing)}   (in the original, not in the replay)",
        f"extra     : {len(cmp.extra)}   (in the replay, not in the original)",
        "",
    ]
    if cmp.structurally_equal:
        lines.append("The replay produced the same set of files as the original run.")
        if cmp.changed:
            lines.append(
                "Changed bytes may reflect timestamps or metadata, but may also reflect different "
                "scientific results. File structure alone does not establish scientific agreement; "
                "inspect the changed results or use a format-aware comparison.")
        else:
            lines.append("All compared files are byte-identical. This establishes output agreement, "
                         "not the biological accuracy of either run.")
    else:
        lines.append("The replay did NOT produce the same set of files. Check whether the runs "
                     "completed and used the same inputs and settings.")
    for label, paths in (("missing", cmp.missing), ("extra", cmp.extra), ("changed", cmp.changed)):
        if paths:
            lines.append("")
            lines.append(f"{label}:")
            lines += [f"  {p}" for p in paths]
    return "\n".join(lines) + "\n"
