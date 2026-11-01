import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from runner import orchestration, preflight, resources, runlog, submodule
from runner.errors import ErrorCode, NfclawError
from runner.schema import Column, InputSchema
from runner.submodule import SubmoduleStatus


def _make_pipeline(tmp_path, name):
    up = tmp_path / "pipelines" / name / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    fix = Path(__file__).parent / "fixtures" / name / "nextflow_schema.json"
    shutil.copy(fix, up / "nextflow_schema.json")
    (tmp_path / "pipelines" / name / "skill.md").write_text(f"---\nname: {name}\n---\n")
    return tmp_path


def _staged_params(res):
    """The params file the run's command actually names.

    `--check` stages it outside --outdir (a dry run must leave the output directory alone), so
    tests read it from the command rather than assuming a location.
    """
    return json.loads(Path(
        re.search(r"-params-file (\S+)", res.command).group(1)).read_text())


def test_check_only_returns_command(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert res.checked_only and "nextflow" in res.command
    # The params file the printed command names must exist, so the command runs as printed...
    params = re.search(r"-params-file (\S+)", res.command).group(1)
    assert Path(params).is_file()
    # ...but it must NOT be staged inside --outdir: `--check` launches nothing, so it has to leave
    # the output directory exactly as it found it. Creating it, or dropping a provenance/ directory
    # in it, made the next real run fail the "--outdir is not empty" guard over an empty result set.
    assert not (tmp_path / "out").exists()
    checks = {row['id']: row for row in res.validation_scope['checks']}
    assert checks['source_identity']['status'] == 'checked'
    assert checks['local_samplesheets']['status'] == 'deferred'
    assert checks['profile_config']['status'] == 'deferred'
    assert checks['remote_inputs']['status'] == 'deferred'
    assert checks['scientific_completeness']['status'] == 'unsupported'


def test_full_run_invokes_execution(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    called = {}
    monkeypatch.setattr(orchestration.execution, "run",
                        lambda *a, **k: called.setdefault("ran", True))
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    assert called.get("ran") and not res.checked_only
    recorded = json.loads((tmp_path / 'out/provenance/run_manifest.json').read_text())
    assert recorded['validation_scope'] == res.validation_scope
    assert any(row['status'] == 'unsupported' for row in recorded['validation_scope']['checks'])


@pytest.mark.parametrize('generated', [False, True])
def test_preflight_scope_reports_a_local_table_only_after_it_is_validated(tmp_path, monkeypatch,
                                                                         library, generated):
    root = library('mini')
    read = tmp_path / 'sample_R1.fastq'
    read.write_text('@read\nACGT\n+\nIIII\n')
    table = tmp_path / 'samples.csv'
    table.write_text(f'sample,fastq_1,fastq_2\nsample,{read},\n')
    if generated:
        read2 = tmp_path / 'sample_R2.fastq'
        read2.write_text('@read\nTGCA\n+\nIIII\n')
        contract = root / 'pipelines/mini/upstream/assets/schema_input.json'
        data = json.loads(contract.read_text())
        for column in ('fastq_1', 'fastq_2'):
            data['items']['properties'][column]['pattern'] = r'^\S+\.fastq$'
        contract.write_text(json.dumps(data))
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
    result = orchestration.run_pipeline(
        'mini', repo_root=root, input_path=[str(read), str(read2)] if generated else str(table),
        outdir=tmp_path / 'out',
        profile='docker', params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=30)
    assert result.validation_scope['local_samplesheets'] == 1
    check = next(row for row in result.validation_scope['checks']
                 if row['id'] == 'local_samplesheets')
    assert check['status'] == 'checked'


def test_check_scope_does_not_claim_unreadable_data_bytes_were_checked(tmp_path, monkeypatch,
                                                                      library):
    root = library('mini')
    read = tmp_path / 'sample.fastq'
    read.write_text('@read\nACGT\n+\nIIII\n')
    read.chmod(0)
    table = tmp_path / 'samples.csv'
    table.write_text(f'sample,fastq_1,fastq_2\nsample,{read},\n')
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
    try:
        result = orchestration.run_pipeline(
            'mini', repo_root=root, input_path=str(table), outdir=tmp_path / 'out',
            profile='docker', params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=True, write_provenance=False, timeout_seconds=30)
    finally:
        read.chmod(0o600)
    checks = {row['id']: row for row in result.validation_scope['checks']}
    assert checks['local_data_bytes']['status'] == 'deferred'
    assert 'readable' not in checks['local_dependencies']['scope']


@pytest.mark.parametrize("console,expected", [
    (b"-[nf-core/mini] Pipeline completed successfully-\n", []),
    (b"-[nf-core/mini] Pipeline completed successfully, but with errored process(es) -\n",
     ["[nf-core/mini] Pipeline completed successfully, but with errored process(es)"])])
def test_a_successful_run_reports_the_caveats_its_pipeline_printed(tmp_path, monkeypatch, console,
                                                                   expected):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: k["run_log"].write(console))
    shown = []
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10,
        on_warning=shown.append)
    said = [f"the pipeline completed but reported: {c}" for c in expected]
    assert [w for w in res.warnings if w.startswith("the pipeline completed")] == said
    assert [w for w in shown if w.startswith("the pipeline completed")] == said
    manifest = json.loads((tmp_path / "out/provenance/run_manifest.json").read_text())
    assert manifest["outcome"] == "success"
    assert manifest.get("completion_caveats", []) == expected


def test_local_files_given_to_format_less_parameters_are_recorded_inputs(tmp_path, monkeypatch):
    # differentialabundance declares --feature-length-matrix without a path format: the gene lengths
    # a chain handed over were neither hashed nor replay-checked, and the chain's lineage broke.
    root = _make_pipeline(tmp_path, "mini")
    schema_path = root / "pipelines/mini/upstream/nextflow_schema.json"
    schema = json.loads(schema_path.read_text())
    props = schema["definitions"]["reference_genome_options"]["properties"]
    props["lengths"] = {"type": "string"}
    props["label"] = {"type": "string"}
    schema_path.write_text(json.dumps(schema))
    lengths = tmp_path / "data" / "gene_lengths.tsv"
    lengths.parent.mkdir()
    lengths.write_text("gene\tA\ng1\t100\n")
    (tmp_path / "data" / "notes").mkdir()
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None,
        cli_overrides={"lengths": str(lengths), "label": str(tmp_path / "data" / "notes")},
        resume=False, demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    hashed = (tmp_path / "out/provenance/inputs.sha256").read_text()
    assert str(lengths) in hashed                       # a file the pipeline reads
    assert "notes" not in hashed  # a directory or plain text is not guessed at


def test_engine_provenance_uses_the_executed_banner_without_probing_a_changed_launcher(
        tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k:
                        k["run_log"].write(b"N E X T F L O W  ~  version 25.10.4\n"))

    def changed_launcher(*args, **kwargs):
        raise AssertionError("the launcher after execution is not evidence of the engine that ran")

    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", changed_launcher)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    prov = tmp_path / "out/provenance"
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow"] == "nextflow version 25.10.4"
    assert "NXF_VER" not in manifest["nextflow_env"]
    assert "export NXF_VER=25.10.4" in (prov / "commands.sh").read_text()


def test_failed_run_still_writes_the_provenance_bundle(tmp_path, monkeypatch):
    # The replay script matters most after a failure — that is when the run gets fixed and retried.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])

    def boom(*a, **k):
        raise NfclawError(ErrorCode.EXECUTION_FAILED, "Nextflow exited 1")

    monkeypatch.setattr(orchestration.execution, "run", boom)
    with pytest.raises(NfclawError, match="Nextflow exited 1"):   # the real cause still surfaces
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    prov = tmp_path / "out" / "provenance"
    assert (prov / "commands.sh").exists()  # replayable once the cause is fixed
    assert json.loads((prov / "run_manifest.json").read_text())["outcome"] == "failed"


def test_provenance_failure_never_masks_the_run_failure(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])

    def boom(*a, **k):
        raise NfclawError(ErrorCode.EXECUTION_FAILED, "Nextflow exited 1")

    def prov_boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(orchestration.execution, "run", boom)
    monkeypatch.setattr(orchestration.provenance, "write", prov_boom)
    with pytest.raises(NfclawError, match="Nextflow exited 1"):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)


