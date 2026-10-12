"""Filesystem and execution oracles for input data separated from execution writes."""
import json

import pytest

from runner import chain, cli, input_safety, locking, orchestration, runlog
from runner.errors import NfclawError


def tree(tmp_path, *, table=False):
    root = tmp_path / "library"
    upstream = root / "pipelines/fixture/upstream"
    upstream.mkdir(parents=True)
    (upstream.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    props = {"input": {"type": "string", "format": "file-path" if table else "directory-path",
                       "exists": True},
             "outdir": {"type": "string", "format": "directory-path"},
             "reference": {"type": "string", "format": "directory-path", "exists": True},
             "future_cache": {"type": "string", "format": "directory-path"}}
    if table:
        props["input"]["schema"] = "assets/schema_input.json"
        (upstream / "assets").mkdir()
        (upstream / "assets/schema_input.json").write_text(json.dumps({"items": {
            "properties": {"sample": {"type": "string"},
                           "reference": {"type": "string", "format": "directory-path"}},
            "required": ["sample", "reference"]}}))
    (upstream / "nextflow_schema.json").write_text(json.dumps({"properties": props}))
    (upstream / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    (upstream / "main.nf").write_text('''process INVENTORY {
 publishDir params.outdir, mode: 'copy'
 input:
 path data
 output:
 path 'entries.txt'
 script:
 """
 find -L ${data} -mindepth 1 -maxdepth 1 -print | sed 's#^.*/##' | LC_ALL=C sort > entries.txt
 """
}
workflow { INVENTORY(file(params.input)) }
''')
    return root


def run(root, data, out, **kwargs):
    options = dict(repo_root=root, input_path=data, outdir=out, profile="", params_file=None,
                   cli_overrides={}, resume=False, demo=False, check_only=False,
                   write_provenance=True, timeout_seconds=60, nxf_ver="25.10.4")
    options.update(kwargs)
    return orchestration.run_pipeline("fixture", **options)


@pytest.mark.parametrize("check_only", [False, True])
@pytest.mark.parametrize("write_provenance", [False, True])
@pytest.mark.parametrize("source", ["input", "params_file", "auxiliary", "samplesheet", "nested_alias"])
def test_overlapping_outputs_are_refused_without_changing_the_data(
        tmp_path, monkeypatch, check_only, write_provenance, source):
    root = tree(tmp_path, table=source == "samplesheet")
    data = tmp_path / "data"
    data.mkdir()
    (data / "index.bin").write_bytes(b"fixed scientific input")
    supplied = data
    options = {"check_only": check_only, "write_provenance": write_provenance}
    if source == "params_file":
        params = tmp_path / "params.json"
        params.write_text(json.dumps({"input": str(data)}))
        supplied = None
        options["params_file"] = params
    elif source == "auxiliary":
        supplied = tmp_path / "other"
        supplied.mkdir()
        options["cli_overrides"] = {"reference": str(data)}
    elif source == "samplesheet":
        supplied = tmp_path / "samples.csv"
        supplied.write_text(f"sample,reference\nS,{data}\n")
    elif source == "nested_alias":
        supplied = tmp_path / "other"
        supplied.mkdir()
        (supplied / "reference").symlink_to(data, target_is_directory=True)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **_: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *_, **__: pytest.fail("engine launched"))
    before = (data.stat().st_mtime_ns, sorted(p.name for p in data.iterdir()))
    with pytest.raises(NfclawError, match="overlaps local dependency") as error:
        run(root, supplied, data / "analysis", **options)
    assert error.value.details["unsafe_write_boundary"]
    assert (data.stat().st_mtime_ns, sorted(p.name for p in data.iterdir())) == before
    assert (data / "index.bin").read_bytes() == b"fixed scientific input"
    assert not (data / "analysis").exists() and not (data / ".analysis.nfclaw.lock").exists()


@pytest.mark.parametrize("destination", ["work", "log", "provenance", "params", "engine_state"])
def test_redirected_execution_writes_cannot_modify_inputs(tmp_path, monkeypatch, destination):
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "index.bin").write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    options = {}
    if destination == "work":
        options["nxf_env"] = {"NXF_WORK": str(data / "work")}
    elif destination == "log":
        options["nxf_env"] = {"NXF_LOG_FILE": str(data / "engine.log")}
    else:
        out.mkdir()
        options["resume"] = True
        if destination == "provenance":
            (out / "provenance").symlink_to(data, target_is_directory=True)
        elif destination == "engine_state":
            (out / ".nextflow").symlink_to(data, target_is_directory=True)
        else:
            (out / "provenance").mkdir()
            (out / "provenance/params.json").symlink_to(data / "index.bin")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **_: [])
    before = data.stat().st_mtime_ns
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        run(root, data, out, **options)
    assert (data / "index.bin").read_bytes() == b"fixed scientific input"
    assert sorted(p.name for p in data.iterdir()) == ["index.bin"]
    assert data.stat().st_mtime_ns == before and not (tmp_path / ".out.nfclaw.lock").exists()


