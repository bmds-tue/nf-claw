import hashlib
import json

import pytest

from runner import outputs, verify
from runner.errors import NfclawError


def _bundle(root, name, entries):
    """A real result directory and its recorded {path: checksum} bundle."""
    out = root / name
    (out / "provenance").mkdir(parents=True)
    lines = []
    for path, content in entries.items():
        result = out / path
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text(content)
        lines.append(f"{hashlib.sha256(content.encode()).hexdigest()}  {path}\n")
    (out / "provenance" / "outputs.sha256").write_text("".join(lines))
    (out / "provenance/outputs.inventory.json").write_text(json.dumps(
        {"version": 1, "entries": outputs.snapshot(out)[1]}))
    return out


def test_a_faithful_replay_is_structurally_equal(tmp_path):
    orig = _bundle(tmp_path, "orig", {"a.txt": "aaa", "b.bam": "bbb"})
    replay = _bundle(tmp_path, "replay", {"a.txt": "aaa", "b.bam": "bbb"})
    cmp = verify.compare(orig, replay)
    assert cmp.structurally_equal
    assert cmp.identical == ["a.txt", "b.bam"] and not cmp.changed


def test_a_changed_file_is_counted_once_not_as_a_missing_plus_an_extra(tmp_path):
    # The trap this command exists to avoid. Diffing the raw `hash  path` lines makes one file whose
    # content changed look like a file that vanished AND a file that appeared, so a run where every
    # report merely carries a new timestamp reads as hundreds of missing and extra files.
    orig = _bundle(tmp_path, "orig", {"report.html": "aaa", "data.txt": "ccc"})
    replay = _bundle(tmp_path, "replay", {"report.html": "zzz", "data.txt": "ccc"})
    cmp = verify.compare(orig, replay)
    assert cmp.changed == ["report.html"]
    assert cmp.missing == [] and cmp.extra == []
    assert cmp.identical == ["data.txt"]
    assert cmp.structurally_equal          # same files produced — only their bytes differ


def test_a_file_the_replay_never_made_is_a_real_failure(tmp_path):
    orig = _bundle(tmp_path, "orig", {"a.txt": "aaa", "gone.vcf": "bbb"})
    replay = _bundle(tmp_path, "replay", {"a.txt": "aaa", "new.vcf": "ccc"})
    cmp = verify.compare(orig, replay)
    assert cmp.missing == ["gone.vcf"] and cmp.extra == ["new.vcf"]
    assert not cmp.structurally_equal      # the replay did different work


def test_report_explains_why_bytes_differ_but_flags_a_structural_difference(tmp_path):
    orig = _bundle(tmp_path, "orig", {"report.html": "aaa"})
    replay = _bundle(tmp_path, "replay", {"report.html": "zzz"})
    text = verify.report(verify.compare(orig, replay))
    assert "changed   : 1" in text
    assert "same set of files" in text and "scientific results" in text

    orig2 = _bundle(tmp_path, "orig2", {"a.txt": "aaa"})
    replay2 = _bundle(tmp_path, "replay2", {})
    text2 = verify.report(verify.compare(orig2, replay2))
    assert "did NOT produce the same set of files" in text2


def test_the_replay_side_needs_no_bundle_of_its_own(tmp_path):
    # `provenance/commands.sh` replays the recorded nextflow command directly, so the replayed run
    # has results but NO provenance bundle. Requiring one would make this command unusable for the
    # one comparison it exists for, so a bundle-less directory is hashed on the spot.
    orig = _bundle(tmp_path, "orig", {})
    (orig / "results.txt").write_text("same bytes")
    (orig / "provenance" / "outputs.sha256").write_text(
        __import__("hashlib").sha256(b"same bytes").hexdigest() + "  results.txt\n")
    (orig / "provenance/outputs.inventory.json").write_text(json.dumps(
        {"version": 1, "entries": outputs.snapshot(orig)[1]}))
    replay = tmp_path / "replay"                       # a plain results directory
    replay.mkdir()
    (replay / "results.txt").write_text("same bytes")
    cmp = verify.compare(orig, replay)
    assert cmp.identical == ["results.txt"] and cmp.structurally_equal


def test_nextflow_state_is_not_counted_as_an_output(tmp_path):
    # .nextflow/ and .nextflow.log describe the run; they are not its results, and no replay would
    # reproduce them. Counting them would report a phantom "extra" file on every comparison.
    orig = _bundle(tmp_path, "orig", {"a.txt": "aaa"})
    replay = tmp_path / "replay"
    (replay / ".nextflow").mkdir(parents=True)
    (replay / ".nextflow" / "history").write_text("h")
    (replay / ".nextflow.log").write_text("log")
    (replay / "a.txt").write_text("aaa")
    cmp = verify.compare(orig, replay)
    assert cmp.extra == [] and cmp.structurally_equal


def test_a_path_that_is_not_a_run_directory_is_named_clearly(tmp_path):
    orig = _bundle(tmp_path, "orig", {"a.txt": "aaa"})
    with pytest.raises(NfclawError, match="not a run directory"):
        verify.compare(orig, tmp_path / "does-not-exist")


def test_unpinnable_parameter_report_names_are_reported_for_explicit_classification(tmp_path):
    # Independent clock-based filenames change the actual inventory. Their metadata role
    # does not justify claiming identical paths or suppressing a structural difference.
    orig = _bundle(tmp_path, "orig", {
        "pipeline_info/params_2026-07-14_14-13-15.json": "aaa",
        "fastqc/x.html": "ccc"})
    replay = _bundle(tmp_path, "replay", {
        "pipeline_info/params_2026-07-14_15-14-07.json": "bbb",
        "fastqc/x.html": "ccc"})
    cmp = verify.compare(orig, replay)
    assert cmp.missing == ["pipeline_info/params_2026-07-14_14-13-15.json"]
    assert cmp.extra == ["pipeline_info/params_2026-07-14_15-14-07.json"]
    assert cmp.changed == [] and cmp.identical == ["fastqc/x.html"]
    assert not cmp.structurally_equal


def test_dated_scientific_results_preserve_their_exact_paths(tmp_path):
    # A real result that happens to carry a date in its name must never be folded together with a
    # differently-dated one — that would hide a genuinely missing output.
    orig = _bundle(tmp_path, "orig", {"results/sample_2026-07-14_14-13-15.vcf": "aaa"})
    replay = _bundle(tmp_path, "replay", {"results/sample_2026-07-14_15-14-07.vcf": "aaa"})
    cmp = verify.compare(orig, replay)
    assert cmp.missing == ["results/sample_2026-07-14_14-13-15.vcf"]
    assert cmp.extra == ["results/sample_2026-07-14_15-14-07.vcf"]
    assert not cmp.structurally_equal


def test_unreadable_run_is_a_clean_error(tmp_path, monkeypatch):
    # verify hashes a replay directory it did not write; one unreadable file raised a raw OSError.
    import pytest
    from runner.errors import ErrorCode, NfclawError
    orig, replay = tmp_path / "orig", tmp_path / "replay"
    (orig / "provenance").mkdir(parents=True)
    (orig / "provenance" / "outputs.sha256").write_text(
        hashlib.sha256(b"a").hexdigest() + "  a.txt\n")
    replay.mkdir()
    (replay / "a.txt").write_text("a")

    def deny(path):
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(verify.provenance, "_sha256", deny)
    with pytest.raises(NfclawError) as exc:
        verify.compare(orig, replay)
    assert exc.value.code == ErrorCode.ENVIRONMENT
    assert "Permission denied" in str(exc.value) and "a.txt" in str(exc.value)