def test_attribution_failure_survives_bundle_recording_failure(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    source = root / "pipelines/mini/upstream/main.nf"
    monkeypatch.setattr(orchestration.execution, "run",
                        lambda *a, **k: source.write_text("changed"))
    def disk_full(**kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(orchestration.provenance, "write", disk_full)
    with pytest.raises(NfclawError, match="during execution") as error:
        orchestration.run_pipeline("mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False, demo=True,
            check_only=False, write_provenance=True, timeout_seconds=10)
    assert error.value.code == ErrorCode.ENVIRONMENT


def test_failed_engine_keeps_its_error_and_records_changed_dependencies(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    source = root / "pipelines/mini/upstream/main.nf"
    def fail(*args, **kwargs):
        source.write_text("changed before pipeline failure")
        raise NfclawError(ErrorCode.EXECUTION_FAILED, "original engine failure")
    monkeypatch.setattr(orchestration.execution, "run", fail)
    out = tmp_path / "out"
    with pytest.raises(NfclawError, match="original engine failure") as error:
        orchestration.run_pipeline("mini", repo_root=root, input_path=None, outdir=out,
            profile="docker", params_file=None, cli_overrides={}, resume=False, demo=True,
            check_only=False, write_provenance=True, timeout_seconds=10)
    assert error.value.code == ErrorCode.EXECUTION_FAILED
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["outcome"] == "failed"
    assert manifest["dependency_stability"]["status"] == "changed"
    assert "previous execution" in orchestration._input_resume_warning(out, {}, {})


@pytest.mark.parametrize("stop",
                         [lambda: orchestration.execution.Terminated(15), KeyboardInterrupt])
def test_stopped_run_with_unchanged_dependencies_resumes_with_its_cache(tmp_path,
                                                                        monkeypatch, stop):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    def stopped(*args, **kwargs):
        raise stop()
    monkeypatch.setattr(orchestration.execution, "run", stopped)
    out = tmp_path / "out"
    with pytest.raises((orchestration.execution.Terminated, KeyboardInterrupt)):
        orchestration.run_pipeline("mini", repo_root=root, input_path=None, outdir=out,
            profile="docker", params_file=None, cli_overrides={}, resume=False, demo=True,
            check_only=False, write_provenance=True, timeout_seconds=10)
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["dependency_stability"]["status"] == "unchanged"
    # Stopping a run (Ctrl-C, `kill`) must not cost its cache: --resume continues where it stopped.
    assert orchestration._input_resume_warning(out, {}, {}) is None


def test_stopped_run_records_dependencies_changed_before_the_stop(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    source = root / "pipelines/mini/upstream/main.nf"
    def stopped(*args, **kwargs):
        source.write_text("changed before the stop")
        raise orchestration.execution.Terminated(15)
    monkeypatch.setattr(orchestration.execution, "run", stopped)
    out = tmp_path / "out"
    with pytest.raises(orchestration.execution.Terminated):
        orchestration.run_pipeline("mini", repo_root=root, input_path=None, outdir=out,
            profile="docker", params_file=None, cli_overrides={}, resume=False, demo=True,
            check_only=False, write_provenance=True, timeout_seconds=10)
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["dependency_stability"]["status"] == "changed"
    assert "fresh Nextflow cache session" in orchestration._input_resume_warning(out, {}, {})


def test_passes_effective_work_dir_and_allow_spaces_to_preflight(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    seen = {}
    monkeypatch.setattr(orchestration.preflight, "check_environment",
                        lambda **k: seen.update(k) or [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=False, timeout_seconds=10,
        nxf_env={"NXF_WORK": "/scratch/work"}, allow_spaces=True)
    assert seen["work_dir"] == Path("/scratch/work")          # NXF_WORK overlay wins
    assert seen["allow_spaces"] is True


def test_work_dir_defaults_under_repo_when_no_nxf_work(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.delenv("NXF_WORK", raising=False)
    seen = {}
    monkeypatch.setattr(orchestration.preflight, "check_environment",
                        lambda **k: seen.update(k) or [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert seen["work_dir"] == root / "work"                  # Nextflow default: <cwd>/work


def test_relative_nxf_work_is_resolved_before_nextflow_changes_cwd(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path / "repo", "mini")
    caller = tmp_path / "caller"
    caller.mkdir()
    monkeypatch.chdir(caller)
    seen = {}
    monkeypatch.setattr(orchestration.preflight, "check_environment",
                        lambda **k: seen.update(k) or [])
    result = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        nxf_env={"NXF_WORK": "scratch/work"})
    expected = (caller / "scratch/work").resolve()
    assert seen["work_dir"] == expected
    assert f"-work-dir {expected}" in result.command


def test_space_in_repo_path_blocks_the_run(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path / "draft 2", "mini")        # repo path has a space
    # real preflight, but isolate from tool/daemon checks so only the space rule can fire
    monkeypatch.setattr(orchestration.preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr(orchestration.preflight, "capture",
                        lambda
                        *a, **k: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path="https://example.test/samplesheet.csv",
            outdir=tmp_path / "out",
            profile="singularity", params_file=None, cli_overrides={}, resume=False,
            demo=False, check_only=True, write_provenance=False, timeout_seconds=10)
    assert exc.value.code == ErrorCode.ENVIRONMENT
    assert any("space" in i for i in exc.value.details["issues"])


def _healthy_env(monkeypatch):
    # real preflight, but tools present and docker daemon healthy, so only the rule under test fires
    monkeypatch.setattr(orchestration.preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr(orchestration.preflight, "capture",
                        lambda
                        *a, **k: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())


def test_check_only_allows_nonempty_outdir(tmp_path, monkeypatch):
    # --check validates without launching, so an existing (non-empty) results dir must not block it.
    root = _make_pipeline(tmp_path / "repo", "mini")
    _healthy_env(monkeypatch)
    out = tmp_path / "out"                                    # outside the repo
    out.mkdir()
    (out / "prev.txt").write_text("a previous run's results")
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=out,
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert res.checked_only and "nextflow" in res.command


def test_full_run_still_blocks_nonempty_outdir(tmp_path, monkeypatch):
    # The guard is intact for an actual run: a non-empty outdir without --resume is rejected.
    root = _make_pipeline(tmp_path / "repo", "mini")
    _healthy_env(monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    (out / "prev.txt").write_text("a previous run's results")
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=out,
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=False, timeout_seconds=10)
    assert exc.value.code == ErrorCode.ENVIRONMENT
    assert any("not empty" in i for i in exc.value.details["issues"])


def test_configs_passed_to_build_as_extra_configs(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    cfg = tmp_path / "extra.config"
    cfg.write_text("docker { runOptions = '--network host' }\n")
    seen = {}
    real_build = orchestration.nextflow_command.build
    monkeypatch.setattr(orchestration.nextflow_command, "build",
                        lambda **k: (seen.update(k), real_build(**k))[1])
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        configs=[str(cfg)])
    assert seen["extra_configs"] == (cfg.resolve(),)  # resolved to absolute, passed as -c


def test_obsolete_validation_param_injects_ignoreparams_config(tmp_path, monkeypatch):
    # A pinned release that declares nf-schema 2.x but still sets an nf-validation 1.x param gets a
    # generated `-c` config that neutralises the inert "not a valid parameter" warning — without
    # editing the release tree. The staged file lists the param under validation.ignoreParams.
    root = _make_pipeline(tmp_path, "mini")
    up = root / "pipelines" / "mini" / "upstream"
    (up / "nextflow.config").write_text("plugins { id 'nf-schema@2.5.1' }\n")
    (up / "conf").mkdir()
    (up / "conf" / "test.config").write_text(
        "params {\n    validationSchemaIgnoreParams = 'genomes'\n}\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    m = re.search(r"-c (\S+nf_schema_compat\.config)", res.command)
    assert m, res.command
    assert "validationSchemaIgnoreParams" in Path(m.group(1)).read_text()


def test_clean_release_injects_no_compat_config(tmp_path, monkeypatch):
    # The default fixture declares no such plugin/param, so no compat `-c` is added — the injection
    # is confined to the actual nf-schema-2.x-plus-1.x-param defect.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert "nf_schema_compat.config" not in res.command


def test_missing_config_fails_fast(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
            configs=["/no/such/file.config"])
    assert exc.value.code == ErrorCode.ENVIRONMENT and "config" in str(exc.value).lower()


def test_url_input_skips_local_validation_and_is_forwarded(tmp_path, monkeypatch):
    # A remote --input (URL) can't be read locally, so it must skip the samplesheet pre-check and be
    # forwarded to Nextflow unchanged (nf-schema stages + validates it). Mirrors nf-core behavior.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    # Force a non-None input schema so the ONLY thing that skips the pre-check is the URL
    # (str) type.
    monkeypatch.setattr(orchestration.schema_mod, "load_input_schema",
                        lambda repo, rel="assets/schema_input.json":
                        InputSchema(columns=(Column("sample", "string", True, None, None),)))
    called = {}
    monkeypatch.setattr(orchestration.samplesheet, "validate",
                        lambda *a, **k: called.setdefault("validated", True) or [])
    url = "https://raw.githubusercontent.com/nf-core/x/samplesheet.csv"
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=url, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=False, check_only=True, write_provenance=False, timeout_seconds=10)
    assert "validated" not in called                          # local pre-check skipped for a URL
    params = _staged_params(res)
    assert params["input"] == url                             # forwarded unchanged, not mangled


def test_missing_params_file_fails_fast(tmp_path, monkeypatch):
    # A --params-file the user named but that doesn't exist must fail fast, not be silently
    # dropped (which would run with none of its values). Mirrors the --config contract.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    ran: dict = {}
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: ran.setdefault("x", True))
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=Path("/no/such/params.json"), cli_overrides={},
            resume=False, demo=True, check_only=False, write_provenance=False, timeout_seconds=10)
    assert exc.value.code == ErrorCode.PARAMS_INVALID and "params-file" in str(exc.value).lower()
    assert "x" not in ran                                         # never reached execution


def test_existing_params_file_is_used(tmp_path, monkeypatch):
    # The happy path still works: an existing params-file is read and its values reach the run.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    pf = tmp_path / "p.json"
    pf.write_text('{"aligner": "hisat2"}')
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=pf, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    params = _staged_params(res)
    assert params["aligner"] == "hisat2"


def test_runs_from_outdir_with_shared_work_dir(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.delenv("NXF_WORK", raising=False)
    eseen, bseen = {}, {}
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: eseen.update(k))
    real_build = orchestration.nextflow_command.build
    monkeypatch.setattr(orchestration.nextflow_command, "build",
                        lambda **k: (bseen.update(k), real_build(**k))[1])
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=False, timeout_seconds=10)
    assert eseen["cwd"] == tmp_path / "out"                       # isolates .nextflow/ per run
    assert bseen["work_dir"] == root / "work"                    # work stays shared, off the outdir


def test_run_is_logged_in_the_bundle_with_nextflow_log_and_advisories(tmp_path, monkeypatch):
    # The run log lives at a fixed place — <outdir>/provenance/logs/run.log — so nobody has to be
    # told where it is; Nextflow's own log is resolved against the outdir it is launched from.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.plugin_compat, "check",
                        lambda *a, **k: ["inert release warning"])
    monkeypatch.delenv("NXF_LOG_FILE", raising=False)
    eseen = {}
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: eseen.update(k))
    out = tmp_path / "out"
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=out,
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=False, timeout_seconds=10)
    log_path = out / "provenance" / "logs" / "run.log"
    assert eseen["run_log"].path == log_path and eseen["logs_dir"] == log_path.parent
    assert eseen["run_log"].nextflow_log == out / ".nextflow.log"
    log = log_path.read_text()
    assert "warning: inert release warning" in log
    assert f"nextflow log: {out / '.nextflow.log'}" in log
    assert log.rstrip().splitlines()[-1].endswith(": success")
    assert res.log_path == log_path


def test_run_log_states_the_outcome_only_once_the_bundle_is_written(tmp_path, monkeypatch):
    # Its last line is what a background run is polled on; it must not say "success" while nfclaw is
    # still hashing the outputs into the bundle (minutes for a large run).
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    log_path = tmp_path / "out" / "provenance" / "logs" / "run.log"
    at_bundle_time = {}
    real_write = orchestration.provenance.write

    def write(**k):
        at_bundle_time["log"] = log_path.read_text()
        return real_write(**k)

    monkeypatch.setattr(orchestration.provenance, "write", write)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    assert "nfclaw run finished" not in at_bundle_time["log"]
    assert log_path.read_text().rstrip().splitlines()[-1].endswith(": success")


def test_failed_run_log_ends_after_the_bundle_with_the_failure(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])

    def boom(*a, **k):
        err = NfclawError(ErrorCode.EXECUTION_FAILED, "Nextflow exited 3")
        k["run_log"].fail("failed (exit status 3)", str(err))
        raise err

    monkeypatch.setattr(orchestration.execution, "run", boom)
    with pytest.raises(NfclawError):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    log = (tmp_path / "out" / "provenance" / "logs" / "run.log").read_text()
    assert "Nextflow exited 3" in log
    assert log.rstrip().splitlines()[-1].endswith(": failed (exit status 3)")
    assert (tmp_path / "out" / "provenance" / "run_manifest.json").exists()


def test_run_log_never_claims_success_when_nfclaw_fails_after_nextflow(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)

    def disk_full(**k):
        raise OSError("No space left on device")

    monkeypatch.setattr(orchestration.provenance, "write", disk_full)
    with pytest.raises(NfclawError) as exc:                  # a clear error, not a raw OSError
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    assert "run succeeded" in str(exc.value) and isinstance(exc.value.__cause__, OSError)
    log = (tmp_path / "out" / "provenance" / "logs" / "run.log").read_text()
    assert "No space left on device" in log
    last = log.rstrip().splitlines()[-1]
    assert not last.endswith(": success") and "after Nextflow succeeded" in last


def test_check_only_names_no_run_log(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert res.log_path is None                                   # --check launches nothing


def test_pipeline_version_routed_through_versions_ensure(tmp_path, monkeypatch):
    # A requested version is resolved/materialized via versions.ensure; everything downstream
    # (schema, validation, command) then targets whatever tree it returns.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    captured = {}

    def fake_ensure(name, version, *, pipelines_dir, repo_root):
        captured["version"] = version
        return submodule.resolve_at(name, pipelines_dir / name / "upstream")

    monkeypatch.setattr(orchestration.versions, "ensure", fake_ensure)
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        pipeline_version="1.2.0")
    assert captured["version"] == "1.2.0"
    assert "nextflow" in res.command


def test_default_run_uses_no_version(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    captured = {}

    def fake_ensure(name, version, *, pipelines_dir, repo_root):
        captured["version"] = version
        return submodule.resolve_at(name, pipelines_dir / name / "upstream")

    monkeypatch.setattr(orchestration.versions, "ensure", fake_ensure)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert captured["version"] is None                          # default = pinned latest


def test_nxf_overlay_flows_to_execution_and_provenance(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    seen = {}
    monkeypatch.setattr(orchestration.execution, "run",
                        lambda *a, **k: seen.update({"exec_env": k.get("env_extra")}))
    # stub the version probe so the provenance step doesn't invoke real `nextflow -version` with
    # NXF_VER set (which would try to fetch that engine — execution.run is mocked here).
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version",
                        lambda env_extra=None: "stub")
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10,
        nxf_ver="25.10.2", nxf_env={"NXF_JVM_ARGS": "-Dx=y"})
    overlay = {"NXF_JVM_ARGS": "-Dx=y", "NXF_VER": "25.10.2"}
    assert seen["exec_env"] == overlay  # applied to the nextflow subprocess
    manifest = json.loads((tmp_path / "out" / "provenance" / "run_manifest.json").read_text())
    assert manifest["nextflow_env"] == overlay  # and recorded for reproducibility


def test_only_a_check_whose_advisories_are_read_judges_the_declared_engine(tmp_path, monkeypatch):
    # Nextflow enforces `manifest.nextflowVersion` when it launches, so a launch is not pre-judged.
    # A check never launches it: `--check` (and a chain's) judges the pin instead, while a chain's
    # silent validation before its real run does not probe at all.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    seen = []
    monkeypatch.setattr(orchestration.engine_version, "check",
                        lambda upstream, **k: seen.append(k.get("nxf_ver")) or ["engine too old"])
    common = dict(repo_root=root, input_path=None, profile="docker", params_file=None,
                  cli_overrides={}, resume=False, demo=True, write_provenance=False,
                  timeout_seconds=10, nxf_ver="25.10.2")
    shown = []
    orchestration.run_pipeline("mini", outdir=tmp_path / "check", check_only=True,
                               on_warning=shown.append, **common)
    assert seen == ["25.10.2"] and "engine too old" in shown
    orchestration.run_pipeline("mini", outdir=tmp_path / "silent", check_only=True, **common)
    orchestration.run_pipeline("mini", outdir=tmp_path / "run", check_only=False,
                               on_warning=shown.append, **common)
    assert seen == ["25.10.2"]


def _make_pipeline_with_bool(tmp_path, name="boolp"):
    up = tmp_path / "pipelines" / name / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    (up / "nextflow_schema.json").write_text(json.dumps({"definitions": {"io": {"properties": {
        "outdir": {"type": "string", "format": "directory-path"},
        "skip_busco": {"type": "boolean"}}}}}))
    (tmp_path / "pipelines" / name / "skill.md").write_text(f"---\nname: {name}\n---\n")
    return tmp_path


def test_boolean_cli_string_is_coerced_in_params_file(tmp_path, monkeypatch):
    root = _make_pipeline_with_bool(tmp_path)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "boolp", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={"skip_busco": "true"},
        resume=False, demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    params = _staged_params(res)
    assert params["skip_busco"] is True  # CLI "true" → real boolean for nf-schema


def test_invalid_param_rejected_before_execution(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    ran: dict = {}
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: ran.setdefault("x", True))
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={"aligner": "bowtie"},  # not in enum
            resume=False, demo=True, check_only=False, write_provenance=False, timeout_seconds=10)
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "x" not in ran                                         # never reached execution
    assert any("must be one of" in i for i in exc.value.details["issues"])


def test_missing_required_param_rejected_before_preflight(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    reached_preflight = {}
    monkeypatch.setattr(orchestration.preflight, "check_environment",
                        lambda **k: reached_preflight.setdefault("x", True) or [])
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=False, check_only=True, write_provenance=False, timeout_seconds=10)
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "missing required parameter '--input'" in str(exc.value)
    assert "x" not in reached_preflight


def test_demo_allows_required_input_to_come_from_test_profile(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert res.checked_only and "-profile test,docker" in res.command


def test_a_profile_or_config_that_can_set_params_defers_required_checks(tmp_path, monkeypatch):
    # nf-core's canonical test command is `-profile test,docker` (no --demo), and a --config file
    # can set `params.input`; nf-schema sees both, so rejecting them as "missing --input" up front
    # was a false positive. Only an engine-only profile with no --config is judged by nfclaw.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    cfg = tmp_path / "params.config"
    cfg.write_text("params.input = '/data/ss.csv'\n")
    for profile, configs in (("test,docker", ()), ("docker,mylab", ()), ("docker", (str(cfg),))):
        res = orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile=profile, params_file=None, cli_overrides={}, resume=False,
            demo=False, check_only=True, write_provenance=False, timeout_seconds=10,
            configs=configs)
        assert res.checked_only, profile


def test_engine_profiles_alone_still_require_the_input(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    for profile in ("docker", "singularity,arm64", "conda,debug"):
        with pytest.raises(NfclawError, match="missing required parameter '--input'"):
            orchestration.run_pipeline(
                "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
                profile=profile, params_file=None, cli_overrides={}, resume=False,
                demo=False, check_only=True, write_provenance=False, timeout_seconds=10)


def _pipeline_with_report_suffix(tmp_path, name="mini"):
    """`mini`, plus the nf-core template's trace_report_suffix parameter."""
    root = _make_pipeline(tmp_path, name)
    schema_path = root / "pipelines" / name / "upstream" / "nextflow_schema.json"
    data = json.loads(schema_path.read_text())
    data["definitions"]["generic_options"] = {
        "title": "Generic options",
        "properties": {"trace_report_suffix": {"type": "string", "hidden": True}},
    }
    schema_path.write_text(json.dumps(data))
    return root


def test_resource_limits_become_a_config_passed_to_nextflow(tmp_path, monkeypatch):
    # nf-core's documented ceiling: a process.resourceLimits config handed to Nextflow with -c.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.engine_version, "effective", lambda *a: "25.10.4")
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        limits=resources.parse(4, "15.GB", "1.h"))
    cfg = Path(re.search(r"-c (\S+)", res.command).group(1))
    assert cfg.name == "resource_limits.config"
    assert cfg.is_file() and "resourceLimits" in cfg.read_text()
    assert cfg.parent == Path(
        re.search(r"-params-file (\S+)", res.command).group(1)).parent   # staged with the params


def test_no_config_is_generated_when_no_limit_is_given(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert "-c " not in res.command
    assert not (tmp_path / "out").exists()             # --check stages nothing in the outdir


def test_an_explicit_config_still_overrides_the_generated_ceiling(tmp_path, monkeypatch):
    # Nextflow lets a later -c win, so the user's own file must come after the generated one.
    root = _make_pipeline(tmp_path, "mini")
    mine = tmp_path / "mine.config"
    mine.write_text("process { resourceLimits = [ cpus: 2 ] }\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.engine_version, "effective", lambda *a: "25.10.4")
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        configs=[str(mine)], limits=resources.parse(4, None, None))
    generated = re.search(r"-c (\S*resource_limits\.config)", res.command).group(1)
    assert res.command.index(generated) < res.command.index(str(mine))


def test_check_asks_the_engine_to_resolve_the_configuration_it_prints(tmp_path, monkeypatch):
    # `--check` probes what the printed command loads — its source, its profile and every `-c` it
    # names, the generated ceiling first — under the engine environment the run would get, and only
    # then reports the profile configuration as checked.
    root = _make_pipeline(tmp_path, "mini")
    mine = tmp_path / "mine.config"
    mine.write_text("process { cpus = 1 }\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.engine_version, "effective", lambda *a: "25.10.4")
    monkeypatch.setattr(orchestration.config_probe.shutil, "which", lambda name: "/bin/nextflow")
    seen = []
    monkeypatch.setattr(orchestration.config_probe, "capture", lambda cmd, **kw: seen.append(
        (cmd, kw["env"])) or subprocess.CompletedProcess(cmd, 0, "", ""))
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        configs=[str(mine)], limits=resources.parse(4, None, None),
        nxf_env={"NXF_OFFLINE": "true"}, probe_config=True)
    [(cmd, env)] = seen
    generated = re.search(r"-c (\S*resource_limits\.config)", res.command).group(1)
    assert cmd == ["nextflow", "-c", generated, "-c", str(mine), "config",
                   str(root / "pipelines/mini/upstream"), "-profile", "test,docker"]
    assert env["NXF_OFFLINE"] == "true"
    checks = {row['id']: row['status'] for row in res.validation_scope['checks']}
    assert checks['profile_config'] == 'checked'


def test_check_refuses_a_configuration_the_engine_cannot_parse(tmp_path, monkeypatch):
    # The release Nextflow 26.04's strict parser rejects is refused by `--check`, with the legacy
    # parser named as the remedy — not first found at launch. Nothing staged for it is left behind.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.config_probe.shutil, "which", lambda name: "/bin/nextflow")
    monkeypatch.setattr(orchestration.config_probe.engine_version, "effective",
                        lambda pinned=None: pinned or "26.04.3")
    monkeypatch.setattr(orchestration.config_probe, "capture",
                        lambda cmd, **kw: subprocess.CompletedProcess(
                            cmd, 1, "ERROR ~ Config parsing failed\n", ""))
    staged = []
    real_mkdtemp = orchestration.tempfile.mkdtemp
    monkeypatch.setattr(orchestration.tempfile, "mkdtemp",
                        lambda *a, **kw: staged.append(real_mkdtemp(*a, **kw)) or staged[-1])
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
            probe_config=True)
    assert exc.value.code is ErrorCode.ENVIRONMENT
    [issue] = exc.value.details["issues"]
    assert "cannot parse its configuration" in issue
    assert "--nxf-env NXF_SYNTAX_PARSER=v1" in issue and "Config parsing failed" in issue
    [check_staging] = [d for d in staged if Path(d).name.startswith("nfclaw-check-")]
    assert not Path(check_staging).exists()
    assert not (tmp_path / "out").exists()


def test_a_real_run_takes_no_configuration_probe(tmp_path):
    # A launch is its own probe: the flag exists for `--check` alone.
    with pytest.raises(ValueError, match="probe_config"):
        orchestration.run_pipeline(
            "mini", repo_root=tmp_path, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=False, check_only=False, write_provenance=False, timeout_seconds=None,
            probe_config=True)


def test_report_suffix_is_pinned_so_the_replay_reproduces_the_run(tmp_path, monkeypatch):
    # Without this the pipeline re-evaluates `now()` on every launch and the replay writes a second,
    # differently-named set of reports rather than reproducing the original run's outputs.
    root = _pipeline_with_report_suffix(tmp_path)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    params = json.loads((tmp_path / "out" / "provenance" / "params.json").read_text())
    suffix = params["trace_report_suffix"]
    assert suffix
    # commands.sh replays through the same params file, so the replay reuses this exact suffix.
    replay = (tmp_path / "out" / "provenance" / "commands.sh").read_text()
    assert '"$_script_dir"/params.json' in replay


def test_a_release_without_the_report_suffix_param_is_untouched(tmp_path, monkeypatch):
    # Older releases predate the parameter — passing it would fail nf-schema validation.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert "trace_report_suffix" not in _staged_params(res)


def test_check_leaves_an_existing_outdir_untouched(tmp_path, monkeypatch):
    # The reported failure in full: --check against a results directory must not add anything to it.
    root = _make_pipeline(tmp_path, "mini")
    out = tmp_path / "out"
    out.mkdir()
    (out / "results.txt").write_text("a previous run")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=out,
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10)
    assert [p.name for p in out.iterdir()] == ["results.txt"]      # nothing added


def test_a_real_run_after_a_check_is_not_blocked_as_non_empty(tmp_path, monkeypatch):
    # The end-to-end regression, asserted against the REAL preflight guard: after a --check, the
    # output directory must still look untouched to it, so the next real run is not refused.
    root = _make_pipeline(tmp_path, "mini")
    out = tmp_path / "out"                       # outside the repo root, as a real --outdir is
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=out, profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=True,
        write_provenance=False, timeout_seconds=10)
    st = submodule.resolve("mini", root / "pipelines")
    issues = preflight.check_environment(
        profile="docker", output_dir=out, submodule=st, repo_root=tmp_path / "repo",
        resume=False, check_only=False, allow_spaces=True)
    assert not any("not empty" in i for i in issues), issues


