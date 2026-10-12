"""Preserve complete original reads and record exact runtime corrections."""
import gzip
import subprocess

import pytest

from runner import fastqrepair_compat as compat


def _decode(path):
    return gzip.open(path, "rb").read() if path.suffix == ".gz" else path.read_bytes()


@pytest.mark.parametrize("compressed", [False, True])
@pytest.mark.parametrize("count,splits", [(3, 2), (1, 4), (5, 3), (12, 5), (1001, 1001)])
def test_record_splitting_preserves_every_byte_and_all_frame_boundaries(tmp_path, compressed, count, splits):
    content = b"".join(f"@read{i}\nACGT\n+\n@@@@\n".encode() for i in range(count))
    source = tmp_path / ("reads.fastq.gz" if compressed else "reads.fastq")
    if compressed:
        with gzip.open(source, "wb") as handle:
            handle.write(content)
    else:
        source.write_bytes(content)
    files = compat.scatter(source, splits, "source", tmp_path / "chunks")
    assert len(files) == min(count, splits)
    assert b"".join(_decode(path) for path in sorted(files)) == content
    for path in files:
        lines = _decode(path).splitlines()
        assert len(lines) % 4 == 0
        assert all(lines[i].startswith(b"@read") and lines[i + 2] == b"+" for i in range(0, len(lines), 4))


@pytest.mark.parametrize("content", [b"noise\n@r\nACGT\n+\nIIII\n", b"@r\nACGT\n+\nIII\n",
                                     b"@r\nACGT\n+\n", b"", b"@r\nACGT\n+\nIIII"])
def test_ambiguous_or_incomplete_input_is_not_discarded_by_splitting(tmp_path, content):
    source = tmp_path / "damaged.fastq"
    source.write_bytes(content)
    files = compat.scatter(source, 4, "source", tmp_path / "chunks")
    assert b"".join(_decode(path) for path in files) == content
    assert len(files) == 1


def test_changed_source_cannot_claim_a_successful_split(tmp_path, monkeypatch):
    source = tmp_path / "reads.fastq"
    source.write_bytes(b"@A\nACGT\n+\nIIII\n")
    scan = compat._scan

    def changed_after_scan(path):
        result = scan(path)
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
    import os
    result = subprocess.run(["bash", str(script)], cwd=tmp_path,
                            env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "repair.log").read_text().splitlines() == ["threads=1", "qin=64"]


def test_unrecognized_task_is_refused_without_modifying_its_recipe(tmp_path):
    path = tmp_path / ".command.sh"
    path.write_text("echo unexpected upstream recipe\n")
    for operation in ("scatter", "repair"):
        with pytest.raises(ValueError, match="unrecognized"):
            compat.patch_task(operation, path)
        assert path.read_text() == "echo unexpected upstream recipe\n"


def test_recorded_helper_executes_without_installed_runner_modules(tmp_path):
    import json
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


def test_runtime_single_chunk_preserves_one_read_and_has_list_cardinality(tmp_path):
    source = tmp_path / "reads.fastq"
    content = b"@one\nACGT\n+\nIIII\n"
    source.write_bytes(content)
    chunks = compat.scatter(source, 1, "source", tmp_path / "chunks", ensure_list=True)
    assert len(chunks) == 2
    assert [_decode(path) for path in chunks] == [content, b""]


def test_empty_compatibility_chunk_has_zero_bytes_and_truthful_undefined_rates(tmp_path):
    source = tmp_path / "empty.fastq.gz"
    with gzip.open(source, "wb"):
        pass
    out, report = tmp_path / "wiped.fastq.gz", tmp_path / "empty.report"
    compat.wiper(["-i", str(source), "-o", str(out), "-r", str(report)])
    assert _decode(out) == b""
    assert "Total lines: 0\n" in report.read_text()
    assert "Clean reads: 0\n" in report.read_text()
    assert "(not applicable)" in report.read_text()


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


@pytest.mark.parametrize("sample", ["WIPE_HOOK", "MATE_ORDERS", "REPAIR_HOOK", "SCATTER_HOOK", "RECIPE"])
def test_configuration_preserves_literal_template_words_in_scientific_identifiers(tmp_path, sample):
    import json
    import re
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
    for name, mate in zip(names, (1, 2)):
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
