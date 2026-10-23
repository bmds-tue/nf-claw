"""Independent basic-statistics check for completed nf-core/demo FastQC tasks.

Usage: python check_demo_fastqc_metrics.py RUN_OUTDIR --output evidence.json
Requires the task reports and staged reads to remain readable. For downloaded CI
evidence, use --work-root ARCHIVE/_temp/demo-fastqc-work to map the recorded task hashes
onto the retained work directory instead of the original runner's absolute paths.
Checks six reports from the bundled demo, not every FastQC module or biological accuracy.
GC is the integer percentage of G/C among canonical bases, as specified by FastQC 0.12.1:
https://github.com/s-andrews/FastQC/blob/v0.12.1/uk/ac/babraham/FastQC/Modules/BasicStats.java
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


def read_metrics(path: Path) -> dict:
    bases = Counter()
    reads, shortest, longest = 0, None, 0
    with gzip.open(path, "rt", encoding="ascii") as handle:
        while header := handle.readline():
            sequence = handle.readline().rstrip("\r\n")
            separator = handle.readline()
            quality = handle.readline().rstrip("\r\n")
            if not header.startswith("@") or not separator.startswith("+"):
                raise ValueError(f"malformed four-line FASTQ record in {path}, read {reads + 1}")
            if not sequence or len(sequence) != len(quality):
                raise ValueError(f"invalid sequence/quality lengths in {path}, read {reads + 1}")
            if set(sequence) - set("ACGTN"):
                raise ValueError(f"unsupported sequence alphabet in {path}, read {reads + 1}")
            reads += 1
            shortest = len(sequence) if shortest is None else min(shortest, len(sequence))
            longest = max(longest, len(sequence))
            bases.update(sequence)
    if not reads:
        raise ValueError(f"empty input: {path}")
    canonical = sum(bases[b] for b in "ACGT")
    return {
        "reads": reads,
        "total_bases": sum(bases.values()),
        "length": str(shortest) if shortest == longest else f"{shortest}-{longest}",
        "gc_percent": 100 * (bases["G"] + bases["C"]) // canonical if canonical else 0,
    }


def check_report(report: Path) -> dict:
    with zipfile.ZipFile(report) as archive:
        entries = [n for n in archive.namelist() if n.endswith("/fastqc_data.txt")]
        if len(entries) != 1:
            raise ValueError(f"expected one FastQC data entry: {report}")
        content = archive.read(entries[0]).decode("utf-8")
    if not content.startswith("##FastQC\t0.12.1\n"):
        raise ValueError(f"unvalidated FastQC version: {report}")
    block = content.split(">>Basic Statistics\t", 1)[1].split(">>END_MODULE", 1)[0]
    table = dict(line.split("\t", 1) for line in block.splitlines()
                 if "\t" in line and not line.startswith("#"))
    filename = table["Filename"]
    if Path(filename).name != filename:
        raise ValueError(f"unexpected input filename: {filename}")
    source = report.parent / filename
    expected = read_metrics(source)
    observed = {"reads": int(table["Total Sequences"]),
                "length": table["Sequence length"], "gc_percent": int(table["%GC"])}
    if int(table["Sequences flagged as poor quality"]) != 0:
        raise ValueError(f"filtered reads require a different oracle: {report}")
    for key, value in observed.items():
        if value != expected[key]:
            raise ValueError(f"{report}: {key}: observed {value!r}, expected {expected[key]!r}")
    return {"report": report.name, "input": source.name,
            "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "data_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "expected": expected, "observed": observed, "matches": True}


def compare_metrics(results: list[dict], baseline: list[dict]) -> None:
    current = {row["report"]: row for row in results}
    previous = {row["report"]: row for row in baseline}
    if len(current) != len(results) or len(previous) != len(baseline):
        raise ValueError("duplicate report identities in comparison")
    if current.keys() != previous.keys():
        raise ValueError("FastQC report inventory changed")
    for name in current:
        for key in ("input_sha256", "data_sha256", "expected", "observed"):
            if current[name][key] != previous[name][key]:
                raise ValueError(f"{name}: replay changed {key}")


def collect_reports(run: Path, *, work_root: Path | None = None) -> list[Path]:
    log = (run / ".nextflow.log").read_text(encoding="utf-8")
    directories = dict.fromkeys(re.findall(
        r"Task completed > TaskHandler\[.*?name: NFCORE_DEMO:DEMO:FASTQC .*?"
        r"status: COMPLETED; exit: 0;.*?workDir: ([^\]]+)\]", log))
    folders = [Path(folder) for folder in directories]
    if work_root is not None:
        mapped = []
        for folder in folders:
            parts = folder.parts[-2:]
            if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{2}", parts[0]) \
                    or not re.fullmatch(r"[0-9a-f]{30}", parts[1]):
                raise ValueError(f"unexpected Nextflow task path: {folder}")
            mapped.append(work_root.joinpath(*parts))
        folders = mapped
    reports = [p for folder in folders for p in sorted(folder.glob("*_fastqc.zip"))]
    if len(directories) != 3 or len(reports) != 6:
        raise ValueError(f"expected three completed demo FastQC tasks and six reports, found "
                         f"{len(directories)} tasks and {len(reports)} reports")
    if len({report.name for report in reports}) != len(reports):
        raise ValueError("duplicate report identities in completed demo tasks")
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--against", type=Path, help="compare inputs and full FastQC data tables "
                                                     "with prior evidence")
    parser.add_argument("--work-root", type=Path, help="retained work directory from a "
                                                       "downloaded CI artifact")
    args = parser.parse_args()
    reports = collect_reports(args.run, work_root=args.work_root)
    results = [check_report(report) for report in reports]
    if args.against is not None:
        compare_metrics(results, json.loads(args.against.read_text(encoding="utf-8"))["results"])
    args.output.write_text(json.dumps({"scope": "FastQC 0.12.1 basic statistics for bundled demo",
                                      "reports_checked": len(results), "results": results},
                                     indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"All {len(results)} reports match independently counted reads, lengths "
          "and GC percentages.")


if __name__ == "__main__":
    main()