def _make_pipeline_with_input(tmp_path, input_param, name="inp"):
    """A pipeline whose `--input` is declared by `input_param`, shipping the conventional
    assets/schema_input.json (a FASTQ samplesheet) whether or not `--input` actually uses it."""
    up = tmp_path / "pipelines" / name / "upstream"
    (up / "assets").mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    (up / "nextflow_schema.json").write_text(json.dumps({"$defs": {"io": {"properties": {
        "input": input_param,
        "outdir": {"type": "string", "format": "directory-path"}}}}}))
    (up / "assets" / "schema_input.json").write_text(json.dumps({"items": {
        "properties": {"sample": {"type": "string"},
                       "fastq_1": {"type": "string", "format": "file-path"}},
        "required": ["sample", "fastq_1"]}}))
    (tmp_path / "pipelines" / name / "skill.md").write_text(f"---\nname: {name}\n---\n")
    return tmp_path


def _check(root, tmp_path, input_value, name="inp"):
    return orchestration.run_pipeline(
        name, repo_root=root, input_path=input_value, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=False, check_only=True, write_provenance=False, timeout_seconds=None)


def test_input_false_leaves_input_unset(tmp_path, monkeypatch):
    # sarek documents `--input false` for runs without a samplesheet (e.g. --build_only_index). It
    # became <cwd>/false. A boolean false is no better: nf-schema 2.7.2 (sarek 3.8) rejects it for a
    # string `input` ("Value is [boolean] but should be [string]", verified), while leaving `input`
    # unset passes every nf-schema version — and sarek only tests the value's truthiness.
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "format": "file-path", "exists": True,
        "schema": "assets/schema_input.json"})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    assert "input" not in _staged_params(_check(root, tmp_path, "false"))


