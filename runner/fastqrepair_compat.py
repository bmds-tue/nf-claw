"""Recorded runtime corrections for the fingerprinted fastqrepair 1.1.1 release.

The pinned repository stays unchanged. Generated task recipes use this standalone
splitter, repair a missing shell continuation, and preserve distinct publications.
The complete helper source is embedded into the recorded config, so replay does
not depend on the installed nfclaw version or the original helper path.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import os
import re
import shlex
import sys
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit

SUPPORTED_COMMIT = "70a38209407b9367a9ff7ab8b26d84cb1983ea18"


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


def _scan(path: Path) -> tuple[int, bool, str]:
    count, framed = 0, True
    digest = hashlib.sha256()
    with _open_source(path) as handle:
        while header := handle.readline():
            sequence, plus, quality = handle.readline(), handle.readline(), handle.readline()
            for line in (header, sequence, plus, quality):
                digest.update(line)
            if (not header.startswith(b"@") or not plus.startswith(b"+") or not sequence
                    or not quality or len(sequence.rstrip(b"\r\n")) != len(quality.rstrip(b"\r\n"))):
                framed = False
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
                break
            count += 1
    return count, framed, digest.hexdigest()


def scatter(path: Path, splits: int, prefix: str, folder: Path, *,
            extension: str = "fastq.gz", suffix: str = "", ensure_list: bool = False) -> list[Path]:
    if splits < 1 or Path(prefix).name != prefix or not prefix or "/" in suffix:
        raise ValueError("invalid chunk count or filename prefix/suffix")
    count, framed, original_digest = _scan(path)
    n = min(splits, count) if framed and count else 1
    if not framed:
        print("nfclaw: ambiguous FASTQ framing; preserve the complete input in one chunk before wiping",
              file=sys.stderr)
    folder.mkdir(parents=True, exist_ok=False)
    width = max(3, len(str(n - 1)))
    files = []
    digest = hashlib.sha256()
    with _open_source(path) as source:
        for index in range(n):
            target = folder / f"{prefix}_{index:0{width}d}{'_' + suffix if suffix else ''}.{extension}"
            files.append(target)
            with ExitStack() as stack:
                raw = stack.enter_context(target.open("xb"))
                output = (stack.enter_context(gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                                                           compresslevel=6, mtime=0))
                          if extension.endswith(".gz") else raw)
                if not framed or not count:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(block)
                        digest.update(block)
                else:
                    size = count // n + (index < count % n)
                    for _ in range(size * 4):
                        line = source.readline()
                        if not line:
                            raise ValueError("FASTQ input changed after framing check")
                        output.write(line)
                        digest.update(line)
        if source.read(1) or digest.hexdigest() != original_digest:
            raise ValueError("FASTQ input changed between framing and splitting")
    if ensure_list and len(files) == 1:
        target = folder / f"{prefix}_{1:0{width}d}{'_' + suffix if suffix else ''}.{extension}"
        with target.open("xb") as raw:
            if extension.endswith(".gz"):
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0):
                    pass
        files.append(target)
    return files


def paired_input_roles(path: Path | None) -> dict[str, list[str]]:
    """The stream identities that survive the exact pinned decoupling/recovery code."""
    if path is None:
        return {}
    orders, seen = {}, set()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream, delimiter="\t" if path.suffix == ".tsv" else ","):
            first, second = (row.get("fastq_1") or "").strip(), (row.get("fastq_2") or "").strip()
            sample = row["sample"].strip()
            if sample in seen:
                raise ValueError(f"sample {sample} occurs more than once; its stream identity would collapse")
            seen.add(sample)
            if not second:
                continue
            names = [Path(urlsplit(value).path if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value)
                          else value).name for value in (first, second)]
            if names[0] == names[1]:
                raise ValueError(f"paired sample {sample} has the same staged filename for both mates")
            if names[0].endswith(".gz") != names[1].endswith(".gz"):
                raise ValueError(f"paired sample {sample} mixes gzip and plain streams; use matching formats")
            orders[sample] = ([sample + "_recovered_1", sample + "_recovered_2"]
                              if names[0].endswith(".gz") else [Path(name).stem for name in names])
            if len(set(orders[sample])) != 2:
                raise ValueError(f"paired sample {sample} has the same decoupled identity for both mates")
    return orders


def wiper(arguments: list[str]) -> None:
    """Pass nonempty data to the pinned tool; empty compatibility chunks have zero counts."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", "--fastq_in", type=Path, required=True)
    parser.add_argument("-o", "--fastq_out", type=Path, required=True)
    parser.add_argument("-r", "--report", type=Path, required=True)
    args, _ = parser.parse_known_args(arguments)
    with _open_source(args.fastq_in) as handle:
        empty = not handle.read(1)
    if not empty:
        os.execvp("wipertools", ["wipertools", "fastqwiper", *arguments])
    with args.fastq_out.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0):
            pass
    args.report.write_text(
        "FASTQWIPER REPORT:\n\nTotal lines: 0\nWell-formed lines: 0 (not applicable)\nClean reads: 0\n"
        "Bad headers or misplaced lines: 0 (not applicable) of which 0 fixed\n"
        "BAD SEQ lines: 0 (not applicable)\nBAD '+' lines: 0 (not applicable)\n"
        "BAD QUAL lines: 0 (not applicable)\nReads discarded because len(SEQ) neq len(QUAL): 0\n"
        "Blank lines: 0 (not applicable)\n")


