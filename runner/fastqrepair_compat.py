"""Recorded runtime corrections for the fingerprinted fastqrepair 1.1.1 release.

The pinned repository stays unchanged. Generated task recipes use this standalone
splitter, wipe placeholder chunks, gather reports exactly, repair a missing shell
continuation, and preserve distinct publications. The complete helper source is
embedded into the recorded config, so replay does not depend on the installed
nfclaw version or the original helper path.

Splitting is invisible to fastqwiper: a chunk starts only at a line where
fastqwiper, wiping the unsplit file, would start a record afresh whatever its
`--alphabet`, so the gathered reads and summed report equal one whole-file wipe.
The pinned subworkflow iterates the chunk list and fails on a single chunk, and
fastqwiper fails on an empty one; when a file holds no such line it is wiped
whole, beside a zero-byte placeholder chunk that yields an empty output and a
zero report.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import shlex
import sys
from contextlib import ExitStack
from pathlib import Path

SUPPORTED_COMMIT = "70a38209407b9367a9ff7ab8b26d84cb1983ea18"

# fastqwiper reads gzip chunks through io.TextIOWrapper (universal newlines) and plain chunks
# through codecs.open, whose readline splits wherever str.splitlines does.
_BREAKS = {"gz": re.compile(rb"\r\n|\r|\n"),
           "plain": re.compile(rb"\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e]|\xc2\x85|\xe2\x80[\xa8\xa9]")}

# The fastqwiper 1.1.5 report, field by field (`Bad headers …` also carries the fixed count).
_FIELDS = ("Total lines", "Well-formed lines", "Clean reads", "Bad headers or misplaced lines",
           "BAD SEQ lines", "BAD '+' lines", "BAD QUAL lines",
           "Reads discarded because len(SEQ) neq len(QUAL)", "Blank lines")
_PERCENT = {"Well-formed lines", "Bad headers or misplaced lines", "BAD SEQ lines", "BAD '+' lines",
            "BAD QUAL lines", "Blank lines"}


def _source() -> bytes:
    return globals().get("_NFCLAW_COMPAT_SOURCE") or Path(__file__).read_bytes()


def recipe_digest() -> str:
    return hashlib.sha256(_source()).hexdigest()


def _command() -> str:
    encoded = base64.b64encode(_source()).decode("ascii")
    bootstrap = f"import base64; _NFCLAW_COMPAT_SOURCE=base64.b64decode('{encoded}'); exec(_NFCLAW_COMPAT_SOURCE)"
    return shlex.join(["python3", "-c", bootstrap])


def _open_source(path: Path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def _lines(handle, breaks):
    """The source's lines, split as fastqwiper splits a chunk (`handle` yields b"\\n"-ended lines)."""
    for raw in handle:
        start = 0
        for match in breaks.finditer(raw):
            yield raw[start:match.end()]
            start = match.end()
        if start < len(raw):
            yield raw[start:]


def _restarts(lines):
    """Pair each line with whether fastqwiper, wiping the whole input, restarts afresh there.

    fastqwiper treats a non-blank line as a header candidate, consumes at most three more
    non-blank lines for it, rejects a printable candidate without `@` on its own, and carries
    only the last clean header's length between records. A clean header (printable, its only
    `@` first) preceded by three non-blank lines that are printable and lack `@` therefore
    begins a record in every reading of the earlier lines, for any alphabet, and resets the
    carried length: wiping from there on its own matches the whole-file wipe line for line.
    """
    quiet = 0
    for line in lines:
        text = line.decode("utf-8", "replace").rstrip()
        if not text:
            yield line, False
            continue
        printable = text.isprintable()
        yield line, quiet >= 3 and printable and text.rfind("@") == 0
        quiet = quiet + 1 if printable and "@" not in text else 0


def _scan(path: Path, breaks) -> tuple[int, int, str]:
    lines = restarts = 0
    digest = hashlib.sha256()
    with _open_source(path) as handle:
        for line, restart in _restarts(_lines(handle, breaks)):
            lines += 1
            restarts += restart
            digest.update(line)
    return lines, restarts, digest.hexdigest()