def test_globbed_directory_aliases_are_inspected(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "selected").symlink_to(data, target_is_directory=True)
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([tmp_path / "select*"], [("outputs", data / "out", True)])


def test_input_files_inside_a_publication_tree_are_refused(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    data = output / "sample.fastq"
    data.write_bytes(b"fixed scientific input")
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([data], [("outputs", output, True)])
    assert data.read_bytes() == b"fixed scientific input"


def test_check_staging_cannot_create_files_in_a_consumed_directory(tmp_path, monkeypatch):
    import tempfile
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(data))
    with pytest.raises(NfclawError, match="check staging directory"):
        run(root, data, tmp_path / "out", check_only=True)
    assert list(data.iterdir()) == []


@pytest.mark.parametrize("dependency_kind", ["pipeline", "config", "params_file"])
def test_output_tree_cannot_contain_code_or_configuration(tmp_path, monkeypatch, dependency_kind):
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    options = {"resume": True}
    if dependency_kind == "pipeline":
        out = root / "pipelines/fixture/upstream"
    elif dependency_kind == "config":
        config = out / "custom.config"
        config.write_text("params.safe = true\n")
        options["configs"] = (str(config),)
    else:
        params = out / "original_params.json"
        params.write_text("{}")
        options["params_file"] = params
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **_: [])
    before = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        run(root, data, out, **options)
    assert {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()} == before
    assert not (out.parent / f".{out.name}.nfclaw.lock").exists()


def test_cached_task_results_and_absent_optional_destinations_remain_usable(tmp_path, monkeypatch):
    root = tree(tmp_path)
    work = tmp_path / "work"
    reference = work / "previous_task" / "reference"
    reference.mkdir(parents=True)
    (reference / "index.bin").write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **_: [])
    checked = run(root, reference, out, check_only=True,
                  cli_overrides={"future_cache": str(out / "future")}, nxf_env={"NXF_WORK": str(work)})
    assert checked.checked_only and not out.exists()
    assert reference in checked.local_dependencies
    assert (reference / "index.bin").read_bytes() == b"fixed scientific input"


@pytest.mark.parametrize("check_only", [False, True])
def test_chain_checks_its_record_directory_before_writing_it(tmp_path, monkeypatch, check_only):
    root = tree(tmp_path)
    out = tmp_path / "analysis"
    # The stage's directory is a sibling of this input; only the chain-level write check sees it.
    source = out / "chain"
    source.mkdir(parents=True)
    (source / "index.bin").write_bytes(b"fixed scientific input")
    spec = chain.parse_spec({"profile": "standard", "nxf_ver": "25.10.4", "stages": [
        {"pipeline": "fixture", "input": str(source)}]})
    monkeypatch.setattr(chain.preflight, "_outdir_issue", lambda *_, **__: None)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **_: [])
    monkeypatch.setattr(chain, "_probe_config", lambda *_, **__: pytest.fail("engine probe before refusal"))
    before = source.stat().st_mtime_ns
    with pytest.raises(NfclawError, match="chain --outdir"):
        chain.run_chain(spec, repo_root=root, outdir=out, check_only=check_only)
    assert sorted(p.name for p in source.iterdir()) == ["index.bin"]
    assert source.stat().st_mtime_ns == before and not (source / ".lock").exists()


def test_refused_attempt_cannot_append_markers_to_an_active_writer(tmp_path):
    if locking.fcntl is None:
        pytest.skip("requires POSIX flock")
    log = tmp_path / "out/provenance/logs/run.log"
    log.parent.mkdir(parents=True)
    log.write_text("active writer's original bytes\n")
    with locking.output_writer(tmp_path / "out"):
        runlog.record_unlaunched(log, command="nfclaw run fixture", outcome="refused", error="bad flag")
    assert log.read_text() == "active writer's original bytes\n"


@pytest.mark.parametrize("alias", ["file", "parent"])
def test_refusal_log_cannot_follow_an_external_symlink(tmp_path, alias):
    original = tmp_path / "source_data"
    original.mkdir()
    data = original / "run.log"
    data.write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    if alias == "parent":
        (out / "provenance").mkdir(parents=True)
        (out / "provenance/logs").symlink_to(original, target_is_directory=True)
    else:
        (out / "provenance/logs").mkdir(parents=True)
        (out / "provenance/logs/run.log").symlink_to(data)
    runlog.record_unlaunched(out / "provenance/logs/run.log", command="nfclaw run fixture",
                            outcome="refused", error="bad flag")
    assert data.read_bytes() == b"fixed scientific input"
    assert not (tmp_path / ".out.nfclaw.lock").exists()


def test_cli_boundary_refusal_preserves_an_existing_log_and_input_inventory(tmp_path, monkeypatch):
    root = tree(tmp_path)
    data = tmp_path / "data"
    out = data / "out"
    log = out / "provenance/logs/run.log"
    log.parent.mkdir(parents=True)
    log.write_text("historical analysis record\n")
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["run", "fixture", "--input", str(data), "--outdir", str(out), "--resume"]) == 1
    assert log.read_text() == "historical analysis record\n"
    assert not (data / ".out.nfclaw.lock").exists()