def _ordered_inputs(source: str, orders: dict[str, list[str]]) -> str:
    match = re.search(r"\bout=([^\s]+)__nfclaw_[0-9a-f]{16}_1_repaired\.fastq\.gz", source)
    inputs = re.findall(r"(?<!\S)in(?:2)?=([^\s]+)", source)
    if match is None or len(inputs) != 2:
        raise ValueError("unrecognized pinned paired repair inputs; orientation correction refused")
    wanted = orders.get(match[1])
    if wanted:
        roles = [re.sub(r"_gather__nfclaw_[0-9a-f]{16}\.fastq\.gz$", "", name) for name in inputs]
        if sorted(roles) != sorted(wanted) or len(set(roles)) != 2:
            raise ValueError("gathered mate identities disagree with the declared samplesheet")
        ordered = [inputs[roles.index(role)] for role in wanted]
    else:
        def mate(name):
            role = None
            with _open_source(Path(name)) as stream:
                while line := stream.readline():
                    header = line.decode("utf-8").split()
                    labels = set()
                    if header and header[0].startswith("@") and header[0].endswith(("/1", "/2")):
                        labels.add(int(header[0][-1]))
                    if len(header) > 1 and header[1].startswith(("1:", "2:")):
                        labels.add(int(header[1][0]))
                    sequence, plus, quality = stream.readline(), stream.readline(), stream.readline()
                    if (len(labels) != 1 or not header or not header[0].startswith("@")
                            or not plus.startswith(b"+") or not sequence or not quality
                            or len(sequence.rstrip(b"\r\n")) != len(quality.rstrip(b"\r\n"))):
                        return None
                    current = labels.pop()
                    if role is not None and role != current:
                        return None
                    role = current
            return role
        roles = [mate(name) for name in inputs]
        if sorted(role or 0 for role in roles) != [1, 2]:
            raise ValueError("mate order cannot be verified from this profile; supply an explicit local samplesheet")
        ordered = [inputs[roles.index(index)] for index in (1, 2)]
    return re.sub(r"(?<!\S)in(?:2)?=([^\s]+)",
                  lambda match: ("in2=" if match[0].startswith("in2=") else "in=")
                  + ordered[1 if match[0].startswith("in2=") else 0], source)


