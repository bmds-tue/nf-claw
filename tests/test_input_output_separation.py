"""Filesystem and execution oracles for input data separated from execution writes."""
import json
import os
import tempfile

import pytest

from runner import chain, cli, input_safety, locking, orchestration, runlog
from runner.errors import NfclawError


@pytest.mark.parametrize("name", ["NXF_HOME", "NXF_DIST", "NXF_TEMP", "CAPSULE_CACHE_DIR"])
@pytest.mark.parametrize("inherited", [False, True])
def test_engine_cache_writes_are_separated_before_version_probes(tmp_path, monkeypatch, name, inherited):
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "index.bin").write_bytes(b"fixed scientific input")
    cache = data / "engine_cache"
    overlay = {name: str(cache)}
    if inherited:
        monkeypatch.setenv(name, str(cache))
        overlay = {}
    monkeypatch.setattr(orchestration.engine_version, "_installed_raw",
                        lambda: pytest.fail("engine version probe ran before cache boundary validation"))
    monkeypatch.setattr(orchestration.execution, "run", lambda *_, **__: pytest.fail("engine launched"))
    before = (data.stat().st_mtime_ns, orchestration.provenance.snapshot_inputs([data]))
    with pytest.raises(NfclawError, match="overlaps local dependency") as error:
        run(root, data, tmp_path / "results", nxf_env=overlay, nxf_ver=None,
            limits=orchestration.resources.parse(2, None, None))
    assert error.value.details["unsafe_write_boundary"]
    assert (data.stat().st_mtime_ns, orchestration.provenance.snapshot_inputs([data])) == before


def test_safe_engine_cache_permits_version_checks_without_changing_inputs(tmp_path, monkeypatch):
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "index.bin").write_bytes(b"fixed scientific input")
    probes = []
    monkeypatch.setattr(orchestration.engine_version, "_installed_raw",
                        lambda: probes.append(True) or "nextflow version 25.10.4")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **_: [])
    before = (data.stat().st_mtime_ns, orchestration.provenance.snapshot_inputs([data]))
    checked = run(root, data, tmp_path / "results", check_only=True, nxf_ver=None,
                  nxf_env={"NXF_HOME": str(tmp_path / "engine_cache")},
                  limits=orchestration.resources.parse(2, None, None))
    assert checked.checked_only and probes and "resource_limits.config" in checked.command
    assert (data.stat().st_mtime_ns, orchestration.provenance.snapshot_inputs([data])) == before


def test_relative_engine_cache_is_checked_from_the_execution_directory(tmp_path, monkeypatch):
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    out = tmp_path / "results"
    monkeypatch.setattr(orchestration.execution, "run", lambda *_, **__: pytest.fail("engine launched"))
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        run(root, data, out, nxf_env={"NXF_HOME": os.path.relpath(data / "cache", out)})
    assert not (data / "cache").exists() and not out.exists()


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
@pytest.mark.parametrize("alias", [False, True])
def test_audited_output_only_destinations_cannot_write_into_inputs(tmp_path, monkeypatch, check_only, alias):
    root = tree(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    source = data / "index.bin"
    source.write_bytes(b"fixed scientific input")
    destination = data / "cache"
    if alias:
        link = tmp_path / "destination_alias"
        link.symlink_to(data, target_is_directory=True)
        destination = link / "cache"
    monkeypatch.setattr(orchestration.path_roles, "output_only_directories",
                        lambda *args: frozenset({"future_cache"}))
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *args, **kwargs: pytest.fail("engine launched"))
    before = data.stat().st_mtime_ns
    out = tmp_path / "out"
    with pytest.raises(NfclawError, match="overlaps local dependency") as error:
        run(root, data, out, check_only=check_only, cli_overrides={"future_cache": str(destination)})
    assert error.value.details["unsafe_write_boundary"]
    assert source.read_bytes() == b"fixed scientific input"
    assert data.stat().st_mtime_ns == before
    assert not destination.exists() and not out.exists()
    assert not (tmp_path / ".out.nfclaw.lock").exists()


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