def test_accession_input_is_forwarded_unchanged(tmp_path, monkeypatch):
    # mhcquant takes a PRIDE accession as --input; it must not become <cwd>/PXD009752.
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "pattern": r"^(PXD\d{6,}|\S+\.sdrf\.tsv|\S+\.tsv)$",
        "if": {"pattern": r"\.tsv$", "not": {"pattern": r"\.sdrf\.tsv$"}},
        "then": {"format": "file-path", "exists": True, "schema": "assets/schema_input.json"}})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    assert _staged_params(_check(root, tmp_path, "PXD009752"))["input"] == "PXD009752"


def test_directory_input_is_not_prechecked_as_a_samplesheet(tmp_path, monkeypatch):
    # rangeland's --input is a directory of imagery; its leftover template schema_input.json
    # (sample, fastq_1) must not be applied to it.
    root = _make_pipeline_with_input(tmp_path, {"type": "string", "format": "path", "exists": True})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "imagery").mkdir()
    params = _staged_params(_check(root, tmp_path, "imagery"))
    assert params["input"] == str(tmp_path / "imagery")


def test_missing_directory_input_fails_fast(tmp_path, monkeypatch):
    root = _make_pipeline_with_input(tmp_path, {"type": "string", "format": "path", "exists": True})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(NfclawError) as exc:
        _check(root, tmp_path, "imagery")
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "--input not found" in str(exc.value)


def test_samplesheet_input_is_still_prechecked(tmp_path, monkeypatch):
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "format": "file-path", "schema": "assets/schema_input.json"})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ss.csv").write_text("sample\nA\n")          # missing the required fastq_1 column
    with pytest.raises(NfclawError) as exc:
        _check(root, tmp_path, "ss.csv")
    assert exc.value.code == ErrorCode.SAMPLESHEET_INVALID


