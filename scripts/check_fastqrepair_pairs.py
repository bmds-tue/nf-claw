"""Known-input read conservation and mate orientation for pinned fastqrepair 1.1.1.

The official bundled test filters its paired sample before BBMAP_REPAIR. This
independent fixture contains reordered mates and one orphan on each side.
It checks exact sequence/quality retention, pairing and singleton inventory;
it does not establish repair accuracy for arbitrary damaged sequencing data.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from pathlib import Path

from runner import runlog

# Distinct sequences and qualities expose mate swaps even if a tool rewrites headers.
READS = {
    "pairA/1": ("ACGT" * 19, "I" * 76),
    "pairA/2": ("TGCA" * 19, "H" * 76),
    "pairB/1": ("GATTACA" * 11, "G" * 77),
    "pairB/2": ("CCTAGGT" * 11, "F" * 77),
    "orphanLeft/1": ("AACCGGTT" * 9, "E" * 72),
    "orphanRight/2": ("TTGGCCAA" * 9, "D" * 72),
}
EXPECTED = {
    "paired_probe_1.fastq.gz": {"pairA/1", "pairB/1"},
    "paired_probe_2.fastq.gz": {"pairA/2", "pairB/2"},
    "paired_probe_singleton.fastq.gz": {"orphanLeft/1", "orphanRight/2"},
}


def write_fixture(directory: Path, *, compressed: bool = False,
                  unsuffixed: bool = False, single_record: bool = False,
                  single_end: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    for name, ids in (("left", ("pairA/1", "orphanLeft/1", "pairB/1")),
                      ("right", ("pairB/2", "pairA/2", "orphanRight/2"))):
        if single_record:
            ids = ("pairA/1" if name == "left" else "pairA/2",)
        text = "".join(f"@{key.rsplit('/', 1)[0] if unsuffixed else key}\n{READS[key][0]}\n+\n{READS[key][1]}\n"
                       for key in ids)
        path = directory / f"{name}.fastq{'.gz' if compressed else ''}"
        if compressed:
            with gzip.open(path, "wt", encoding="ascii") as handle:
                handle.write(text)
        else:
            path.write_text(text, encoding="ascii")
    with (directory / "samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq_1", "fastq_2"])
        suffix = ".fastq.gz" if compressed else ".fastq"
        writer.writerow(["paired_probe", str((directory / f"left{suffix}").resolve()),
                         "" if single_end else str((directory / f"right{suffix}").resolve())])
    # Deliberately perturb task arrival order: completion order must not determine mate identity.
    (directory / "arrival.config").write_text(
        "process {\n    withName: '.*:WIPERTOOLS_FASTQGATHER' {\n"
        "        beforeScript = { meta.id in ['left', 'paired_probe_recovered_1'] ? 'sleep 3' : '' }\n    }\n}\n",
        encoding="utf-8")


def read_fastq(path: Path) -> dict[str, tuple[str, str]]:
    records = {}
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "rt", encoding="ascii") as handle:
        while header := handle.readline():
            sequence = handle.readline().rstrip("\r\n")
            plus = handle.readline()
            quality = handle.readline().rstrip("\r\n")
            if not header.startswith("@") or not plus.startswith("+") or not sequence:
                raise ValueError(f"invalid FASTQ record in {path}")
            if len(sequence) != len(quality) or any(not 33 <= ord(c) <= 126 for c in quality):
                raise ValueError(f"invalid sequence/quality in {path}")
            key = header[1:].split()[0]
            if key in records:
                raise ValueError(f"duplicate read {key!r} in {path}")
            records[key] = (sequence, quality)
    return records


def check_run(run: Path, *, source_run: Path | None = None, compressed: bool = False,
              unsuffixed: bool = False, single_record: bool = False,
              single_end: bool = False, skip_pairing: bool = False,
              phred64: bool = False) -> dict[str, int]:
    # A commands.sh replay supervises Nextflow directly; identity remains in the
    # guarded source bundle, while the replay records its own engine log/outcome.
    identity = source_run or run
    manifest = json.loads((identity / "provenance/run_manifest.json").read_text(encoding="utf-8"))
    expected_identity = {"pipeline": "fastqrepair", "version": "1.1.1",
                         "commit": "70a38209407b9367a9ff7ab8b26d84cb1983ea18",
                         "nextflow": "nextflow version 25.10.4", "outcome": "success"}
    if any(manifest.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("unvalidated pipeline, engine or run outcome")
    if phred64 and json.loads((identity / "provenance/params.json").read_text(encoding="utf-8")).get("qin") != 64:
        raise ValueError("Phred+64 control must declare its input quality offset")
    if source_run is not None:
        log = run / "provenance/logs/run.log"
        if runlog.read_state(log).state != "success":
            raise ValueError("replay must record its own successful outcome")
        # Archived evidence retains the original absolute origin; a relocated
        # source bundle records its new physical origin when commands.sh runs.
        origins = {f"    replay of: {manifest['outdir']}", f"    replay of: {source_run.resolve()}",
                   f"    replay of: {source_run.absolute()}"}
        if not origins.intersection(log.read_text(encoding="utf-8").split("\n")):
            raise ValueError("replay origin disagrees with the validated source bundle")
        engine_log = (run / ".nextflow.log").read_text(encoding="utf-8", errors="replace")
        versions = re.findall(r"nextflow.cli.CmdRun - N E X T F L O W\s+~\s+version (\S+)", engine_log)
        if versions != ["25.10.4"]:
            raise ValueError("replay engine differs from the validated engine")
    outputs = run / "repaired"
    expected_inventory = EXPECTED
    if single_end:
        expected_inventory = {"paired_probe.fastq.gz": {key for key in READS if key.endswith("/1")}}
    elif skip_pairing:
        expected_inventory = {f"paired_probe_{mate}.fastq.gz": {key for key in READS if key.endswith(f"/{mate}")}
                              for mate in (1, 2)}
    inventory = {path.name for path in outputs.glob("*.fastq.gz")}
    if inventory != set(expected_inventory):
        raise ValueError(f"unexpected repaired inventory: {sorted(inventory)}")
    counts = {}
    for filename, ids in expected_inventory.items():
        if single_record:
            ids = {key for key in ids if key.startswith("pairA/")}
        records = read_fastq(outputs / filename)
        expected = {key.rsplit("/", 1)[0] if unsuffixed else key: READS[key] for key in ids}
        if phred64 and not single_end and not skip_pairing:
            expected = {key: (sequence, "".join(chr(ord(char) - 64 + 33) for char in quality))
                        for key, (sequence, quality) in expected.items()}
        if records != expected:
            raise ValueError(f"read identities, mate orientation, sequences or qualities changed: {filename}")
        counts[filename] = len(records)
    reports = outputs if single_end else outputs / "reports/paired_probe"
    expected_reports = ({"paired_probe.report"} if single_end else
                        {"paired_probe_recovered_1.report", "paired_probe_recovered_2.report"}
                        if compressed else {"left.report", "right.report"})
    if {path.name for path in reports.glob("*.report")} != expected_reports:
        raise ValueError("both mate repair reports must be retained separately")
    for path in reports.glob("*.report"):
        text = path.read_text(encoding="utf-8")
        count = 1 if single_record else 3
        if (re.search(rf"(?m)^Total lines: {4 * count}$", text) is None
                or re.search(rf"(?m)^Clean reads: {count}$", text) is None):
            raise ValueError("mate repair report disagrees with the known input inventory")
    log = outputs / "paired_probe.repair.sh.log"
    repaired_pairs = not single_end and not skip_pairing
    if repaired_pairs and (not log.is_file() or not log.read_text(encoding="utf-8", errors="replace").strip()):
        raise ValueError("BBMap repair diagnostics must be retained separately from singleton reads")
    if not repaired_pairs and log.exists():
        raise ValueError("unexpected BBMap diagnostics for an unrepaired control")
    traces = list((run / "pipeline_info").glob("execution_trace*.txt"))
    if len(traces) != 1:
        raise ValueError("expected one fresh execution trace")
    with traces[0].open(encoding="utf-8") as handle:
        tasks = list(csv.DictReader(handle, delimiter="\t"))
    repair = [row for row in tasks if ":BBMAP_REPAIR " in row.get("name", "")]
    if repaired_pairs and (len(repair) != 1 or repair[0].get("status") != "COMPLETED" or repair[0].get("exit") != "0"):
        raise ValueError("BBMAP_REPAIR must execute successfully; stubs or skipped pairing are insufficient")
    if not repaired_pairs and repair:
        raise ValueError("BBMAP_REPAIR must be absent for this single-end or skip-pairing control")
    recovery = [row for row in tasks if ":GZRT " in row.get("name", "")]
    if compressed and (len(recovery) != 1 or recovery[0].get("status") != "COMPLETED"
                       or recovery[0].get("exit") != "0"):
        raise ValueError("GZRT must execute successfully for the gzip source control")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fixture = sub.add_parser("fixture")
    fixture.add_argument("directory", type=Path)
    fixture.add_argument("--gzip", action="store_true", dest="compressed")
    fixture.add_argument("--unsuffixed", action="store_true")
    fixture.add_argument("--single-record", action="store_true")
    fixture.add_argument("--single-end", action="store_true")
    check = sub.add_parser("check")
    check.add_argument("run", type=Path)
    check.add_argument("--source-run", type=Path)
    check.add_argument("--gzip", action="store_true", dest="compressed")
    check.add_argument("--unsuffixed", action="store_true")
    check.add_argument("--single-record", action="store_true")
    check.add_argument("--single-end", action="store_true")
    check.add_argument("--skip-pairing", action="store_true")
    check.add_argument("--phred64", action="store_true")
    args = parser.parse_args()
    if args.command == "fixture":
        write_fixture(args.directory, compressed=args.compressed,
                      unsuffixed=args.unsuffixed, single_record=args.single_record, single_end=args.single_end)
    else:
        print(check_run(args.run, source_run=args.source_run, compressed=args.compressed,
                        unsuffixed=args.unsuffixed, single_record=args.single_record,
                        single_end=args.single_end, skip_pairing=args.skip_pairing, phred64=args.phred64))
        print("Known pairs and singletons retain their exact sequences, qualities and mate identity.")


if __name__ == "__main__":
    main()