def scatter(path: Path, splits: int, prefix: str, folder: Path, *,
            extension: str = "fastq.gz", suffix: str = "") -> list[Path]:
    if splits < 1 or Path(prefix).name != prefix or not prefix or "/" in suffix:
        raise ValueError("invalid chunk count or filename prefix/suffix")
    breaks = _BREAKS["gz" if extension.endswith(".gz") else "plain"]
    lines, restarts, original_digest = _scan(path, breaks)
    if not lines:
        raise ValueError(f"{path} holds no FASTQ lines; fastqwiper cannot report on an empty input")
    segments = restarts + 1
    n = min(splits, segments)
    # Chunk i holds segments [starts[i], starts[i + 1]): a balanced share of whole segments.
    starts = [0]
    for index in range(n):
        starts.append(starts[-1] + segments // n + (index < segments % n))
    if n == 1:
        print(f"nfclaw: {path.name} has no line where fastqwiper restarts afresh; wiping it whole "
              "beside an empty placeholder chunk", file=sys.stderr)
    total = max(n, 2)
    width = max(3, len(str(total - 1)))
    names = [folder / f"{prefix}_{index:0{width}d}{'_' + suffix if suffix else ''}.{extension}"
             for index in range(total)]
    folder.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256()
    with _open_source(path) as source, ExitStack() as stack:
        chunk, segment = -1, 0
        for line, restart in _restarts(_lines(source, breaks)):
            segment += restart
            if chunk + 1 < n and segment == starts[chunk + 1]:
                chunk += 1
                stack.close()  # the previous chunk, before the next one opens
                raw = stack.enter_context(names[chunk].open("xb"))
                output = (stack.enter_context(gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                                                           compresslevel=6, mtime=0))
                          if extension.endswith(".gz") else raw)
            output.write(line)
            digest.update(line)
        if chunk != n - 1 or digest.hexdigest() != original_digest:
            raise ValueError("FASTQ input changed between framing and splitting")
    for placeholder in names[n:]:
        placeholder.open("xb").close()
    return names


def _zero_report() -> str:
    return "FASTQWIPER REPORT:\n\n" + "".join(
        f"{field}: 0" + (" (0.0%)" if field in _PERCENT else "")
        + (" of which 0 fixed" if field == "Bad headers or misplaced lines" else "") + "\n"
        for field in _FIELDS)


def wipe(argv: list[str]) -> None:
    """fastqwiper for one chunk; a zero-byte placeholder chunk yields an empty output and zero report."""
    parser = argparse.ArgumentParser(prog="wipe", add_help=False, allow_abbrev=False)
    parser.add_argument("-i", "--fastq_in", required=True)
    parser.add_argument("-o", "--fastq_out", required=True)
    parser.add_argument("-r", "--report")
    known, _ = parser.parse_known_args(argv)
    if os.path.getsize(known.fastq_in):
        sys.stdout.flush()
        os.execvp("wipertools", ["wipertools", "fastqwiper", *argv])
    with open(known.fastq_out, "xb") as raw:
        if known.fastq_out.endswith(".gz"):
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0).close()
    if known.report:
        Path(known.report).write_text(_zero_report())
    else:
        print(_zero_report(), end="")