@pytest.mark.parametrize("change", ["malformed", "missing"])
def test_input_snapshot_refuses_a_sheet_changed_after_validation_before_launch(
        tmp_path, monkeypatch, change):
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "format": "file-path", "schema": "assets/schema_input.json"})
    reads = tmp_path / "reads.fastq.gz"
    reads.write_text("reads")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,fastq_1,description\nA,{reads},valid\n")
    validate = orchestration.samplesheet.validate

    def changed_after_validation(path, schema):
        issues = validate(path, schema)
        assert not issues
        if change == "missing":
            path.unlink()
        else:
            path.write_text(f'sample,fastq_1,description\nA,{reads},"unterminated\nB,{reads},second\n')
        return issues

    launched = []
    monkeypatch.setattr(orchestration.samplesheet, "validate", changed_after_validation)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launched.append(True))
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *a, **k: "")
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline(
            "inp", repo_root=root, input_path=str(sheet), outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=False, check_only=False, write_provenance=True, timeout_seconds=10)
    expected = ErrorCode.ENVIRONMENT if change == "missing" else ErrorCode.SAMPLESHEET_INVALID
    assert error.value.code is expected
    assert str(sheet) in str(error.value)
    assert not launched
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("check_only", [False, True])
@pytest.mark.parametrize("auxiliary", [False, True])
@pytest.mark.parametrize("phase", ["validation", "discovery", "probe"])
def test_validated_descriptor_cannot_select_different_data_before_launch(
        tmp_path, monkeypatch, check_only, auxiliary, phase):
    if auxiliary:
        root = _pipeline_with_auxiliary_sheet(tmp_path)
        header = "label,fasta"
    else:
        root = _make_pipeline_with_input(tmp_path, {
            "type": "string", "format": "file-path", "schema": "assets/schema_input.json"})
        header = "sample,fastq_1"
    first, second = tmp_path / "first.fastq.gz", tmp_path / "second.fastq.gz"
    first.write_text("ordinary dataset A")
    second.write_text("ordinary dataset B")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"{header}\nA,{first}\n")
    module, function = {"validation": (orchestration.samplesheet, "validate"),
                        "discovery": (orchestration.provenance, "samplesheet_dependencies"),
                        "probe": (orchestration.plugin_compat, "check")}[phase]
    original = getattr(module, function)

    def replace_descriptor(*args, **kwargs):
        result = original(*args, **kwargs)
        sheet.write_text(f"{header}\nA,{second}\n")
        return result

    monkeypatch.setattr(module, function, replace_descriptor)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launched.append(True))
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline(
            "inp", repo_root=root, input_path=None if auxiliary else str(sheet),
            outdir=tmp_path / "out", profile="docker", params_file=None,
            cli_overrides={"references": str(sheet)} if auxiliary else {}, resume=False,
            demo=True, check_only=check_only, write_provenance=True, timeout_seconds=10)
    assert error.value.code is ErrorCode.SAMPLESHEET_INVALID
    assert str(sheet) in str(error.value)
    assert not launched and not (tmp_path / "out").exists()


@pytest.mark.parametrize("check_only", [False, True])
def test_validated_descriptor_namespace_cannot_change_with_identical_bytes(
        tmp_path, monkeypatch, check_only):
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "format": "file-path", "schema": "assets/schema_input.json"})
    reads = tmp_path / "reads.fastq.gz"
    reads.write_text("ordinary reads")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,fastq_1\nA,{reads}\n")
    other = tmp_path / "identical.csv"
    other.write_bytes(sheet.read_bytes())

    def replace_namespace(*a, **k):
        sheet.unlink()
        sheet.symlink_to(other)
        return []

    monkeypatch.setattr(orchestration.plugin_compat, "check", replace_namespace)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launched.append(True))
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline(
            "inp", repo_root=root, input_path=str(sheet), outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=check_only, write_provenance=True, timeout_seconds=10)
    assert error.value.code is ErrorCode.SAMPLESHEET_INVALID
    assert not launched and not (tmp_path / "out").exists()


@pytest.mark.parametrize("phase,check_only", [("input_baseline", False),
                                              ("command", False), ("command", True)])
def test_descriptor_change_during_launch_preparation_is_refused(
        tmp_path, monkeypatch, phase, check_only):
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "format": "file-path", "schema": "assets/schema_input.json"})
    first, second = tmp_path / "first.fastq.gz", tmp_path / "second.fastq.gz"
    first.write_text("ordinary dataset A")
    second.write_text("ordinary dataset B")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,fastq_1\nA,{first}\n")
    if phase == "input_baseline":
        original = orchestration.provenance.snapshot_inputs

        def snapshot(paths):
            if first in paths:
                sheet.write_text(f"sample,fastq_1\nA,{second}\n")
            return original(paths)

        monkeypatch.setattr(orchestration.provenance, "snapshot_inputs", snapshot)
    else:
        original = orchestration.nextflow_command.build

        def build(*args, **kwargs):
            result = original(*args, **kwargs)
            sheet.write_text(f"sample,fastq_1\nA,{second}\n")
            return result

        monkeypatch.setattr(orchestration.nextflow_command, "build", build)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launched.append(True))
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline(
            "inp", repo_root=root, input_path=str(sheet), outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=check_only, write_provenance=True, timeout_seconds=10)
    assert error.value.code is ErrorCode.SAMPLESHEET_INVALID
    assert not launched and not (tmp_path / "out/provenance/run_manifest.json").exists()
    if phase == "input_baseline":
        assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("check_only", [False, True])
@pytest.mark.parametrize("change_descriptor", [False, True])
def test_a_descriptor_used_for_two_roles_retains_its_first_validation_snapshot(
        tmp_path, monkeypatch, check_only, change_descriptor):
    root = _pipeline_with_auxiliary_sheet(tmp_path)
    up = root / "pipelines/inp/upstream"
    schema_file = up / "nextflow_schema.json"
    schema = json.loads(schema_file.read_text())
    schema["$defs"]["io"]["properties"]["input"] = {
        "type": "string", "format": "file-path", "schema": "assets/schema_input.json"}
    schema_file.write_text(json.dumps(schema))
    first, second = tmp_path / "first.fastq.gz", tmp_path / "second.fastq.gz"
    first.write_text("ordinary dataset A")
    second.write_text("ordinary dataset B")
    fasta = tmp_path / "reference.fa"
    fasta.write_text(">chr\nACGT\n")
    sheet = tmp_path / "shared.csv"
    sheet.write_text(f"sample,fastq_1,label,fasta\nA,{first},ref,{fasta}\n")
    original = orchestration.samplesheet.validate
    validations = []

    def change_after_primary_validation(path, schema):
        problems = original(path, schema)
        assert not problems
        validations.append(schema)
        if change_descriptor and len(validations) == 1:
            sheet.write_text(f"sample,fastq_1,label,fasta\nA,{second},ref,{fasta}\n")
        return problems

    monkeypatch.setattr(orchestration.samplesheet, "validate", change_after_primary_validation)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launched.append(True))
    def run():
        return orchestration.run_pipeline(
            "inp", repo_root=root, input_path=str(sheet), outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={"references": str(sheet)},
            resume=False, demo=True, check_only=check_only, write_provenance=True,
            timeout_seconds=10)

    if not change_descriptor:
        result = run()
        assert result.checked_only is check_only
        assert len(validations) == 2
        assert bool(launched) is not check_only
        return
    with pytest.raises(NfclawError) as error:
        run()
    assert len(validations) == 2
    assert error.value.code is ErrorCode.SAMPLESHEET_INVALID
    assert not launched and not (tmp_path / "out").exists()


def test_local_input_without_a_path_format_is_still_hashed_into_provenance(tmp_path, monkeypatch):
    # mhcquant's --input has no top-level `format`, so the reference-path scan alone would skip it.
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "pattern": r"^(PXD\d{6,}|\S+\.sdrf\.tsv|\S+\.tsv)$"})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *a, **k: "")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "study.sdrf.tsv").write_text("source name\n")
    orchestration.run_pipeline(
        "inp", repo_root=root, input_path="study.sdrf.tsv", outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=False, check_only=False, write_provenance=True, timeout_seconds=None)
    hashed = (tmp_path / "out" / "provenance" / "inputs.sha256").read_text()
    assert str(tmp_path / "study.sdrf.tsv") in hashed


