"""Preserve complete original reads and record exact runtime corrections."""
import gzip
import json
import os
import random
import re
import subprocess
import sys

import pytest

import fastqwiper_oracle as oracle
from runner import fastqrepair_compat as compat


def _decode(path):
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()


def _write(path, content):
    if path.name.endswith(".gz"):
        with gzip.open(path, "wb") as handle:
            handle.write(content)
    else:
        path.write_bytes(content)
    return path


@pytest.mark.parametrize("compressed", [False, True])
@pytest.mark.parametrize("count,splits", [(3, 2), (2, 4), (5, 3), (12, 5), (1001, 1001)])
def test_record_splitting_preserves_every_byte_and_all_frame_boundaries(tmp_path, compressed, count, splits):
    content = b"".join(f"@read{i}\nACGT\n+\nIIII\n".encode() for i in range(count))
    source = _write(tmp_path / ("reads.fastq.gz" if compressed else "reads.fastq"), content)
    files = compat.scatter(source, splits, "source", tmp_path / "chunks")
    # Clean reads are dealt out evenly, as before: every record boundary is a restart.
    assert len(files) == min(count, splits)
    assert [len(_decode(path).splitlines()) // 4 for path in files] == [
        count // len(files) + (i < count % len(files)) for i in range(len(files))]
    assert b"".join(_decode(path) for path in sorted(files)) == content
    for path in files:
        lines = _decode(path).splitlines()
        assert len(lines) % 4 == 0
        assert all(lines[i].startswith(b"@read") and lines[i + 2] == b"+" for i in range(0, len(lines), 4))


@pytest.mark.parametrize("content", [b"noise\n@r\nACGT\n+\nIIII\n", b"@r\nACGT\n+\nIII\n",
                                     b"@r\nACGT\n+\n", b"@r\nACGT\n+\nIIII",
                                     b"@a\nACGT\n+\n@@@@\n@b\nACGT\n+\nI@II\n"])
@pytest.mark.parametrize("splits", [1, 2, 4])
def test_input_without_a_restart_is_wiped_whole_beside_a_placeholder(tmp_path, content, splits):
    # The pinned subworkflow iterates the chunk list (one chunk is a Path, iterated by name
    # component) and fastqwiper divides by the line count (an empty chunk fails): such input
    # stays whole in the first chunk, and a zero-byte placeholder completes the list.
    source = _write(tmp_path / "damaged.fastq", content)
    files = compat.scatter(source, splits, "source", tmp_path / "chunks")
    assert [path.name for path in files] == ["source_000.fastq.gz", "source_001.fastq.gz"]
    assert _decode(files[0]) == content
    assert files[1].stat().st_size == 0


def test_empty_input_is_refused(tmp_path):
    with pytest.raises(ValueError, match="no FASTQ lines"):
        compat.scatter(_write(tmp_path / "empty.fastq", b""), 2, "source", tmp_path / "chunks")


def _wiped(paths, alphabet):
    """Wipe each chunk as the patched task does (a placeholder yields nothing) and gather."""
    reads, totals = [], dict.fromkeys(oracle.FIELDS, 0)
    for path in sorted(paths):
        if path.stat().st_size == 0:
            continue
        text, counts = oracle.wipe(path, alphabet)
        reads.append(text)
        for key, value in counts.items():
            totals[key] += value
    return "".join(reads), totals


DAMAGE = [
    b"@r1\nACGT\n+\nIIII\n@r2\nacgt\n+\n@III\n@r3\nACGT\n+\nIIII\n@r4\nACGT\n+\nIIII\n",
    b"@r1\nACGT\n+\nIIII\n\n\n@r2\nACG\n+\nIIII\n@r3\nAC\n@r4\nACGT\n+\nIIII\n@r5\nTT\n+\nII\n",
    b"@r1\nACGT\n+\nII\x01I\n@r2\nACGT\n+\nIIII\n@r3\nGG\n+\nII\n@r4\nCC\n+\nII\n@r5\nAA\n+\nII\n",
    b"@r1\rACGT\r+\rIIII\r@r2\r\nAC\r\n+\r\nII\r\n@r3\nGG\n+\nII\n@r4\x0bGG\n+\nII\n@r5\nGG\n+\nII\n",
    b"x@r1\nACGT\n+\nIIII\n\x02@r2\nACGT\n+\nIIII\n@r3\nACGT\n+r3\nIIII\n@r4\nNN\n+\nII\n@r5\nAC\n+\nII\n",
    "@r1\nACGT\n+\nIIII\n@r2\u2028x\nACGT\n+\nIIII\n@r3\nAC\n+\nII\n@r4\nAC\n+\nII\n".encode()
    + b"\xff\xfe@r5\nAC\n+\nII\n@r6\nAC\n+\nII\n@r7\nAC\n+\nII\n",
]


def _fuzz(seed, records=40):
    rng = random.Random(seed)
    lines = []
    for i in range(records):
        length = rng.randint(1, 8)
        seq = "".join(rng.choice("ACGTN") for _ in range(length))
        qual = "".join(rng.choice("#,:F@IJ") for _ in range(length))
        lines += [f"@read{i}", seq, "+", qual]
    for _ in range(rng.randint(0, 12)):
        index = rng.randrange(len(lines) + 1)
        mutation = rng.choice(("delete", "blank", "noise", "lower", "control", "at", "dup", "cr"))
        if mutation == "delete" and index < len(lines):
            del lines[index]
        elif mutation == "blank":
            lines.insert(index, rng.choice(("", " ", "\t")))
        elif mutation == "noise":
            lines.insert(index, rng.choice(("garbage", "+", "@", "ACGT", "@x@y", "IIII")))
        elif mutation == "lower" and index < len(lines):
            lines[index] = lines[index].lower()
        elif mutation == "control" and index < len(lines):
            lines[index] = lines[index][:1] + "\x03" + lines[index][1:]
        elif mutation == "at" and index < len(lines):
            lines[index] = "@" + lines[index]
        elif mutation == "dup" and index < len(lines):
            lines.insert(index, lines[index])
        elif mutation == "cr" and index < len(lines):
            lines[index] += "\r"
    return ("\n".join(lines) + rng.choice(("\n", ""))).encode()


@pytest.mark.parametrize("extension", ["fastq.gz", "fastq"])
@pytest.mark.parametrize("splits", [1, 2, 3, 7])
@pytest.mark.parametrize("case", range(len(DAMAGE) + 60))
def test_chunks_wipe_exactly_as_the_whole_file(tmp_path, extension, splits, case):
    """Gathered chunk wipes equal one whole-file wipe, reads and report, for every alphabet."""
    content = DAMAGE[case] if case < len(DAMAGE) else _fuzz(case)
    source = _write(tmp_path / f"reads.{extension}", content)
    files = compat.scatter(source, splits, "source", tmp_path / "chunks", extension=extension)
    assert len(files) >= 2
    assert b"".join(_decode(path) for path in files if path.stat().st_size) == content
    for alphabet in ("ACGTN", "ACGT", "acgtnACGTN", "ACGTN@"):
        assert _wiped(files, alphabet) == oracle.wipe(source, alphabet)


def test_restarts_are_used_wherever_they_exist(tmp_path):
    # Records whose quality holds "@" offer no restart before the next header; others do.
    content = (b"@a\nAC\n+\nI@\n@b\nAC\n+\nII\n@c\nAC\n+\n@I\n@d\nAC\n+\nII\n"
               b"@e\nAC\n+\nII\n@f\nAC\n+\nII\n")
    files = compat.scatter(_write(tmp_path / "reads.fastq", content), 10, "source", tmp_path / "chunks")
    assert [_decode(path).split(b"\n")[0] for path in files] == [b"@a", b"@c", b"@e", b"@f"]


def test_changed_source_cannot_claim_a_successful_split(tmp_path, monkeypatch):
    source = tmp_path / "reads.fastq"
    source.write_bytes(b"@A\nACGT\n+\nIIII\n")
    scan = compat._scan

    def changed_after_scan(path, breaks):
        result = scan(path, breaks)
        path.write_bytes(b"@A\nTGCA\n+\nHHHH\n")
        return result

    monkeypatch.setattr(compat, "_scan", changed_after_scan)
    with pytest.raises(ValueError, match="changed"):
        compat.scatter(source, 2, "source", tmp_path / "chunks")


def test_repair_quality_offset_and_log_redirection_reach_the_actual_command(tmp_path):
    fake = tmp_path / "repair.sh"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    fake.chmod(0o755)
    script = tmp_path / ".command.sh"
    script.write_text('#!/bin/bash -eu\nrepair.sh \\\n    threads=1\n    qin=64 \\\n    &> repair.log\n')
    compat.patch_task("repair", script)
    result = subprocess.run(["bash", str(script)], cwd=tmp_path,
                            env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "repair.log").read_text().splitlines() == ["threads=1", "qin=64"]


def test_unrecognized_task_is_refused_without_modifying_its_recipe(tmp_path):
    path = tmp_path / ".command.sh"
    path.write_text("echo unexpected upstream recipe\n")
    for operation in ("scatter", "wiper", "reportgather", "repair"):
        with pytest.raises(ValueError, match="unrecognized"):
            compat.patch_task(operation, path)
        assert path.read_text() == "echo unexpected upstream recipe\n"


def test_recorded_helper_executes_without_installed_runner_modules(tmp_path):
    source = tmp_path / "reads.fastq"
    source.write_bytes(b"@A\nACGT\n+\nIIII\n@B\nTGCA\n+\nHHHH\n@C\nAAAA\n+\n@@@@\n")
    script = tmp_path / ".command.sh"
    script.write_text('wipertools \\\n    fastqscatter \\\n    -f reads.fastq -n 2 -p source -o chunks\n'
                      'echo "wipertools fastqscatter: $(wipertools fastqscatter --version)"\n')
    compat.patch_task("scatter", script)
    result = subprocess.run(["bash", str(script)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert compat.recipe_digest() in result.stdout
    assert b"".join(_decode(path) for path in sorted((tmp_path / "chunks").iterdir())) == source.read_bytes()
    config = compat.write_config(tmp_path / "recorded.config").read_text()
    assert compat.recipe_digest()[:16] in config
    assert "import runner" not in config
    assert json.dumps(compat._command() + " patch repair .command.sh --mate-orders e30=") in config


WIPER_RECIPE = ('#!/usr/bin/env bash -C -e -u -o pipefail\nwipertools \\\n    fastqwiper \\\n'
                '    -i {chunk} \\\n    -o {chunk}_wiped.fastq.gz \\\n    -r {chunk}_wiped.report \\\n'
                '    --alphabet ACGTN\n\ncat <<-END_VERSIONS > versions.yml\n"WIPER":\n'
                '    wipertools fastqwiper: $(wipertools fastqwiper --version)\nEND_VERSIONS\n')


def _fake_wipertools(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "wipertools"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > wipertools.args\n'
                    '[ "$2" = --version ] && echo 1.1.5\nexit 0\n')
    fake.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def test_placeholder_chunk_yields_an_empty_output_and_zero_report(tmp_path):
    env = _fake_wipertools(tmp_path)
    (tmp_path / "source_001.fastq.gz").write_bytes(b"")
    script = tmp_path / ".command.sh"
    script.write_text(WIPER_RECIPE.format(chunk="source_001.fastq.gz"))
    compat.patch_task("wiper", script)
    result = subprocess.run(["bash", str(script)], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert gzip.decompress((tmp_path / "source_001.fastq.gz_wiped.fastq.gz").read_bytes()) == b""
    report = (tmp_path / "source_001.fastq.gz_wiped.report").read_text()
    assert report == compat._zero_report()
    assert compat._parse_report(tmp_path / "source_001.fastq.gz_wiped.report") == dict.fromkeys(
        (*compat._FIELDS, "fixed"), 0)
    # The real tool never ran for the placeholder; its version is still recorded.
    assert (tmp_path / "wipertools.args").read_text() == "fastqwiper\n--version\n"


def test_task_corrections_keep_non_ascii_names_under_a_strict_c_locale(tmp_path):
    # Sample and file names may hold any Unicode letter, and a task container can run Python under
    # a bare C locale (no UTF-8 coercion), where the default text encoding is ASCII.
    script = tmp_path / ".command.sh"
    script.write_text(WIPER_RECIPE.format(chunk="muestra_ñu_001.fastq.gz"), encoding="utf-8")
    env = {"PATH": os.environ["PATH"], "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    result = subprocess.run([sys.executable, compat.__file__, "patch", "wiper", str(script)],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    patched = script.read_text(encoding="utf-8")
    assert "muestra_ñu_001.fastq.gz" in patched and " wipe \\\n" in patched


def test_placeholder_report_does_not_claim_defined_percentages_with_zero_denominator(tmp_path):
    text = compat._zero_report()
    assert "(not applicable)" in text and "%" not in text
    path = tmp_path / "zero.report"
    path.write_text(text)
    assert not any(compat._parse_report(path).values())
    path.write_text(text.replace("Total lines: 0", "Total lines: 4"))
    with pytest.raises(ValueError, match="report|undefined"):
        compat._parse_report(path)


def test_real_chunk_reaches_fastqwiper_with_every_argument(tmp_path):
    env = _fake_wipertools(tmp_path)
    _write(tmp_path / "source_000.fastq.gz", b"@r\nACGT\n+\nIIII\n")
    script = tmp_path / ".command.sh"
    script.write_text(WIPER_RECIPE.format(chunk="source_000.fastq.gz").replace(
        "versions.yml", "versions.txt"))
    compat.patch_task("wiper", script)
    (tmp_path / "wipertools.args").unlink(missing_ok=True)
    result = subprocess.run(["bash", "-c", script.read_text().split("\n\ncat")[0]], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "wipertools.args").read_text().splitlines() == [
        "fastqwiper", "-i", "source_000.fastq.gz", "-o", "source_000.fastq.gz_wiped.fastq.gz",
        "-r", "source_000.fastq.gz_wiped.report", "--alphabet", "ACGTN"]


def _report(total, fixed, blank=0):
    return (f"FASTQWIPER REPORT:\n\nTotal lines: {total}\nWell-formed lines: 8 (1.0%)\nClean reads: 2\n"
            f"Bad headers or misplaced lines: 40 (10.0%) of which {fixed} fixed\nBAD SEQ lines: 5 (1.25%)\n"
            "BAD '+' lines: 3 (0.75%)\nBAD QUAL lines: 0 (0.0%)\n"
            f"Reads discarded because len(SEQ) neq len(QUAL): 2\nBlank lines: {blank} (0.25%)\n")


def test_reports_are_gathered_exactly(tmp_path):
    # wipertools reportgather 1.1.5 matched `.+(\d+).+` and kept "2" of "12 fixed".
    (tmp_path / "a.report").write_text(_report(400, 12, blank=1))
    (tmp_path / "b.report").write_text(_report(400, 12))
    (tmp_path / "c.report").write_text(compat._zero_report())
    compat.gather_reports([tmp_path / "a.report", tmp_path / "b.report", tmp_path / "c.report"],
                          tmp_path / "all.report")
    assert (tmp_path / "all.report").read_text() == (
        "FASTQWIPER REPORT:\n\nTotal lines: 800\nWell-formed lines: 16 (2.0%)\nClean reads: 4\n"
        "Bad headers or misplaced lines: 80 (10.0%) of which 24 fixed\nBAD SEQ lines: 10 (1.25%)\n"
        "BAD '+' lines: 6 (0.75%)\nBAD QUAL lines: 0 (0.0%)\n"
        "Reads discarded because len(SEQ) neq len(QUAL): 4\nBlank lines: 1 (0.12%)\n")


@pytest.mark.parametrize("damage", [lambda r: r.replace("Clean reads: 2\n", ""),
                                    lambda r: r.replace("of which 12 fixed", "of which some fixed"),
                                    lambda r: r + "Clean reads: 2\n"])
def test_unrecognized_report_is_refused(tmp_path, damage):
    (tmp_path / "a.report").write_text(damage(_report(400, 12)))
    with pytest.raises(ValueError, match="report"):
        compat.gather_reports([tmp_path / "a.report"], tmp_path / "all.report")
    assert not (tmp_path / "all.report").exists()


def test_report_gathering_runs_from_the_recorded_recipe(tmp_path):
    (tmp_path / "a.report").write_text(_report(400, 12))
    (tmp_path / "b.report").write_text(_report(400, 12))
    script = tmp_path / ".command.sh"
    script.write_text('wipertools \\\n    reportgather \\\n    -r a.report b.report \\\n'
                      '    -f sample.report \\\n\n'
                      'echo "wipertools reportgather: $(wipertools reportgather --version)"\n')
    compat.patch_task("reportgather", script)
    result = subprocess.run(["bash", str(script)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "of which 24 fixed" in (tmp_path / "sample.report").read_text()
    assert f"nfclaw_record_reportgather: nfclaw-fastqrepair-compat-sha256:{compat.recipe_digest()}" in result.stdout


def test_unsuffixed_mates_follow_samplesheet_order_in_the_actual_repair_command(tmp_path):
    script = tmp_path / ".command.sh"
    script.write_text('repair.sh \\\n    in=right_gather__nfclaw_0123456789abcdef.fastq.gz in2=left_gather__nfclaw_0123456789abcdef.fastq.gz \\\n'
                      '    out=S__nfclaw_0123456789abcdef_1_repaired.fastq.gz out2=S__nfclaw_0123456789abcdef_2_repaired.fastq.gz \\\n'
                      '    threads=1\n    qin=64 \\\n    &> repair.log\n')
    compat.patch_task("repair", script, mate_orders={"S": ["left", "right"]})
    text = script.read_text()
    assert "in=left_gather" in text and "in2=right_gather" in text
    assert "threads=1 \\\n" in text


def test_mate_map_uses_declared_streams_and_refuses_collapsed_raw_names(tmp_path):
    sheet = tmp_path / "samples.csv"
    sheet.write_text("sample,fastq_1,fastq_2\nS,/data/left.fastq,/data/right.fastq\n")
    assert compat.paired_input_roles(sheet) == {"S": ["left", "right"]}
    sheet.write_text("sample,fastq_1,fastq_2\nS,/data/left.fastq.gz,/data/right.fastq.gz\n")
    assert compat.paired_input_roles(sheet) == {"S": ["S_recovered_1", "S_recovered_2"]}
    sheet.write_text("sample,fastq_1,fastq_2\nS,/left/reads.fastq,/right/reads.fastq\n")
    with pytest.raises(ValueError, match="same|identit"):
        compat.paired_input_roles(sheet)


def test_raw_mate_identifiers_cannot_collapse_across_fastq_extensions(tmp_path):
    sheet = tmp_path / "samples.csv"
    sheet.write_text("sample,fastq_1,fastq_2\nS,/data/reads.fastq,/data/reads.fq\n")
    with pytest.raises(ValueError, match="identit|same"):
        compat.paired_input_roles(sheet)


def test_multiple_rows_cannot_overwrite_a_single_end_sample_publication(tmp_path):
    sheet = tmp_path / "samples.csv"
    sheet.write_text("sample,fastq_1,fastq_2\nS,/data/left.fastq,\nS,/data/right.fastq,\n")
    with pytest.raises(ValueError, match="more than once|identit"):
        compat.paired_input_roles(sheet)


@pytest.mark.parametrize("sample", ["WIPE_HOOK", "WIPER_HOOK", "REPORTGATHER_HOOK", "MATE_ORDERS",
                                    "REPAIR_HOOK", "SCATTER_HOOK", "RECIPE"])
def test_configuration_preserves_literal_template_words_in_scientific_identifiers(tmp_path, sample):
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,fastq_1,fastq_2\n{sample},/data/left.fastq,/data/right.fastq\n")
    config = compat.write_config(tmp_path / "recorded.config", input_path=sheet).read_text()
    # The JSON literals are consumed by Groovy's JSON parser, and must still name
    # the supplied scientific samples rather than expanded template instructions.
    blocks = re.findall(r"parseText\(\[(.*?)\]\.join\(''\)\)", config)
    assert blocks
    for block in blocks:
        roles = json.loads("".join(json.loads("[" + block + "]")))
        assert roles == {sample: ["left", "right"]}


def test_profile_fallback_cannot_infer_all_mates_from_the_first_header(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    names = ["left.fastq.gz", "right.fastq.gz"]
    for name, mate in zip(names, (1, 2), strict=True):
        with gzip.open(name, "wt") as stream:
            stream.write(f"@first/{mate}\nACGT\n+\nIIII\n@second\nTGCA\n+\nHHHH\n")
    script = 'in=left.fastq.gz in2=right.fastq.gz out=S__nfclaw_0123456789abcdef_1_repaired.fastq.gz'
    with pytest.raises(ValueError, match="mate order|explicit local"):
        compat._ordered_inputs(script, {})


@pytest.mark.parametrize("problem", [None, "opposite", "conflicting", "truncated"])
def test_profile_fallback_requires_consistent_labels_on_every_complete_record(tmp_path, monkeypatch, problem):
    monkeypatch.chdir(tmp_path)
    for name, role in (("left.fastq", 2), ("right.fastq", 1)):
        label = 3 - role if problem == "opposite" else role
        header = f"@second/{label}" + (f" {3 - label}:N:0:1" if problem == "conflicting" else "")
        content = f"@first/{role}\nACGT\n+\nIIII\n{header}\nTGCA\n+\nHHHH\n"
        (tmp_path / name).write_text(content[:-4] if problem == "truncated" else content)
    script = 'in=left.fastq in2=right.fastq out=S__nfclaw_0123456789abcdef_1_repaired.fastq.gz'
    if problem is None:
        corrected = compat._ordered_inputs(script, {})
        assert "in=right.fastq in2=left.fastq" in corrected
    else:
        with pytest.raises(ValueError, match="mate order|explicit local"):
            compat._ordered_inputs(script, {})
