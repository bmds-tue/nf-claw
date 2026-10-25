"""A changed generated selection must not mix fresh and historical publications."""
from pathlib import Path

import pytest

import sheetgen_schemas as S
from runner import orchestration, provenance
from runner.submodule import SubmoduleStatus
from test_sheetgen import fq
from test_sheetgen_run import run  # noqa: F401


@pytest.mark.parametrize("change", ["replace", "add", "remove", "alias"])
def test_resume_compares_complete_file_membership_and_identity(tmp_path, change):
    first, second = tmp_path / "A.fastq", tmp_path / "B.fastq"
    first.write_bytes(b"same data")
    second.write_bytes(b"same data")
    alias = tmp_path / "selected.fastq"
    alias.symlink_to(first)
    before = [alias] if change == "alias" else [first, second] if change == "remove" else [first]
    out = tmp_path / "results"
    provenance.write(outdir=out, pipeline="fixture", command_str="echo CHECK",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=before)
    if change == "alias":
        alias.unlink()
        alias.symlink_to(second)
    after = {"alias": [alias], "replace": [second], "add": [first, second]}.get(change, [first])
    hashes, namespace = provenance.snapshot_inputs(after)
    warning = orchestration._input_resume_warning(out, namespace, hashes)
    assert warning and "fresh Nextflow cache session" in warning


@pytest.mark.parametrize("change", ["add", "remove", "replace"])
def test_generated_selection_change_archives_prior_results_before_resume(tmp_path, run, change):  # noqa: F811
    data = tmp_path / "data"
    first = fq(data / "A.fastq.gz", "SRR390728.1")
    second = fq(data / "B.fastq.gz", "SRR390728.2") if change == "remove" else None
    run(S.ATACSEQ, str(data), sheet_set={"replicate": "1"})
    old = tmp_path / "results/A.txt"
    old.write_text("previous sample A result\n")
    if change in ("replace", "remove"):
        (second if change == "remove" else first).unlink()
    if change in ("add", "replace"):
        fq(data / "B.fastq.gz", "SRR390728.2")
    resumed = run(S.ATACSEQ, str(data), sheet_set={"replicate": "1"}, resume=True)
    assert "-resume" not in resumed.launched[-1]
    assert not old.exists(), "fresh output must not retain an earlier sample's publication"
    archives = list(tmp_path.glob("results.previous-*"))
    assert len(archives) == 1
    assert (archives[0] / "A.txt").read_text() == "previous sample A result\n"
    assert Path(resumed.generated_samplesheet).exists()


def test_generated_sample_annotations_change_the_analysis_identity(tmp_path, run):  # noqa: F811
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    run(S.RNASEQ, str(data), sheet_set={"strandedness": "forward"})
    (tmp_path / "results/first.txt").write_text("old annotations\n")
    resumed = run(S.RNASEQ, str(data), sheet_set={"strandedness": "reverse"}, resume=True)
    assert "-resume" not in resumed.launched[-1]
    assert not (tmp_path / "results/first.txt").exists()
    archive, = tmp_path.glob("results.previous-*")
    assert "forward" in (archive / "provenance/samplesheet.csv").read_text()
    assert "reverse" in Path(resumed.generated_samplesheet).read_text()