def test_samplesheet_data_without_a_path_format_is_hashed_into_provenance(tmp_path, monkeypatch):
    # Columns typed by pattern alone (hic, nanoseq, phaseimpute) and columns a custom parser reads
    # without declaring them (hgtseq's input1) name data the run consumes: hash them as inputs.
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "format": "file-path", "schema": "assets/schema_input.json"})
    schema = tmp_path / "pipelines/inp/upstream/assets/schema_input.json"
    data = json.loads(schema.read_text())
    data["items"]["properties"]["fastq_2"] = {"type": "string", "pattern": r"^\S+\.f(ast)?q\.gz$"}
    schema.write_text(json.dumps(data))
    files = {}
    for name in ("A_1.fastq.gz", "A_2.fastq.gz", "A_input1.fastq.gz"):
        files[name] = tmp_path / name
        files[name].write_text(name)
    sheet = tmp_path / "samples.csv"
    sheet.write_text("sample,fastq_1,fastq_2,input1\n"
                     f"A,{files['A_1.fastq.gz']},{files['A_2.fastq.gz']},{files['A_input1.fastq.gz']}\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *a, **k: "")
    orchestration.run_pipeline(
        "inp", repo_root=root, input_path=str(sheet), outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=False, check_only=False, write_provenance=True, timeout_seconds=None)
    hashed = orchestration.provenance.read_checksums(
        tmp_path / "out/provenance/inputs.sha256", relative=False)
    for path in files.values():
        assert hashed[str(path)] == orchestration.provenance.sha256_file(path)


# --- dev: running unreleased development code -------------------------------------------------

def _git(path, *args):
    return subprocess.run(["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
                           *args], check=True, capture_output=True, text=True).stdout.strip()


def _library_with_dev(tmp_path, name="mini"):
    """A real nf-core-like remote (release 1.0.0 on main, newer code on `dev`) and an nf-claw
    root whose `pipelines/<name>/upstream` is a shallow clone of the release, as in production."""
    remote = tmp_path / "remote"
    remote.mkdir()
    _git(remote, "init", "-q", "-b", "main")
    for f in ("main.nf", "nextflow.config"):
        (remote / f).write_text("x")
    shutil.copy(Path(__file__).parent / "fixtures" / name / "nextflow_schema.json",
                remote / "nextflow_schema.json")
    _git(remote, "add", ".")
    _git(remote, "commit", "-q", "-m", "release")
    release = _git(remote, "rev-parse", "HEAD")
    _git(remote, "tag", "1.0.0")
    _git(remote, "checkout", "-q", "-b", "dev")
    (remote / "main.nf").write_text("x // dev\n")
    _git(remote, "commit", "-q", "-am", "dev work")
    dev = _git(remote, "rev-parse", "HEAD")
    _git(remote, "checkout", "-q", "main")
    root = tmp_path / "lib"
    (root / "pipelines" / name).mkdir(parents=True)
    (root / ".gitmodules").write_text(
        f'[submodule "pipelines/{name}/upstream"]\n\turl = file://{remote}\n')
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--single-branch", "--branch", "main",
                    f"file://{remote}", str(root / "pipelines" / name / "upstream")],
                   check=True, capture_output=True)
    (root / "pipelines" / name / "skill.md").write_text(
        f"---\nname: {name}\nversion: 1.0.0\ncommit: {release}\n---\n")
    return root, remote, dev


# `--pipeline-version dev` fetches and materializes a real git worktree inside the run's
# budget. That budget is a hang bound, not a speed limit: on a loaded runner the git work alone
# took most of 10 seconds and one run timed out.
DEV_GIT_TIMEOUT = 300


@pytest.fixture
def dev_library(tmp_path):
    """`_library_with_dev`, plus teardown that makes git's read-only pack files removable so
    pytest's tmp cleanup never trips over them (even when the test fails)."""
    yield lambda: _library_with_dev(tmp_path)
    for p in sorted(tmp_path.rglob("*"), reverse=True):
        try:
            p.chmod(0o700)
        except OSError:
            pass


def test_dev_check_targets_the_materialized_commit_and_warns(tmp_path, monkeypatch, dev_library):
    root, _, dev = dev_library()
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    ids = tmp_path / "ids.csv"
    ids.write_text("SRR9984183\n")
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=ids, outdir=tmp_path / "out",
        profile="binac2", params_file=None, cli_overrides={}, resume=False,
        demo=False, check_only=True, write_provenance=False, timeout_seconds=DEV_GIT_TIMEOUT,
        pipeline_version="dev", nxf_ver="25.10.4")
    tree = root / "pipelines" / "mini" / ".versions" / f"dev-{dev[:12]}" / "upstream"
    assert res.command.startswith(f"nextflow run {tree.as_posix()} -profile binac2 ")
    assert (tree / "main.nf").read_text() == "x // dev\n"
    assert any("unreleased development code" in w and dev in w for w in res.warnings)
    assert not (tmp_path / "out").exists()                     # --check still leaves --outdir alone
    # the engine pin is part of the command that would run, so it is reported with it
    assert res.env == {"NXF_VER": "25.10.4"}


def test_dev_run_records_the_commit_and_replays_exactly_it(tmp_path, monkeypatch, dev_library):
    root, _, dev = dev_library()
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version",
                        lambda env_extra=None: "stub")
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=DEV_GIT_TIMEOUT,
        pipeline_version="dev")
    prov = tmp_path / "out" / "provenance"
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["version"] == "dev" and manifest["commit"] == dev
    # the replay runs the immutable tree of that commit, not whatever `dev` is by then: the bundle
    # archives that tree's tracked source and the replay extracts and runs the archive
    assert manifest["pipeline_path"].endswith(f".versions/dev-{dev[:12]}/upstream")
    assert manifest["pipeline_archive"]["files"] == len(orchestration.provenance.read_checksums(
        prov / "pipeline.sha256"))
    assert "--pipeline-source" in (prov / "commands.sh").read_text()


def test_resuming_a_dev_run_after_dev_moved_says_so(tmp_path, monkeypatch, dev_library):
    root, remote, first = dev_library()
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version",
                        lambda env_extra=None: "stub")
    kw = dict(repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
              params_file=None, cli_overrides={}, demo=True, check_only=False,
              write_provenance=True, timeout_seconds=DEV_GIT_TIMEOUT, pipeline_version="dev")
    orchestration.run_pipeline("mini", resume=False, **kw)
    same = orchestration.run_pipeline("mini", resume=True, **kw)
    assert not any("--resume continues" in w for w in same.warnings)    # dev unchanged → silent
    _git(remote, "checkout", "-q", "dev")
    (remote / "main.nf").write_text("x // dev v2\n")
    _git(remote, "commit", "-q", "-am", "more dev work")
    second = _git(remote, "rev-parse", "HEAD")
    _git(remote, "checkout", "-q", "main")
    moved = orchestration.run_pipeline("mini", resume=True, **kw)
    advisory = [w for w in moved.warnings if "--resume continues" in w]
    assert advisory and first[:12] in advisory[0] and second[:12] in advisory[0]


def test_status_notes_surface_as_run_warnings(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])

    def fake_ensure(name, version, *, pipelines_dir, repo_root):
        st = submodule.resolve_at(name, pipelines_dir / name / "upstream")
        return replace(st, notes=("stale dev head", "unreleased code"))

    monkeypatch.setattr(orchestration.versions, "ensure", fake_ensure)
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        pipeline_version="dev")
    assert res.warnings[:2] == ["stale dev head", "unreleased code"]   # said first, in order


def test_resume_advisory_tolerates_missing_or_bad_manifests(tmp_path):
    st = SubmoduleStatus("p", tmp_path, True, True, "dev", "b" * 40, ())
    out = tmp_path / "out"
    assert orchestration._resume_advisory(out, st) == []                 # no previous bundle
    (out / "provenance").mkdir(parents=True)
    manifest = out / "provenance" / "run_manifest.json"
    for text in ("not json", "[]", '{"commit": null}', '{"commit": ""}',
                 '{"commit": "' + "b" * 40 + '"}'):
        manifest.write_text(text)
        assert orchestration._resume_advisory(out, st) == [], text
    manifest.write_text('{"version": "1.0.0", "commit": "' + "a" * 40 + '"}')
    [w] = orchestration._resume_advisory(out, st)
    assert "1.0.0 (commit aaaaaaaaaaaa)" in w and "dev (commit bbbbbbbbbbbb)" in w


def test_warnings_are_emitted_before_execution(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])

    def fake_ensure(name, version, *, pipelines_dir, repo_root):
        st = submodule.resolve_at(name, pipelines_dir / name / "upstream")
        return replace(st, notes=("unreleased code",))

    events = []
    monkeypatch.setattr(orchestration.versions, "ensure", fake_ensure)

    def boom(*a, **k):
        events.append("launch")
        raise NfclawError(ErrorCode.EXECUTION_FAILED, "Nextflow exited 1")

    monkeypatch.setattr(orchestration.execution, "run", boom)
    with pytest.raises(NfclawError):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=False, timeout_seconds=10,
            pipeline_version="dev", on_warning=lambda w: events.append(w))
    assert events[0] == "unreleased code" and events[-1] == "launch"


def _check_with_params_file(root, tmp_path, params, name="inp", input_value=None):
    pf = tmp_path / "params.json"
    pf.write_text(json.dumps(params))
    return orchestration.run_pipeline(
        name, repo_root=root, input_path=input_value, outdir=tmp_path / "out",
        profile="docker", params_file=pf, cli_overrides={}, resume=False,
        demo=False, check_only=True, write_provenance=False, timeout_seconds=None)


_SAREK_LIKE_INPUT = {"type": "string", "format": "file-path", "exists": True,
                     "schema": "assets/schema_input.json"}


def test_params_file_input_false_leaves_input_unset(tmp_path, monkeypatch):
    # `input: false` in a params file is sarek's `--input false`. It reached nf-schema as a boolean,
    # which nf-schema 2.7 rejects for a string `input`; it must be left unset, as the flag is.
    root = _make_pipeline_with_input(tmp_path, _SAREK_LIKE_INPUT)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    for value in (False, "false"):
        assert "input" not in _staged_params(
            _check_with_params_file(root, tmp_path, {"input": value}))


def test_params_file_samplesheet_is_prechecked_like_the_flag(tmp_path, monkeypatch):
    # A samplesheet named in the params file skipped the pre-check `--input` gets, so a missing or
    # malformed sheet only failed once Nextflow was running.
    root = _make_pipeline_with_input(tmp_path, _SAREK_LIKE_INPUT)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(NfclawError) as exc:
        _check_with_params_file(root, tmp_path, {"input": "missing.csv"})
    assert exc.value.code == ErrorCode.SAMPLESHEET_INVALID
    (tmp_path / "ss.csv").write_text("sample\nA\n")          # missing the required fastq_1 column
    with pytest.raises(NfclawError) as exc:
        _check_with_params_file(root, tmp_path, {"input": "ss.csv"})
    assert exc.value.code == ErrorCode.SAMPLESHEET_INVALID