@pytest.mark.parametrize("alias", ["final", "parent"])
def test_a_logical_input_slot_inside_outputs_is_protected_when_its_target_is_external(tmp_path, alias):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    out.mkdir()
    if alias == "final":
        supplied = out / "reads.fastq"
        supplied.symlink_to(source)
    else:
        (out / "data").symlink_to(data, target_is_directory=True)
        supplied = out / "data/reads.fastq"
    before = out.stat().st_mtime_ns
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([supplied], [("outputs", out, True)])
    assert source.read_bytes() == b"fixed scientific input"
    assert out.stat().st_mtime_ns == before


@pytest.mark.parametrize("nested", [False, True])
def test_execution_files_cannot_share_a_hardlinked_input_inode(tmp_path, nested):
    source = tmp_path / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    destination = tmp_path / "out/provenance/logs/run.log"
    destination.parent.mkdir(parents=True)
    os.link(source, destination)
    writer = destination.parents[2] if nested else destination
    before = (source.stat().st_mtime_ns, source.read_bytes())
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([source], [("outputs", writer, True)])
    assert (source.stat().st_mtime_ns, source.read_bytes()) == before


def test_nested_output_directory_alias_cannot_reach_an_external_input_tree(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    out.mkdir()
    (out / "publication").symlink_to(data, target_is_directory=True)
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([source], [("outputs", out, True)])
    assert source.read_bytes() == b"fixed scientific input"


@pytest.mark.parametrize("alias", ["file", "directory"])
def test_declared_task_work_aliases_remain_readable_for_a_resume(tmp_path, alias):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    work = out / "work"
    work.mkdir(parents=True)
    staged = work / "staged"
    staged.symlink_to(source if alias == "file" else data, target_is_directory=alias == "directory")
    input_safety.check_write_boundaries([data], [("outputs", out, True), ("work", work, False)])
    assert source.read_bytes() == b"fixed scientific input"


def test_directory_aliases_and_hardlinks_to_unconsumed_data_are_not_refused(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    unrelated = tmp_path / "other.fastq"
    unrelated.write_bytes(b"other data")
    out = tmp_path / "out"
    out.mkdir()
    os.link(unrelated, out / "other.fastq")
    (out / "cycle").symlink_to(out, target_is_directory=True)
    input_safety.check_write_boundaries([source], [("outputs", out, True)])


def test_a_broad_staging_directory_does_not_disable_output_alias_checks(tmp_path):
    source = tmp_path / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    out.mkdir()
    os.link(source, out / "reads.fastq")
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([source], [
            ("outputs", out, True), ("check staging directory", tmp_path, False)])


def test_an_output_alias_into_an_external_cache_is_still_a_write_boundary(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    source = cache / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    out = tmp_path / "out"
    out.mkdir()
    (out / "publication").symlink_to(cache, target_is_directory=True)
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([source], [
            ("outputs", out, True), ("engine cache", cache, False)])


def test_missing_logical_slots_are_protected_through_parent_aliases(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    route = tmp_path / "route"
    route.symlink_to(tmp_path, target_is_directory=True)
    (out / "data").symlink_to(data, target_is_directory=True)
    supplied = route / "out/data/missing.fastq"
    with pytest.raises(NfclawError, match="overlaps local dependency"):
        input_safety.check_write_boundaries([supplied], [("outputs", out, True)])
    assert not supplied.exists()


def test_refusal_log_cannot_append_to_a_hardlinked_scientific_input(tmp_path):
    source = tmp_path / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    log = tmp_path / "out/provenance/logs/run.log"
    log.parent.mkdir(parents=True)
    os.link(source, log)
    runlog.record_unlaunched(log, command="nfclaw run fixture", outcome="refused", error="bad flag")
    assert source.read_bytes() == b"fixed scientific input"
    assert not (tmp_path / ".out.nfclaw.lock").exists()


def test_check_staging_cannot_create_files_in_a_consumed_directory(tmp_path, monkeypatch):
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
    monkeypatch.setattr(chain.preflight, "outdir_issue", lambda *_, **__: None)
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
