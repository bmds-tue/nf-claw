"""Verification must measure replay files, not stale or ambiguous checksum metadata."""
import hashlib
import json

import pytest

from runner import outputs, verify
from runner.errors import NfclawError


def _run(root, name, files):
    out = root / name
    (out / "provenance").mkdir(parents=True)
    lines = []
    for path, content in files.items():
        result = out / path
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_bytes(content)
        lines.append(f"{hashlib.sha256(content).hexdigest()}  {path}\n")
    (out / "provenance" / "outputs.sha256").write_text("".join(lines))
    (out / "provenance/outputs.inventory.json").write_text(json.dumps(
        {"version": 1, "entries": outputs.snapshot(out)[1]}))
    return out


def test_replay_changes_are_measured_even_when_its_bundle_is_stale(tmp_path):
    original = _run(tmp_path, "original", {"counts.tsv": b"gene\t10\n"})
    replay = _run(tmp_path, "replay", {"counts.tsv": b"gene\t10\n"})
    (replay / "counts.tsv").write_bytes(b"gene\t99\n")
    comparison = verify.compare(original, replay)
    assert comparison.changed == ["counts.tsv"]
    assert comparison.identical == []


def test_replay_deletions_are_measured_even_when_its_bundle_is_stale(tmp_path):
    original = _run(tmp_path, "original", {"calls.vcf": b"original variants\n"})
    replay = _run(tmp_path, "replay", {"calls.vcf": b"original variants\n"})
    (replay / "calls.vcf").unlink()
    assert verify.compare(original, replay).missing == ["calls.vcf"]


def test_replay_additions_are_measured_even_when_its_bundle_is_stale(tmp_path):
    original = _run(tmp_path, "original", {"result.txt": b"data"})
    replay = _run(tmp_path, "replay", {"result.txt": b"data"})
    (replay / "extra.txt").write_bytes(b"unexpected")
    assert verify.compare(original, replay).extra == ["extra.txt"]


@pytest.mark.parametrize("content", [
    "not a checksum manifest\n",
    "abc  counts.tsv\n",
    "g" * 64 + "  counts.tsv\n",
    "0" * 64 + "  ../outside.tsv\n",
    "0" * 64 + "  /outside.tsv\n",
    "0" * 64 + "  nested//counts.tsv\n",
    "0" * 64 + "  counts.tsv\n" + "1" * 64 + "  counts.tsv\n",
])
def test_malformed_original_checksums_fail_explicitly(tmp_path, content):
    original = _run(tmp_path, "original", {})
    replay = _run(tmp_path, "replay", {})
    (original / "provenance" / "outputs.sha256").write_text(content)
    with pytest.raises(NfclawError, match="checksum"):
        verify.compare(original, replay)


def test_inventory_preserves_multiple_metadata_files(tmp_path):
    first = "pipeline_info/params_2026-10-08_10-00-00.json"
    second = "pipeline_info/params_2026-10-08_11-00-00.json"
    original = _run(tmp_path, "original", {first: b"attempt 1", second: b"attempt 2"})
    replay = _run(tmp_path, "replay", {second: b"attempt 2"})
    comparison = verify.compare(original, replay)
    assert comparison.identical == [second]
    assert comparison.missing == [first]
    assert not comparison.structurally_equal


def test_changed_scientific_data_is_not_byte_identical(tmp_path):
    original = _run(tmp_path, "original", {"counts.tsv": b"gene\t10\n"})
    replay = _run(tmp_path, "replay", {"counts.tsv": b"gene\t99\n"})
    comparison = verify.compare(original, replay)
    assert comparison.structurally_equal
    assert not comparison.byte_identical


def test_report_does_not_assume_all_changes_are_timestamps(tmp_path):
    original = _run(tmp_path, "original", {"counts.tsv": b"gene\t10\n"})
    replay = _run(tmp_path, "replay", {"counts.tsv": b"gene\t99\n"})
    report = verify.report(verify.compare(original, replay))
    assert "scientific" in report.lower()
    assert "Differing bytes are expected" not in report


@pytest.mark.parametrize("prefix", ["pipeline_info/params_", "pipeline_info/sample_",
                                    "pipeline_info/nested/sample_"])
def test_dated_path_changes_cannot_claim_identical_output_inventory(tmp_path, prefix):
    first = prefix + "2026-10-08_10-00-00.json"
    second = prefix + "2026-10-09_10-00-00.json"
    original = _run(tmp_path, "original", {first: b"same bytes"})
    replay = _run(tmp_path, "replay", {second: b"same bytes"})
    comparison = verify.compare(original, replay)
    assert comparison.missing == [first]
    assert comparison.extra == [second]
    assert not comparison.byte_identical
    assert "same set of files as the original" not in verify.report(comparison)


@pytest.mark.parametrize("strict", [False, True])
def test_cli_refuses_dated_inventory_changes_even_with_identical_bytes(tmp_path, capsys, strict):
    from runner import cli
    original = _run(tmp_path, "original", {
        "pipeline_info/params_2026-10-08_10-00-00.json": b"unchanged"})
    replay = _run(tmp_path, "replay", {
        "pipeline_info/params_2026-10-09_10-00-00.json": b"unchanged"})
    args = ["verify", str(replay), "--against", str(original)] + (["--strict"] if strict else [])
    assert cli.main(args) == 1
    output = capsys.readouterr().out
    assert "missing" in output and "extra" in output