def _parse_report(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in path.read_text().splitlines():
        for field in _FIELDS:
            if line.startswith(field + ":"):
                rest = r" \(\d+(?:\.\d+)?%\)" if field in _PERCENT else ""
                fixed = r" of which (\d+) fixed" if field == "Bad headers or misplaced lines" else ""
                match = re.fullmatch(re.escape(field) + r": (\d+)" + rest + fixed, line)
                if field in counts or not match:
                    raise ValueError(f"{path}: unrecognized fastqwiper report line: {line!r}")
                counts[field] = int(match[1])
                if fixed:
                    counts["fixed"] = int(match[2])
    if len(counts) != len(_FIELDS) + 1:
        raise ValueError(f"{path}: incomplete fastqwiper report")
    return counts


def gather_reports(reports: list[Path], final: Path) -> None:
    """Sum fastqwiper reports exactly; the pinned reportgather keeps one digit of each fixed count."""
    totals = {key: 0 for key in (*_FIELDS, "fixed")}
    for report in reports:
        for key, value in _parse_report(report).items():
            totals[key] += value
    if not totals["Total lines"]:
        raise ValueError("fastqwiper reports hold no lines")

    def share(field: str) -> str:
        return f" ({round((totals[field] / totals['Total lines']) * 100, 2)}%)"

    final.write_text("FASTQWIPER REPORT:\n\n" + "".join(
        f"{field}: {totals[field]}" + (share(field) if field in _PERCENT else "")
        + (f" of which {totals['fixed']} fixed" if field == "Bad headers or misplaced lines" else "")
        + "\n" for field in _FIELDS))


# Each corrected task: the pinned invocation, its version line (None: the tool still runs), the
# replacement subcommand and the version line recorded instead.
_TASKS = {
    "scatter": ("wipertools \\\n    fastqscatter \\\n",
                "wipertools fastqscatter: $(wipertools fastqscatter --version)", "scatter",
                "nfclaw_record_scatter"),
    "wiper": ("wipertools \\\n    fastqwiper \\\n", None, "wipe", None),
    "reportgather": ("wipertools \\\n    reportgather \\\n",
                     "wipertools reportgather: $(wipertools reportgather --version)", "reportgather",
                     "nfclaw_record_reportgather"),
}


def patch_task(kind: str, path: Path) -> None:
    source = path.read_text()
    if kind in _TASKS:
        needle, version, subcommand, recorded = _TASKS[kind]
        if source.count(needle) != 1 or (version is not None and source.count(version) != 1):
            raise ValueError(f"unrecognized pinned {kind} task; runtime correction refused")
        command = _command()
        corrected = source.replace(needle, f"{command} {subcommand} \\\n", 1)
        if version is not None:
            corrected = corrected.replace(version, f"{recorded}: $({command} version)", 1)
    elif kind == "repair":
        corrected, matches = re.subn(r"(?m)^(\s*threads=\d+)\n", r"\1 \\\n", source)
        if matches != 1 or "qin=" not in source:
            raise ValueError("unrecognized pinned repair task; runtime correction refused")
    else:
        raise ValueError("unknown task correction")
    temp = path.with_name(path.name + ".nfclaw.tmp")
    try:
        temp.write_text(corrected)
        temp.chmod(path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_config(target: Path) -> Path:
    command = _command()
    hooks = {f"{kind.upper()}_HOOK": json.dumps(f"{command} patch {kind} .command.sh")
             for kind in ("scatter", "wiper", "reportgather", "repair")}
    salt = recipe_digest()[:16]
    config = """// nfclaw runtime correction for fastqrepair 1.1.1; pinned source is unchanged.
process {
    withName: 'WIPERTOOLS_FASTQSCATTER' {
        beforeScript = SCATTER_HOOK
        ext.prefix = { "${meta.id}__nfclaw_RECIPE" }
    }
    withName: 'WIPERTOOLS_FASTQWIPER' {
        beforeScript = WIPER_HOOK
    }
    withName: 'WIPERTOOLS_FASTQGATHER' {
        ext.prefix = { "${meta.id}_gather__nfclaw_RECIPE" }
    }
    withName: 'BBMAP_REPAIR' {
        beforeScript = REPAIR_HOOK
        ext.prefix = { "${meta.id}__nfclaw_RECIPE" }
        publishDir = [path: { "${params.outdir}/repaired" }, mode: "${-> params.publish_dir_mode}",
            overwrite: true, saveAs: { filename ->
                if (filename == 'versions.yml') return null
                if (filename.endsWith('.repair.sh.log')) return "${meta.id}.repair.sh.log"
                if (filename.endsWith('_1_repaired.fastq.gz')) return "${meta.id}_1.fastq.gz"
                if (filename.endsWith('_2_repaired.fastq.gz')) return "${meta.id}_2.fastq.gz"
                if (filename.endsWith('_singleton.fastq.gz')) return "${meta.id}_singleton.fastq.gz"
                throw new IllegalStateException("Unexpected BBMAP_REPAIR publication: ${filename}")
            }]
    }
    withName: 'WIPERTOOLS_REPORTGATHER' {
        beforeScript = REPORTGATHER_HOOK
        publishDir = [path: { "${params.outdir}/repaired" }, mode: "${-> params.publish_dir_mode}",
            overwrite: true, saveAs: { filename ->
                if (filename == 'versions.yml') return null
                return meta.single_end ? "${meta.sample_id}.report" : "reports/${meta.sample_id}/${meta.id}.report"
            }]
    }
    withName: 'FASTQC' {
        publishDir = [path: { "${params.outdir}/QC/fastqc" }, mode: "${-> params.publish_dir_mode}",
            overwrite: true, saveAs: { filename -> filename == 'versions.yml' ? null : filename }]
    }
    withName: 'MULTIQC' {
        publishDir = [path: { "${params.outdir}/QC/multiqc" }, mode: "${-> params.publish_dir_mode}",
            overwrite: true, saveAs: { filename -> filename == 'versions.yml' ? null : filename }]
    }
}
""".replace("RECIPE", salt)
    for name, hook in hooks.items():
        config = config.replace(name, hook)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(config)
    return target


def main() -> None:
    if sys.argv[1:2] == ["wipe"]:
        # fastqwiper's own options pass through unchanged, so they are not parsed here.
        wipe(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version")
    patch = sub.add_parser("patch")
    patch.add_argument("kind", choices=(*_TASKS, "repair"))
    patch.add_argument("script", type=Path)
    split = sub.add_parser("scatter")
    split.add_argument("-f", "--fastq", type=Path, required=True)
    split.add_argument("-n", "--num_splits", type=int, required=True)
    split.add_argument("-p", "--prefix", required=True)
    split.add_argument("-s", "--suffix", default="", nargs="?", const="")
    split.add_argument("-e", "--ext", choices=("fastq", "fq", "fastq.gz", "fq.gz"), default="fastq.gz")
    split.add_argument("-o", "--out_folder", type=Path, default=Path("chunks"))
    split.add_argument("-O", "--os", choices=("unix", "cross_platform"), default="unix")
    gather = sub.add_parser("reportgather")
    gather.add_argument("-r", "--reports", type=Path, nargs="+", required=True)
    gather.add_argument("-f", "--final_report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "version":
        print("nfclaw-record-scatter-sha256:" + recipe_digest())
    elif args.command == "patch":
        patch_task(args.kind, args.script)
    elif args.command == "scatter":
        scatter(args.fastq, args.num_splits, args.prefix, args.out_folder,
                extension=args.ext, suffix=args.suffix)
    else:
        gather_reports(args.reports, args.final_report)


if __name__ == "__main__":
    main()
