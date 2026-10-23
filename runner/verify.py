from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from runner import environment_record, outputs, provenance
from runner.errors import ErrorCode, NfclawError


@dataclass(frozen=True)
class Comparison:
    """How a replay's outputs compare to the run they reproduce."""

    identical: list[str] = field(default_factory=list)   # same path, same bytes
    changed: list[str] = field(default_factory=list)     # same path, different bytes
    missing: list[str] = field(default_factory=list)     # in the original, absent from the replay
    extra: list[str] = field(default_factory=list)       # in the replay, absent from the original
    missing_directories: list[str] = field(default_factory=list)
    extra_directories: list[str] = field(default_factory=list)
    changed_links: list[str] = field(default_factory=list)
    unverified_structure: bool = False
    # "original -> replay" pairs whose paths differ only by an nf-core launch timestamp; each is
    # also listed under identical or changed by its bytes.
    renamed: list[str] = field(default_factory=list)
    # The two runs' recorded execution environments compared (runner.environment_record), or None
    # when either run predates the record.
    environment: dict | None = None

    @property
    def structurally_equal(self) -> bool:
        """The replay has the same file identities and multiplicities, regardless of contents."""
        return not (self.missing or self.extra or self.missing_directories
                    or self.extra_directories or self.unverified_structure)

    @property
    def byte_identical(self) -> bool:
        """Every paired file has the same bytes and no file is missing or extra."""
        return self.structurally_equal and not self.changed and not self.changed_links

    @property
    def same_environment(self) -> bool:
        """Images, plugins, engine and staged remote inputs agree (or neither run recorded them)."""
        return self.environment is None or self.environment["status"] == "identical"


