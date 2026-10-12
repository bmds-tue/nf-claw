"""Samplesheet generation as a stage of `nfclaw run`: staging, command, provenance and replay."""
import json
import re
import shlex
from pathlib import Path

import pytest

import sheetgen_schemas as S
from runner import orchestration, provenance, replay_guard
from runner.errors import ErrorCode, NfclawError
from test_sheetgen import fq, pair


@pytest.fixture
def run(tmp_path, monkeypatch):
    """`run(spec, input, **kw)`: run_pipeline on a pipeline laid out from `spec`, with the engine
    replaced by a stub that records the command."""
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []

    def engine(cmd, **k):
        launched.append(cmd)
        k["run_log"].write(b"N E X T F L O W  ~  version 25.10.4\n")

    monkeypatch.setattr(orchestration.execution, "run", engine)

    def go(spec, input_path, *, outdir=None, check_only=False, sheet_set=None, resume=False,
           warnings=None, name="pipe"):
        if not (tmp_path / "pipelines" / name).exists():
            S.make_pipeline(tmp_path, spec, name)
        res = orchestration.run_pipeline(
            name, repo_root=tmp_path, input_path=input_path,
            outdir=outdir or tmp_path / "results", profile="docker", params_file=None,
            cli_overrides={}, resume=resume, demo=False, check_only=check_only,
            write_provenance=True, timeout_seconds=None, sheet_set=sheet_set,
            on_warning=(warnings.append if warnings is not None else None))
        res.launched = launched
        return res
    return go


def _arg(command: str, flag: str) -> str:
    args = shlex.split(command)
    return args[args.index(flag) + 1]


def test_check_generates_stages_and_names_the_sheet(tmp_path, run):
    data = tmp_path / "data"
    a1, a2 = pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    said = []
    res = run(S.RNASEQ, str(data), check_only=True, sheet_set={"strandedness": "auto"},
              warnings=said)
    sheet = Path(_arg(res.command, "--input"))
    assert sheet.name == "samplesheet.csv" and res.generated_samplesheet == sheet
    assert sheet.read_text() == f"sample,fastq_1,fastq_2,strandedness\nA,{a1},{a2},auto\n"
    params = json.loads(Path(_arg(res.command, "-params-file")).read_text())
    assert params["input"] == str(sheet) and sheet.parent == Path(_arg(res.command, "-params-file")).parent
    assert not (tmp_path / "results").exists()
    assert any(w.startswith("Generated the pipe samplesheet") for w in said)
    assert any(str(sheet) in w for w in said)


def test_real_run_records_the_sheet_as_a_config_and_its_files_as_inputs(tmp_path, run):
    data = tmp_path / "data"
    files = [*pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz"), fq(data / "B.fastq.gz", "b")]
    out = tmp_path / "results"
    res = run(S.ATACSEQ, str(data), sheet_set={"replicate": "1"})
    prov = out / "provenance"
    sheet = prov / "samplesheet.csv"
    assert res.generated_samplesheet == sheet
    assert json.loads((prov / "params.json").read_text())["input"] == str(sheet)
    configs = provenance.read_checksums(prov / "configs.sha256", relative=False)
    assert str(sheet) in configs
    # atacseq's FastQ columns carry no path format: generation names its inputs all the same.
    inputs = provenance.read_checksums(prov / "inputs.sha256", relative=False)
    assert set(inputs) == {str(f) for f in files}
    manifest = json.loads((prov / "run_manifest.json").read_text())
    record = manifest["generated_samplesheet"]
    assert record["file"] == "samplesheet.csv" and record["samples"] == 2
    assert record["sha256"] == configs[str(sheet)] and record["sheet_set"] == {"replicate": "1"}
    command = res.launched[0]
    assert command[command.index("--input") + 1] == str(sheet)
    script = (prov / "commands.sh").read_text()
    assert '--input "$_script_dir"/samplesheet.csv' in script
    replay_guard.verify_dependencies(prov)
    # A moved bundle replays its own copy of the sheet; the guard finds and checks it there.
    moved = tmp_path / "moved"
    out.rename(moved)
    replay_guard.verify_dependencies(moved / "provenance")
    (moved / "provenance" / "samplesheet.csv").write_text("sample,fastq_1\n")
    with pytest.raises(ValueError, match="configs content changed"):
        replay_guard.verify_dependencies(moved / "provenance")


def test_failed_generation_leaves_the_outdir_untouched(tmp_path, run):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    with pytest.raises(NfclawError) as err:
        run(S.RNASEQ, str(data))
    assert err.value.code is ErrorCode.SAMPLESHEET_INVALID and "'strandedness'" in str(err.value)
    assert not (tmp_path / "results").exists()


def test_sheet_set_needs_a_generated_samplesheet(tmp_path, run):
    sheet = tmp_path / "sheet.csv"
    a1, _ = pair(tmp_path / "data", "A_R1.fastq.gz", "A_R2.fastq.gz")
    sheet.write_text(f"sample,fastq_1,strandedness\nA,{a1},auto\n")
    with pytest.raises(NfclawError) as err:
        run(S.RNASEQ, str(sheet), check_only=True, sheet_set={"strandedness": "auto"})
    assert err.value.code is ErrorCode.PARAMS_INVALID and "--sheet-set" in str(err.value)


def test_a_written_samplesheet_runs_exactly_as_before(tmp_path, run):
    a1, a2 = pair(tmp_path / "data", "A_R1.fastq.gz", "A_R2.fastq.gz")
    sheet = tmp_path / "sheet.csv"
    sheet.write_text(f"sample,fastq_1,fastq_2,strandedness\nA,{a1},{a2},auto\n")
    res = run(S.RNASEQ, str(sheet))
    assert "--input" not in res.launched[0] and res.generated_samplesheet is None
    manifest = json.loads((tmp_path / "results/provenance/run_manifest.json").read_text())
    assert "generated_samplesheet" not in manifest
    assert not (tmp_path / "results/provenance/samplesheet.csv").exists()


def test_resume_says_how_the_regenerated_sheet_changed(tmp_path, run):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    run(S.RNASEQ, str(data), sheet_set={"strandedness": "auto"})
    pair(data, "C_R1.fastq.gz", "C_R2.fastq.gz")
    said = []
    run(S.RNASEQ, str(data), sheet_set={"strandedness": "auto"}, resume=True, warnings=said)
    assert any("added: C" in w for w in said)
    sheet = tmp_path / "results/provenance/samplesheet.csv"
    assert re.search(r"^C,", sheet.read_text(), re.M)


def test_several_input_values(tmp_path, run):
    data = tmp_path / "data"
    a1, a2 = pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    pair(data, "B_R1.fastq.gz", "B_R2.fastq.gz")
    res = run(S.RNASEQ, [str(a1), str(a2)], check_only=True, sheet_set={"strandedness": "auto"})
    assert Path(_arg(res.command, "--input")).read_text().count("\n") == 2