def patch_task(kind: str, path: Path, *, mate_orders: dict[str, list[str]] | None = None) -> None:
    source = path.read_text()
    if kind == "scatter":
        needle = "wipertools \\\n    fastqscatter \\\n"
        version = "wipertools fastqscatter: $(wipertools fastqscatter --version)"
        if source.count(needle) != 1 or source.count(version) != 1:
            raise ValueError("unrecognized pinned scatter task; runtime correction refused")
        command = _command()
        corrected = source.replace(needle, command + " scatter --ensure-list \\\n", 1).replace(
            version, f"nfclaw_record_scatter: $({command} version)", 1)
    elif kind == "repair":
        corrected, matches = re.subn(r"(?m)^(\s*threads=\d+)\n", r"\1 \\\n", source)
        if matches != 1 or "qin=" not in source:
            raise ValueError("unrecognized pinned repair task; runtime correction refused")
        if mate_orders is not None:
            corrected = _ordered_inputs(corrected, mate_orders)
    elif kind == "wipe":
        needle = "wipertools \\\n    fastqwiper \\\n"
        if source.count(needle) != 1:
            raise ValueError("unrecognized pinned wiping task; empty-chunk correction refused")
        corrected = source.replace(needle, _command() + " wiper \\\n", 1)
        version = "wipertools fastqwiper: $(wipertools fastqwiper --version)"
        corrected = corrected.replace(version, version + "\n    nfclaw_empty_chunk: $(" + _command() + " version)")
    else:
        raise ValueError("unknown task correction")
    temp = path.with_name(path.name + ".nfclaw.tmp")
    try:
        temp.write_text(corrected)
        temp.chmod(path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_config(target: Path, *, input_path: Path | None = None) -> Path:
    command = _command()
    scatter_hook = json.dumps(command + " patch scatter .command.sh")
    orders = paired_input_roles(input_path)
    encoded = base64.b64encode(json.dumps(orders, sort_keys=True).encode()).decode()
    repair_hook = json.dumps(command + " patch repair .command.sh --mate-orders " + encoded)
    # Keep a large cohort map out of process argv. Groovy selects only this task's
    # sample, and bounded string literals avoid the JVM constant-size ceiling.
    serialized = json.dumps(orders, sort_keys=True)
    fragments = ", ".join(json.dumps(serialized[index:index + 8000])
                          for index in range(0, len(serialized), 8000))
    order_expression = f"new groovy.json.JsonSlurper().parseText([{fragments}].join(''))"
    if orders:
        repair_hook = ("{\n            def roles = " + order_expression + "\n"
                       "            def pair = roles[meta.id]\n"
                       "            def selection = pair == null ? [:] : [(meta.id): pair]\n"
                       "            return " + json.dumps(command + " patch repair .command.sh")
                       + ' + " --mate-orders " + groovy.json.JsonOutput.toJson(selection).bytes.encodeBase64().toString()\n'
                       "        }")
    wipe_hook = json.dumps(command + " patch wipe .command.sh")
    salt = (hashlib.sha256(_source() + encoded.encode()).hexdigest()[:16] if orders else recipe_digest()[:16])
    config = """// nfclaw runtime correction for fastqrepair 1.1.1; pinned source is unchanged.
process {
    withName: 'WIPERTOOLS_FASTQSCATTER' {
        beforeScript = SCATTER_HOOK
        ext.prefix = { "${meta.id}__nfclaw_RECIPE" }
    }
    withName: 'WIPERTOOLS_FASTQGATHER' {
        ext.prefix = { "${meta.id}_gather__nfclaw_RECIPE" }
        publishDir = [path: { "${params.outdir}/repaired" }, mode: "${-> params.publish_dir_mode}",
            enabled: true, overwrite: true,
            saveAs: { filename ->
                if (filename == 'versions.yml') return null
                if (!meta.single_end && !params.skip_bbmap_repair) return null
                if (meta.single_end) return "${meta.sample_id}.fastq.gz"
                def roles = MATE_ORDERS
                def pair = roles[meta.sample_id]
                if (pair == null || !pair.contains(meta.id))
                    throw new IllegalStateException("Cannot publish unverified mate identity; supply an explicit local samplesheet")
                return "${meta.sample_id}_${pair.indexOf(meta.id) + 1}.fastq.gz"
            }]
    }
    withName: 'WIPERTOOLS_FASTQWIPER' {
        beforeScript = WIPE_HOOK
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
"""
    replacements = {"RECIPE": salt, "SCATTER_HOOK": scatter_hook, "REPAIR_HOOK": repair_hook,
                    "WIPE_HOOK": wipe_hook, "MATE_ORDERS": order_expression}
    # Expand only the original template. Sample identifiers and embedded helper
    # source can contain literal marker words and must never be expanded again.
    config = re.sub("|".join(replacements), lambda match: replacements[match[0]], config)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(config)
    return target


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "wiper":
        wiper(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version")
    patch = sub.add_parser("patch")
    patch.add_argument("kind", choices=("scatter", "repair", "wipe"))
    patch.add_argument("script", type=Path)
    patch.add_argument("--mate-orders")
    split = sub.add_parser("scatter")
    split.add_argument("-f", "--fastq", type=Path, required=True)
    split.add_argument("-n", "--num_splits", type=int, required=True)
    split.add_argument("-p", "--prefix", required=True)
    split.add_argument("-s", "--suffix", default="", nargs="?", const="")
    split.add_argument("-e", "--ext", choices=("fastq", "fq", "fastq.gz", "fq.gz"), default="fastq.gz")
    split.add_argument("-o", "--out_folder", type=Path, default=Path("chunks"))
    split.add_argument("-O", "--os", choices=("unix", "cross_platform"), default="unix")
    split.add_argument("--ensure-list", action="store_true")
    args = parser.parse_args()
    if args.command == "version":
        print("nfclaw-record-scatter-sha256:" + recipe_digest())
    elif args.command == "patch":
        orders = json.loads(base64.b64decode(args.mate_orders)) if args.mate_orders else None
        patch_task(args.kind, args.script, mate_orders=orders)
    else:
        scatter(args.fastq, args.num_splits, args.prefix, args.out_folder,
                extension=args.ext, suffix=args.suffix, ensure_list=args.ensure_list)


if __name__ == "__main__":
    main()