def test_params_file_conditional_samplesheet_is_made_absolute(tmp_path, monkeypatch):
    # mhcquant's `input` declares its path format only inside `then`, so the generic path-param
    # pass never touched a params-file value: a relative sheet stayed relative and Nextflow — which
    # nfclaw launches from --outdir — looked for it there.
    root = _make_pipeline_with_input(tmp_path, {
        "type": "string", "pattern": r"^(PXD\d{6,}|\S+\.sdrf\.tsv|\S+\.tsv)$",
        "if": {"pattern": r"\.tsv$", "not": {"pattern": r"\.sdrf\.tsv$"}},
        "then": {"format": "file-path", "exists": True, "schema": "assets/schema_input.json"}})
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reads.fq.gz").write_text("")
    (tmp_path / "ss.tsv").write_text(f"sample\tfastq_1\nA\t{tmp_path / 'reads.fq.gz'}\n")
    params = _staged_params(_check_with_params_file(root, tmp_path, {"input": "ss.tsv"}))
    assert params["input"] == str(tmp_path / "ss.tsv")
    # ...and an accession in the params file is still forwarded unchanged.
    params = _staged_params(_check_with_params_file(root, tmp_path, {"input": "PXD009752"}))
    assert params["input"] == "PXD009752"


def test_input_flag_still_wins_over_the_params_file(tmp_path, monkeypatch):
    root = _make_pipeline_with_input(tmp_path, _SAREK_LIKE_INPUT)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    # The params file names a missing sheet, but --input false replaces it: no pre-check, no input.
    res = _check_with_params_file(root, tmp_path, {"input": "missing.csv"}, input_value="false")
    assert "input" not in _staged_params(res)


def test_params_file_non_string_input_is_reported_not_crashed(tmp_path, monkeypatch):
    root = _make_pipeline_with_input(tmp_path, _SAREK_LIKE_INPUT)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(NfclawError) as exc:
        _check_with_params_file(root, tmp_path, {"input": 42})
    assert exc.value.code == ErrorCode.PARAMS_INVALID and "expects a string" in str(exc.value)


def test_provenance_failure_after_a_successful_run_is_a_clear_error(tmp_path, monkeypatch):
    # A full disk (or an unreadable result) while the bundle is written escaped as a raw OSError
    # traceback, so a run that had succeeded read as a crash with no word about its results.
    root = _make_pipeline(tmp_path, "mini")
    out = tmp_path / "out"
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run",
                        lambda *a, **k: (out / "result.txt").write_text("r"))
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *a, **k: "")

    def disk_full(path):
        raise OSError(28, "No space left on device", str(path))

    monkeypatch.setattr(orchestration.provenance, "sha256_file", disk_full)
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=out,
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    msg = str(exc.value)
    assert exc.value.code == ErrorCode.ENVIRONMENT
    assert "run succeeded" in msg and "No space left on device" in msg and "--resume" in msg
    assert (out / "result.txt").exists()


def test_outdir_that_cannot_be_created_is_a_clear_error(tmp_path, monkeypatch):
    # Preflight's writability check is advisory (root, ACLs, /proc); mkdir is the authority, and its
    # failure was a raw traceback.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    (tmp_path / "notes.txt").write_text("x")
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "notes.txt" / "out",
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    assert exc.value.code == ErrorCode.ENVIRONMENT and "could not be created" in str(exc.value)


# --- chain hooks: a stage's link to its chain, and parameters a handoff will supply later ---

def test_check_defers_parameters_a_handoff_will_supply(tmp_path, monkeypatch):
    # A chain's --check validates a later stage before the stage feeding it has produced anything:
    # its --input does not exist yet, and must count neither as missing nor as a bad samplesheet.
    root = _make_pipeline(tmp_path, "mini")          # mini requires --input
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    res = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=False, check_only=True,
        write_provenance=False, timeout_seconds=None, deferred_params=frozenset({"input"}))
    assert res.checked_only and "input" not in _staged_params(res)


def test_without_deferral_a_missing_input_is_still_reported(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError, match="missing required parameter '--input'"):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={}, resume=False, demo=False, check_only=True,
            write_provenance=False, timeout_seconds=None)


def test_deferred_params_are_only_for_check(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(ValueError):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
            write_provenance=True, timeout_seconds=None, deferred_params=frozenset({"input"}))


def test_chain_link_lands_in_the_run_manifest(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    link = {"id": "c1", "record": "/x/chain", "stage": "mini", "index": 1, "upstream": None}
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
        write_provenance=True, timeout_seconds=None, chain_link=link)
    manifest = json.loads((tmp_path / "out/provenance/run_manifest.json").read_text())
    assert manifest["chain"] == link


def _pipeline_with_auxiliary_sheet(tmp_path):
    root = _make_pipeline_with_input(tmp_path, {"type": "string"})
    up = root / "pipelines/inp/upstream"
    schema_path = up / "nextflow_schema.json"
    schema = json.loads(schema_path.read_text())
    schema["$defs"]["io"]["properties"]["references"] = {
        "type": "string", "format": "file-path", "schema": "assets/references.json"}
    schema_path.write_text(json.dumps(schema))
    (up / "assets/references.json").write_text(json.dumps({"items": {
        "properties": {"label": {"type": "string", "meta": ["id"]},
                       "fasta": {"type": "string", "format": "file-path"}},
        "required": ["label", "fasta"]}}))
    return root


@pytest.mark.parametrize("record", ["label\nA\n", "label,fasta\nA,relative.fa\n",
                                   "label,fasta\nsafe$(touch${IFS}MARKER),{fasta}\n"])
def test_auxiliary_samplesheet_is_validated_before_output_or_execution(tmp_path,
                                                                       monkeypatch, record):
    root = _pipeline_with_auxiliary_sheet(tmp_path)
    fasta = tmp_path / "reference.fa"
    fasta.write_text(">chr\nACGT\n")
    sheet = tmp_path / "references.csv"
    sheet.write_text(record.replace("{fasta}", str(fasta)))
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    called = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: called.append(True))
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline(
            "inp", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={"references": str(sheet)}, resume=False,
            demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    assert error.value.code == ErrorCode.SAMPLESHEET_INVALID
    assert not called and not (tmp_path / "out").exists()


def test_auxiliary_samplesheet_data_enters_replay_identity(tmp_path, monkeypatch, no_engine_probe):
    root = _pipeline_with_auxiliary_sheet(tmp_path)
    fasta = tmp_path / "reference.fa"
    fasta.write_bytes(b">chr\nACGT\n")
    sheet = tmp_path / "references.csv"
    sheet.write_text(f"label,fasta\nA,{fasta}\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: None)
    orchestration.run_pipeline(
        "inp", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={"references": str(sheet)}, resume=False,
        demo=True, check_only=False, write_provenance=True, timeout_seconds=10)
    checksums = (tmp_path / "out/provenance/inputs.sha256").read_text()
    assert f"{hashlib.sha256(fasta.read_bytes()).hexdigest()}  {fasta}" in checksums
    assert str(sheet) in checksums
    params = json.loads((tmp_path / "out/provenance/params.json").read_text())
    assert params["references"] == str(sheet)


def test_auxiliary_check_resolves_relative_sheet_and_leaves_output_untouched(tmp_path, monkeypatch):
    root = _pipeline_with_auxiliary_sheet(tmp_path)
    fasta = tmp_path / "reference.fa"
    fasta.write_text(">chr\nACGT\n")
    sheet = tmp_path / "references.csv"
    sheet.write_text(f"label,fasta\nA,{fasta}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    result = orchestration.run_pipeline(
        "inp", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={"references": sheet.name}, resume=False,
        demo=True, check_only=True, write_provenance=True, timeout_seconds=10)
    assert _staged_params(result)["references"] == str(sheet)
    assert not (tmp_path / "out").exists()


def test_auxiliary_chain_check_defers_future_handoff_table(tmp_path, monkeypatch):
    root = _pipeline_with_auxiliary_sheet(tmp_path)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    result = orchestration.run_pipeline(
        "inp", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={"references": str(tmp_path / "future.csv")}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=10,
        deferred_params=frozenset({"references"}))
    assert result.checked_only and not (tmp_path / "out").exists()


def _pinned_git_pipeline(tmp_path):
    """The `mini` fixture as its own git repository with two releases; skill.md pins 1.1.0."""
    root = _make_pipeline(tmp_path, "mini")
    up = root / "pipelines" / "mini" / "upstream"
    _git(up, "init", "-q")
    _git(up, "add", "-A")
    _git(up, "commit", "-qm", "1.0.0")
    _git(up, "tag", "1.0.0")
    (up / "main.nf").write_text("y")
    _git(up, "commit", "-qam", "1.1.0")
    _git(up, "tag", "1.1.0")
    pin = _git(up, "rev-parse", "HEAD")
    (root / "pipelines" / "mini" / "skill.md").write_text(
        f"---\nname: mini\nversion: 1.1.0\ncommit: {pin}\n---\n")
    return root, up


def _check_pinned(root, tmp_path, **kw):
    return orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=True,
        write_provenance=False, timeout_seconds=10, **kw)


def test_the_documented_pin_runs(tmp_path, monkeypatch):
    root, _ = _pinned_git_pipeline(tmp_path)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    assert _check_pinned(root, tmp_path).checked_only


@pytest.mark.parametrize("check_only", [False, True])
@pytest.mark.parametrize("phase", ["probe", "command"])
@pytest.mark.parametrize("change", ["commit", "dirty"])
def test_launch_source_must_still_be_the_validated_release(
        tmp_path, monkeypatch, check_only, phase, change):
    root, up = _pinned_git_pipeline(tmp_path)
    module, function = {"probe": (orchestration.plugin_compat, "check"),
                        "command": (orchestration.nextflow_command, "build")}[phase]
    original = getattr(module, function)

    def replace_source(*args, **kwargs):
        result = original(*args, **kwargs)
        if change == "commit":
            _git(up, "checkout", "-q", "1.0.0")
        else:
            (up / "main.nf").write_text("ordinary changed source")
        return result

    monkeypatch.setattr(module, function, replace_source)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launched.append(True))
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={}, resume=False, demo=True, check_only=check_only,
            write_provenance=True, timeout_seconds=10)
    assert error.value.code is ErrorCode.SUBMODULE_INCOMPLETE
    assert not launched and not (tmp_path / "out/provenance/run_manifest.json").exists()
    if phase == "probe":
        assert not (tmp_path / "out").exists()


