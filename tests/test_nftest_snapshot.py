"""A run is checked against the release's own nf-test snapshot, as nf-core's CI checks it."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/check_nftest_snapshot.py"
spec = importlib.util.spec_from_file_location("check_nftest_snapshot", SCRIPT)
snapshot_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot_check)

READS = b"@r1\nACGT\n+\nIIII\n"
COUNTS = b"sample\treads\nA\t1\n"


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _run(tmp_path, reads=READS, counts=COUNTS):
    """An nf-core/demo-shaped run: published results, plus nfclaw's provenance bundle."""
    out = tmp_path / "run"
    (out / "fq" / "A").mkdir(parents=True)
    (out / "fq" / "A" / "A_R1.fastq.gz").write_bytes(gzip.compress(reads, mtime=0))
    (out / "multiqc").mkdir()
    (out / "multiqc" / "general_stats.txt").write_bytes(counts)
    (out / "multiqc" / "report.html").write_text("<html>dated report</html>")
    (out / "provenance").mkdir()
    (out / "provenance" / "general_stats.txt").write_text("not a published result")
    return out


def _snapshot(test="-profile test"):
    # nf-test hashes a .gz file's decompressed content and names each file by its basename.
    return {test: {"content": [
        {"FASTQC": {"fastqc": "0.12.1"}},
        ["fq", "fq/A", "fq/A/A_R1.fastq.gz", "multiqc", "multiqc/report.html"],
        [f"A_R1.fastq.gz:md5,{_md5(READS)}",
         f"general_stats.txt:md5,{_md5(COUNTS)}"],
    ], "meta": {"nf-test": "0.9.5", "nextflow": "26.04.3"}}}


def test_a_run_with_the_expected_results_matches_the_snapshot(tmp_path):
    result = snapshot_check.compare(_snapshot(), _run(tmp_path), "-profile test")
    assert result["identical"] == ["A_R1.fastq.gz", "general_stats.txt"]
    assert not (result["different"] or result["missing_files"] or result["missing_paths"])


@pytest.mark.parametrize("changed", [{"reads": b"@r1\nACGA\n+\nIIII\n"},
                                     {"counts": b"sample\treads\nA\t2\n"}])
def test_changed_results_differ_from_the_snapshot(tmp_path, changed):
    result = snapshot_check.compare(_snapshot(), _run(tmp_path, **changed))
    assert len(result["different"]) == 1 and not result["missing_files"]


def test_missing_outputs_are_reported_and_provenance_is_not_a_result(tmp_path):
    run = _run(tmp_path)
    (run / "multiqc" / "general_stats.txt").unlink()
    (run / "multiqc" / "report.html").unlink()
    result = snapshot_check.compare(_snapshot(), run)
    assert result["missing_files"] == ["general_stats.txt"]
    assert result["missing_paths"] == ["multiqc/report.html"]


def test_a_snapshot_with_several_tests_needs_the_test_named(tmp_path):
    snapshot = {**_snapshot("-profile test"), **_snapshot("-profile test_full")}
    run = _run(tmp_path)
    with pytest.raises(ValueError, match="name one with --test"):
        snapshot_check.compare(snapshot, run)
    with pytest.raises(ValueError, match="no test 'stub'"):
        snapshot_check.compare(snapshot, run, "stub")
    assert snapshot_check.compare(snapshot, run, "-profile test")["identical"]


def test_command_line_exit_status(tmp_path, capsys):
    snap = tmp_path / "default.nf.test.snap"
    snap.write_text(json.dumps(_snapshot()))
    run = _run(tmp_path)
    assert snapshot_check.main([str(snap), str(run), "--test", "-profile test"]) == 0
    assert "5 of 5 expected paths present; 2 of 2 checksums identical" in capsys.readouterr().out
    (run / "multiqc" / "general_stats.txt").write_text("changed")
    assert snapshot_check.main([str(snap), str(run)]) == 1
    assert "different: general_stats.txt" in capsys.readouterr().out
    assert snapshot_check.main([str(tmp_path / "absent.snap"), str(run)]) == 2


def test_nextflow_state_in_the_outdir_is_not_a_published_result(tmp_path):
    run = _run(tmp_path)
    (run / "multiqc" / "general_stats.txt").unlink()
    (run / ".nextflow" / "cache").mkdir(parents=True)
    (run / ".nextflow" / "cache" / "general_stats.txt").write_bytes(COUNTS)
    (run / ".nextflow.log.1").mkdir()
    (run / ".nextflow.log.1" / "general_stats.txt").write_bytes(COUNTS)
    assert snapshot_check.compare(_snapshot(), run)["missing_files"] == ["general_stats.txt"]


def test_large_results_are_hashed_in_chunks(tmp_path, monkeypatch):
    # Results were read (and decompressed) into memory whole; a .gz is hashed as a stream.
    monkeypatch.setattr(snapshot_check, "_CHUNK", 3)
    run = _run(tmp_path)
    reads = run / "fq" / "A" / "A_R1.fastq.gz"
    assert snapshot_check.digests(reads) == {_md5(reads.read_bytes()), _md5(READS)}
    not_gzip = run / "fake.gz"
    not_gzip.write_bytes(b"plain")
    assert snapshot_check.digests(not_gzip) == {_md5(b"plain")}
    # A gzip header over damaged data raised zlib.error, a traceback instead of a mismatch.
    packed = gzip.compress(READS * 50, mtime=0)
    corrupt = run / "corrupt.gz"
    corrupt.write_bytes(packed[:10] + b"\xff\xff\xff\xff" + packed[14:])
    assert snapshot_check.digests(corrupt) == {_md5(corrupt.read_bytes())}
    assert snapshot_check.compare(_snapshot(), run)["identical"] == ["A_R1.fastq.gz",
                                                                     "general_stats.txt"]


@pytest.mark.parametrize("snapshot", [[], {"-profile test": []}, {"-profile test": "x"}])
def test_a_malformed_snapshot_is_an_error_not_a_traceback(tmp_path, capsys, snapshot):
    snap = tmp_path / "bad.snap"
    snap.write_text(json.dumps(snapshot))
    assert snapshot_check.main([str(snap), str(_run(tmp_path))]) == 2
    assert capsys.readouterr().err.startswith("error: ")


def test_a_missing_run_directory_is_an_error(tmp_path):
    snap = tmp_path / "s.snap"
    snap.write_text(json.dumps(_snapshot()))
    assert snapshot_check.main([str(snap), str(tmp_path / "absent")]) == 2


def test_the_pinned_demo_snapshot_records_paths_and_checksums():
    snap = REPO / "pipelines/demo/upstream/tests/default.nf.test.snap"
    if not snap.is_file():
        pytest.skip("pipelines/demo/upstream is not initialised")
    paths, checksums = snapshot_check.expectations(json.loads(snap.read_text()), "-profile test")
    assert "cowpy/cowpy.txt" in paths and len(checksums) >= 7
    assert any(name.endswith(".fastq.gz") for name, _ in checksums)
