"""Damaged single-end reads through the pinned fastqrepair 1.1.1, against one whole-file wipe.

fastqrepair scatters each FASTQ into chunks, wipes them separately and gathers the reads and
reports. These samples reach what the pinned splitter, wiper and report gatherer could not
handle: reads damaged so that fastqwiper must resynchronise, a single read and qualities full
of '@' (no line where a split is invisible to fastqwiper), and many repaired headers per chunk
(the pinned report gatherer kept one digit of each count). The check runs the pinned fastqwiper
container once on each whole input and requires the published reads and report to equal that
wipe byte for byte. It establishes that chunking changes nothing, not that the repair is right.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
import tempfile
from pathlib import Path

IMAGE = "quay.io/biocontainers/wipertools:1.1.5--pyhdfd78af_0"
COMMIT = "70a38209407b9367a9ff7ab8b26d84cb1983ea18"


def _record(name: str, length: int, quality: str = "I") -> list[str]:
    bases = "ACGTN"
    return [f"@{name}", "".join(bases[(i * 7 + len(name)) % 5] for i in range(length)), "+",
            (quality * length)[:length]]


def _damaged() -> bytes:
    lines: list[str] = []
    for i in range(90):
        record = _record(f"read{i} 1:N:0:1", 20 + i % 13)
        if i % 7 == 3:
            record[1] = record[1].lower()          # rejected sequence: fastqwiper resynchronises
        if i % 11 == 5:
            record.insert(2, "")                   # blank line inside a record
        if i % 13 == 6:
            del record[2]                          # missing '+' line
        if i % 17 == 8:
            record[0] = "\x01" + record[0][1:]     # unprintable header, rescued or dropped
        if i % 19 == 9:
            record[3] = "@" + record[3][1:]        # quality starting like a header
        if i % 23 == 10:
            record[3] = record[3][:-2]             # quality shorter than the sequence
        lines += record
    text = "\n".join(lines) + "\n"
    return text.replace("\n", "\r\n", 40).encode()  # some Windows line ends too


SAMPLES = {
    "damaged": _damaged(),
    "single_read": "\n".join(_record("only read", 30)).encode() + b"\n",
    "at_quality": "".join("\n".join(_record(f"q{i}", 24, "@I#F")) + "\n" for i in range(40)).encode(),
    # One clean header per block keeps restarts; each block repairs eleven misplaced headers.
    "fixed_headers": "".join(
        "\n".join(_record(f"block{b}", 25) if r == 0 else
                  [f"junk@fix{b}_{r}", *_record("x", 25)[1:]]) + "\n"
        for b in range(6) for r in range(12)).encode(),
}


def write_fixture(directory: Path, *, compressed: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for sample, content in SAMPLES.items():
        path = directory / f"{sample}.fastq{'.gz' if compressed else ''}"
        if compressed:
            with gzip.GzipFile(path, "wb", mtime=0) as handle:
                handle.write(content)
        else:
            path.write_bytes(content)
        rows.append([sample, str(path.resolve())])
    with (directory / "samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq_1"])
        writer.writerows(rows)


def whole_file_wipe(content: bytes, alphabet: str = "ACGTN") -> tuple[bytes, str]:
    """The pinned fastqwiper on the whole input, in the gzip form the pipeline wipes."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        with gzip.GzipFile(work / "whole.fastq.gz", "wb", mtime=0) as handle:
            handle.write(content)
        user = subprocess.run(["id", "-u"], capture_output=True, text=True, check=True).stdout.strip()
        group = subprocess.run(["id", "-g"], capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["docker", "run", "--rm", "-u", f"{user}:{group}", "-v", f"{work}:/w", "-w", "/w",
                        IMAGE, "wipertools", "fastqwiper", "-i", "whole.fastq.gz",
                        "-o", "whole_wiped.fastq.gz", "-r", "whole.report", "--alphabet", alphabet],
                       check=True, capture_output=True)
        with gzip.open(work / "whole_wiped.fastq.gz") as wiped:
            return wiped.read(), (work / "whole.report").read_text(encoding="utf-8")


def check_run(run: Path, *, source_run: Path | None = None, wipe=whole_file_wipe) -> dict[str, int]:
    # A commands.sh replay supervises Nextflow directly; its identity stays in the source bundle.
    manifest = json.loads(((source_run or run) / "provenance/run_manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("pipeline"), manifest.get("commit"), manifest.get("outcome")) != (
            "fastqrepair", COMMIT, "success"):
        raise ValueError("unvalidated pipeline or run outcome")
    outputs = run / "repaired"
    if {path.name for path in outputs.glob("*.fastq.gz")} != {f"{s}.fastq.gz" for s in SAMPLES}:
        raise ValueError(f"unexpected repaired inventory: {sorted(p.name for p in outputs.iterdir())}")
    clean = {}
    for sample, content in SAMPLES.items():
        reads, report = wipe(content)
        with gzip.open(outputs / f"{sample}.fastq.gz") as repaired:
            if repaired.read() != reads:
                raise ValueError(f"{sample}: repaired reads differ from one whole-file wipe")
        if (outputs / f"{sample}.report").read_text(encoding="utf-8") != report:
            raise ValueError(f"{sample}: gathered report differs from one whole-file wipe")
        clean[sample] = reads.count(b"\n") // 4
    return clean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fixture = sub.add_parser("fixture")
    fixture.add_argument("directory", type=Path)
    fixture.add_argument("--gzip", action="store_true", dest="compressed")
    check = sub.add_parser("check")
    check.add_argument("run", type=Path)
    check.add_argument("--source-run", type=Path)
    args = parser.parse_args()
    if args.command == "fixture":
        write_fixture(args.directory, compressed=args.compressed)
    else:
        print(check_run(args.run, source_run=args.source_run))
        print("Every sample's repaired reads and report equal one whole-file fastqwiper run.")


if __name__ == "__main__":
    main()
