"""The damaged-read control reaches every chunking path and detects any departure from one wipe."""
import gzip
import json

import pytest

import fastqwiper_oracle as oracle
from runner import fastqrepair_compat as compat
from scripts.check_fastqrepair_wipe import COMMIT, SAMPLES, check_run, write_fixture


def _scatter(tmp_path, sample):
    source = tmp_path / f"{sample}.fastq"
    source.write_bytes(SAMPLES[sample])
    return compat.scatter(source, 3, sample, tmp_path / f"{sample}-chunks")


@pytest.mark.parametrize("sample,real,placeholders", [
    ("damaged", 3, 0), ("single_read", 1, 1), ("at_quality", 1, 1), ("fixed_headers", 3, 0)])
def test_each_control_reaches_its_chunking_path(tmp_path, sample, real, placeholders):
    files = _scatter(tmp_path, sample)
    sizes = [path.stat().st_size for path in files]
    assert (sum(1 for size in sizes if size), sizes.count(0)) == (real, placeholders)


def test_repaired_headers_exceed_one_digit_in_every_chunk(tmp_path):
    for path in _scatter(tmp_path, "fixed_headers"):
        assert oracle.wipe(path)[1]["fixed"] == 22


@pytest.mark.parametrize("sample", sorted(SAMPLES))
def test_controls_gather_to_one_whole_file_wipe(tmp_path, sample):
    whole = tmp_path / "whole.fastq.gz"
    with gzip.open(whole, "wb") as handle:
        handle.write(SAMPLES[sample])
    reads, totals = [], dict.fromkeys(oracle.FIELDS, 0)
    for path in _scatter(tmp_path, sample):
        if path.stat().st_size:
            text, counts = oracle.wipe(path)
            reads.append(text)
            totals = {key: totals[key] + counts[key] for key in totals}
    assert ("".join(reads), totals) == oracle.wipe(whole)


def _run(tmp_path, reads, report):
    run = tmp_path / "run"
    (run / "repaired").mkdir(parents=True)
    (run / "provenance").mkdir()
    (run / "provenance/run_manifest.json").write_text(json.dumps(
        {"pipeline": "fastqrepair", "commit": COMMIT, "outcome": "success"}))
    for sample in SAMPLES:
        with gzip.open(run / "repaired" / f"{sample}.fastq.gz", "wb") as handle:
            handle.write(reads(sample))
        (run / "repaired" / f"{sample}.report").write_text(report(sample))
    return run


def _wipe(content):
    return b"@r\nACGT\n+\nIIII\n" * (len(content) % 5), f"Total lines: {len(content)}\n"


def test_check_accepts_exactly_the_whole_file_wipe(tmp_path):
    run = _run(tmp_path, lambda s: _wipe(SAMPLES[s])[0], lambda s: _wipe(SAMPLES[s])[1])
    assert check_run(run, wipe=_wipe) == {s: len(SAMPLES[s]) % 5 for s in SAMPLES}


@pytest.mark.parametrize("damage", ["reads", "report"])
def test_check_detects_a_changed_read_or_report(tmp_path, damage):
    run = _run(tmp_path,
               lambda s: _wipe(SAMPLES[s])[0] + (b"@x\nA\n+\nI\n" if damage == "reads" else b""),
               lambda s: _wipe(SAMPLES[s])[1] + ("Blank lines: 1\n" if damage == "report" else ""))
    with pytest.raises(ValueError, match=damage):
        check_run(run, wipe=_wipe)


def test_gzip_fixture_holds_the_exact_control_bytes(tmp_path):
    write_fixture(tmp_path / "fixture", compressed=True)
    for sample, content in SAMPLES.items():
        written = tmp_path / "fixture" / f"{sample}.fastq.gz"
        assert gzip.decompress(written.read_bytes()) == content
    assert (tmp_path / "fixture/samples.csv").read_text().splitlines()[0] == "sample,fastq_1"