def test_a_checkout_off_the_documented_pin_is_refused(tmp_path, monkeypatch):
    # `git pull` of nf-claw moves the pin; without `git submodule update` the old release would run
    # under the new release's docs.
    root, up = _pinned_git_pipeline(tmp_path)
    _git(up, "checkout", "-q", "1.0.0")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError) as exc:
        _check_pinned(root, tmp_path)
    assert exc.value.code is ErrorCode.SUBMODULE_INCOMPLETE
    text = str(exc.value)
    assert "checked out at 1.0.0" in text and "pins nf-core/mini 1.1.0" in text
    assert "git submodule update --force pipelines/mini/upstream" in text


def test_locally_modified_pipeline_code_is_refused(tmp_path, monkeypatch):
    root, up = _pinned_git_pipeline(tmp_path)
    (up / "main.nf").write_text("patched")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError, match="local modifications to tracked pipeline files"):
        _check_pinned(root, tmp_path)
    # Untracked files (e.g. a stray .nextflow/ from a manual run) do not change the code.
    (up / "main.nf").write_text("y")
    (up / "notes.txt").write_text("scratch")
    assert _check_pinned(root, tmp_path).checked_only


def test_modified_file_listing_handles_renames(tmp_path):
    root, up = _pinned_git_pipeline(tmp_path)
    _git(up, "mv", "main.nf", "renamed.nf")
    assert submodule.modified_files(up) == ["renamed.nf"]


@pytest.mark.parametrize("engine", ["23.10.1", "24.03.0-edge"])
def test_resource_limits_refused_on_an_engine_that_would_ignore_them(tmp_path, monkeypatch, engine):
    # Verified on Nextflow 23.10.1: process.resourceLimits is accepted silently and a 16-CPU/64 GB
    # request runs uncapped. A ceiling the engine will not apply must not be reported as applied.
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={}, resume=False, demo=True, check_only=True,
            write_provenance=False, timeout_seconds=10, nxf_ver=engine,
            limits=resources.parse(2, "4.GB", None))
    assert exc.value.code is ErrorCode.PARAMS_INVALID
    assert "24.04.0" in exc.value.message and engine.split("-")[0] in exc.value.message


def test_resource_limits_on_the_installed_engine_are_judged_by_its_version(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    kwargs = dict(repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
                  params_file=None, cli_overrides={}, resume=False, demo=True, check_only=True,
                  write_provenance=False, timeout_seconds=10,
                  limits=resources.parse(None, "4.GB", None))
    monkeypatch.setattr(orchestration.engine_version, "_installed_raw",
                        lambda: "nextflow version 23.04.0 build 5857")
    with pytest.raises(NfclawError, match="Nextflow 23.04.0"):
        orchestration.run_pipeline("mini", **kwargs)
    monkeypatch.setattr(orchestration.engine_version, "_installed_raw",
                        lambda: "nextflow version 24.04.0 build 5917")
    res = orchestration.run_pipeline("mini", **kwargs)
    assert "resource_limits.config" in res.command
    assert not any("could not be determined" in w for w in res.warnings)
    # An engine that cannot be identified is not assumed to enforce the ceiling: the run says so.
    monkeypatch.setattr(orchestration.engine_version, "_installed_raw", lambda: None)
    with pytest.raises(NfclawError, match="could not be determined"):
        orchestration.run_pipeline("mini", **kwargs)


def test_preplanned_tree_cannot_run_a_different_clean_commit(tmp_path, monkeypatch):
    root, up = _pinned_git_pipeline(tmp_path)
    planned = submodule.resolve("mini", root / "pipelines")
    _git(up, "checkout", "-q", "1.0.0")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError, match="pipeline code"):
        _check_pinned(root, tmp_path, resolved_tree=planned)


def test_preplanned_git_identity_must_still_be_verifiable(tmp_path, monkeypatch):
    root, _ = _pinned_git_pipeline(tmp_path)
    planned = submodule.resolve("mini", root / "pipelines")
    monkeypatch.setattr(submodule, "_git", lambda *a: "")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    with pytest.raises(NfclawError, match="pipeline code"):
        _check_pinned(root, tmp_path, resolved_tree=planned)


def test_unidentified_engine_cannot_launch_with_a_requested_resource_ceiling(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.engine_version, "_installed_raw", lambda: None)
    launches = []
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: launches.append(a))
    with pytest.raises(NfclawError, match="version could not be determined"):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
            write_provenance=False, timeout_seconds=10, limits=resources.parse(2, None, None))
    assert not launches and not (tmp_path / "out").exists()


def test_a_stub_test_profile_is_announced_and_reported_as_a_caveat(tmp_path, monkeypatch):
    # proteinfold 2.0.0's test profile sets `stubRun = true`: --demo "succeeded" with every output
    # an empty placeholder, and nothing said the run had computed nothing.
    root = _make_pipeline(tmp_path, "mini")
    up = root / "pipelines/mini/upstream"
    (up / "nextflow.config").write_text("profiles { test { includeConfig 'conf/test.config' } }\n")
    (up / "conf").mkdir()
    (up / "conf/test.config").write_text("stubRun = true\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched, shown = [], []

    def run(*args, **kwargs):
        launched.append(len(shown))
        kwargs["run_log"].write(b"-[nf-core/mini] Pipeline completed successfully-\n")

    monkeypatch.setattr(orchestration.execution, "run", run)
    out = tmp_path / "out"
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=out, profile="docker", params_file=None,
        cli_overrides={}, resume=False, demo=True, check_only=False, write_provenance=True,
        timeout_seconds=10, on_warning=shown.append)
    assert any("stubRun = true" in w for w in shown[:launched[0]])      # said before launch
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["stub_profiles"] == ["test"]
    assert any(c.startswith("stub run:") for c in manifest["completion_caveats"])
    state = runlog.read_state(out / "provenance/logs/run.log")
    assert state.state == "success"
    assert any(c.startswith("stub run:") for c in state.caveats)



def test_a_config_that_runs_stubs_is_announced_and_reported_as_a_caveat(tmp_path, monkeypatch):
    # `stubRun = true` in a `--config` file stubs every task just as a test profile can, so the
    # run must not report a plain success either.
    root = _make_pipeline(tmp_path, "mini")
    stub = tmp_path / "stub.config"
    stub.write_text("stubRun = true\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched, shown = [], []

    def run(*args, **kwargs):
        launched.append(len(shown))
        kwargs["run_log"].write(b"-[nf-core/mini] Pipeline completed successfully-\n")

    monkeypatch.setattr(orchestration.execution, "run", run)
    out = tmp_path / "out"
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=out, profile="docker", params_file=None,
        cli_overrides={}, resume=False, demo=False, check_only=False, write_provenance=True,
        timeout_seconds=10, on_warning=shown.append, configs=[str(stub)])
    assert any("`stub.config`" in w and "stubRun = true" in w for w in shown[:launched[0]])
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["stub_configs"] == ["stub.config"]
    assert "stub_profiles" not in manifest
    assert any(c.startswith("stub run: the `stub.config` config")
               for c in manifest["completion_caveats"])
    state = runlog.read_state(out / "provenance/logs/run.log")
    assert state.state == "success"
    assert any(c.startswith("stub run:") for c in state.caveats)

def test_a_non_stub_demo_reports_no_stub_caveat(tmp_path, monkeypatch):
    root = _make_pipeline(tmp_path, "mini")
    up = root / "pipelines/mini/upstream"
    (up / "nextflow.config").write_text("profiles { test { includeConfig 'conf/test.config' } }\n")
    (up / "conf").mkdir()
    (up / "conf/test.config").write_text("params { input = 'x' }\n")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **k: k["run_log"].write(
        b"-[nf-core/mini] Pipeline completed successfully-\n"))
    shown = []
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
        write_provenance=True, timeout_seconds=10, on_warning=shown.append)
    # Other diagnostics can legitimately name this test's "non_stub" output path.
    # Reject an actual stub completion caveat, not an unrelated substring in a filename.
    assert not any(w.startswith("the pipeline completed but reported: stub run:") for w in shown)
    manifest = json.loads((tmp_path / "out/provenance/run_manifest.json").read_text())
    assert "stub_profiles" not in manifest and "stub_configs" not in manifest
    assert not manifest.get("completion_caveats")


@pytest.mark.parametrize("java,refused", [(17, True), (21, True), (11, False), (None, False)])
def test_an_engine_too_old_for_nextflows_java_is_refused_before_launch(tmp_path, monkeypatch, java,
                                                                       refused):
    root = _make_pipeline(tmp_path, "mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    monkeypatch.setattr(orchestration.engine_version, "java_major_for_nextflow", lambda env: java)
    def run():
        return orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="docker",
            params_file=None, cli_overrides={}, resume=False, demo=True, check_only=True,
            write_provenance=False, timeout_seconds=10, nxf_ver="21.04.0")
    if refused:
        with pytest.raises(NfclawError, match="21.10.0") as error:
            run()
        assert error.value.code == ErrorCode.ENVIRONMENT
        assert not (tmp_path / "out").exists()
    else:
        assert run().checked_only