def _environment(original: Path, replay: Path) -> dict | None:
    records = []
    for outdir in (original, replay):
        try:
            records.append(json.loads(
                (outdir / "provenance"
                 / environment_record.RECORD_NAME).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return None
    if not all(isinstance(record, dict) for record in records):
        return None
    return environment_record.compare(*records)


def _read(outdir: Path, *, recorded: bool) -> tuple[dict[str, str], dict[str, dict] | None]:
    """What a run directory produced, as {relative path: hash}.

    The original's recorded snapshot is the reference. The replay is always measured live, even
    when it has a bundle: otherwise a stale manifest hides changed, removed or added results.
    Without an original snapshot, both directories are measured live.
    """
    checksums = outdir / "provenance" / "outputs.sha256"
    try:
        if recorded and (checksums.exists() or checksums.is_symlink()):
            hashes = provenance.read_checksums(checksums)
            index = outdir / "provenance/outputs.inventory.json"
            inventory = (outputs.read_inventory(index, hashes)
                         if index.exists() or index.is_symlink() else None)
            return hashes, inventory
        if not outdir.is_dir():
            raise NfclawError(
                ErrorCode.ENVIRONMENT, f"not a run directory: {outdir}",
                fix="Pass the --outdir of a run (the replay's target, and the original it "
                    "reproduces).")
        hashes, inventory, _ = outputs.snapshot(outdir, provenance._sha256)
        return hashes, inventory
    except ValueError as exc:
        raise NfclawError(
            ErrorCode.ENVIRONMENT, f"cannot read the recorded output manifests in {outdir}: {exc}",
            fix="Restore valid output checksums and namespace records; do not discard records.",
        ) from exc
    except OSError as exc:
        where = getattr(exc, "filename", None) or checksums
        reason = getattr(exc, "strerror", None) or exc
        raise NfclawError(
            ErrorCode.ENVIRONMENT, f"cannot read the run in {outdir}: {reason} ({where})",
            fix="Make every file of both runs readable, then retry.") from exc


# The run-metadata files the nf-core template names from the clock at launch: `params_<time>.json`
# (written with an inline `new Date()` that no parameter pins) and the execution report, timeline,
# trace and DAG of releases that predate `trace_report_suffix`. Only these exact names are paired;
# any other dated file — possibly a scientific result — keeps its exact path in the comparison.
# nf-core's launch-stamped run metadata, and the reports the nf-co2footprint plugin names the
# same way.
_LAUNCH_STAMPED = re.compile(
    r"^pipeline_info/(params|execution_report|execution_timeline|execution_trace|pipeline_dag"
    r"|co2footprint_report|co2footprint_summary|co2footprint_trace)_"
    r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.(json|html|txt|svg|dot|mmd|pdf|png)$")


def _launch_time_pairs(missing: list[str], extra: list[str]) -> list[tuple[str, str]]:
    """(original, replay) launch-stamped run-metadata files, paired one to one.

    Only an unambiguous pair is matched: when several files share a stamped name on either side
    (an earlier attempt's report beside a resumed one), none of them is paired by guess."""
    def keys(paths):
        groups = defaultdict(list)
        for path in paths:
            if m := _LAUNCH_STAMPED.match(path):
                groups[(m.group(1), m.group(3))].append(path)
        return groups

    before, after = keys(missing), keys(extra)
    return sorted((before[key][0], after[key][0]) for key in before.keys() & after.keys()
                  if len(before[key]) == 1 and len(after[key]) == 1)


def compare(original: Path, replay: Path) -> Comparison:
    """Compare a replay's outputs against the run it reproduces, by path.

    Comparing the raw `outputs.sha256` lines instead — the obvious thing to do — is misleading: a
    file whose *content* differs has a different `hash  path` line, so it shows up as both "missing"
    from the replay and "extra" in it, and one changed file is counted twice. Keying on the path
    separates the two questions that matter: did the replay produce the same *files* (structural),
    and did any of them come out different (content).
    """
    before, original_inventory = _read(original, recorded=True)
    after, replay_inventory = _read(replay, recorded=False)
    before_dirs = (
        {name for name, entry in original_inventory.items() if entry["type"] == "directory"}
        if original_inventory is not None else set())
    after_dirs = {name for name, entry in replay_inventory.items() if entry["type"] == "directory"}
    changed_links = []
    if original_inventory is not None:
        for name in original_inventory.keys() & replay_inventory.keys():
            a, b = original_inventory[name], replay_inventory[name]
            if any(a.get(key) != b.get(key) for key in ("link_target", "resolved_path")):
                changed_links.append(name)
    identical, changed = [], []
    # File paths are part of the inventory. Metadata renames are reported for explicit
    # classification, never silently equated with an identical directory structure.
    for path in sorted(before.keys() & after.keys()):
        (identical if after.pop(path) == before.pop(path) else changed).append(path)
    # A file named by the clock at launch is the same logical result under a new name: pair it
    # explicitly and compare its bytes, rather than reporting a faithful replay as missing a file.
    renamed = []
    for old_path, new_path in _launch_time_pairs(sorted(before), sorted(after)):
        label = f"{old_path} -> {new_path}"
        (identical if before.pop(old_path) == after.pop(new_path) else changed).append(label)
        renamed.append(label)
        if original_inventory is not None and any(
                original_inventory.get(old_path, {}).get(key)
                != replay_inventory.get(new_path, {}).get(key)
                for key in ("link_target", "resolved_path")):
            changed_links.append(label)
    return Comparison(
        renamed=renamed,
        identical=sorted(identical),
        changed=sorted(changed),
        missing=sorted(before),
        extra=sorted(after),
        missing_directories=sorted(before_dirs - after_dirs),
        extra_directories=sorted(after_dirs - before_dirs)
        if original_inventory is not None else [],
        changed_links=sorted(changed_links),
        unverified_structure=original_inventory is None,
        environment=_environment(original, replay),
    )


def report(cmp: Comparison) -> str:
    lines = [
        f"identical : {len(cmp.identical)}",
        f"changed   : {len(cmp.changed)}   (same file, different bytes)",
        f"missing   : {len(cmp.missing)}   (in the original, not in the replay)",
        f"extra     : {len(cmp.extra)}   (in the replay, not in the original)",
        f"renamed   : {len(cmp.renamed)}   (nf-core run metadata named by its launch time)",
        f"missing directories : {len(cmp.missing_directories)}",
        f"extra directories   : {len(cmp.extra_directories)}",
        f"changed links       : {len(cmp.changed_links)}   (target identities differ)",
        "environment         : " + (cmp.environment["status"] if cmp.environment else
                                    "not recorded by both runs")
        + "   (container images, plugins, staged remote inputs)",
        "",
    ]
    if cmp.unverified_structure:
        lines.append("The original has file checksums but no recorded output namespace. "
                     "The file comparison is shown, but directory agreement is unverified. "
                     "Start a fresh run to record its complete output namespace.")
    elif cmp.structurally_equal:
        lines.append("The replay produced the same set of files and directories as "
                     "the original run.")
        if cmp.renamed:
            lines.append(f"{len(cmp.renamed)} nf-core run-metadata file(s) are named by their "
                         "launch time; each is paired with its counterpart and compared by bytes, "
                         "as listed under renamed.")
        if cmp.changed or cmp.changed_links:
            lines.append(
                "Changed bytes may reflect timestamps or metadata, but may also reflect different "
                "scientific results. Link identities can differ with task work directories. "
                "File structure alone does not establish scientific agreement; "
                "inspect the changed results or use a format-aware comparison.")
        else:
            lines.append("All compared files are byte-identical and recorded link identities "
                         "match. This establishes output agreement, not the biological accuracy "
                         "of either run.")
    else:
        lines.append("The replay did NOT produce the same set of files and directories. Check "
                     "whether the runs completed and used the same inputs and settings.")
    if cmp.environment and cmp.environment["status"] == "differs":
        lines.append("The runs did NOT execute in the same environment (see environment "
                     "mismatches): the replay is not a reproduction of the original execution.")
    environment = cmp.environment or {}
    for label, paths in (("environment mismatches", environment.get("mismatches") or []),
                         ("environment unverified", environment.get("unverified") or []),
                         ("environment notes", environment.get("notes") or []),
                         ("renamed", cmp.renamed), ("missing", cmp.missing), ("extra", cmp.extra),
                         ("changed", cmp.changed),
                         ("missing directories", cmp.missing_directories),
                         ("extra directories", cmp.extra_directories),
                         ("changed links", cmp.changed_links)):
        if paths:
            lines.append("")
            lines.append(f"{label}:")
            lines += [f"  {p}" for p in paths]
    return "\n".join(lines) + "\n"
