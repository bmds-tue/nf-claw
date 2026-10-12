# ruff: noqa: F811
import json
from dataclasses import replace

import pytest

from runner import chain, handoff
from runner.errors import ErrorCode, NfclawError
from test_chain import RULE, _boom, _spec, fake_runs  # noqa: F401
from test_handoff import DIRECT, FASTQS, SHEET, _rule, _trees


@pytest.mark.parametrize("relative", ["samplesheet/samplesheet.csv", "fastq/A_1.fastq.gz"])
def test_handoff_refuses_a_source_changed_after_upstream_success(
        library, finished_run, tmp_path, relative):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {"samplesheet/samplesheet.csv": SHEET, **FASTQS})
    source = up / relative
    source.write_text(source.read_text().replace('"A"', '"B"') if relative.endswith(".csv")
                      else "changed reads")
    with pytest.raises(NfclawError) as err:
        handoff.materialize(_rule(DIRECT), upstream_outdir=up, downstream_tree=down,
                            dest=tmp_path / "handoff")
    assert err.value.code is ErrorCode.HANDOFF_FAILED
    assert relative in str(err.value)


def test_handoff_refuses_an_unrecorded_matching_output(library, finished_run, tmp_path):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {})
    (up / "counts.tsv").write_text("new,unrecorded,data\n")
    with pytest.raises(NfclawError) as err:
        handoff.materialize(_rule({"params": {"fasta": {"file": "counts.tsv"}}}),
                            upstream_outdir=up, downstream_tree=down, dest=tmp_path / "handoff")
    assert err.value.code is ErrorCode.HANDOFF_FAILED
    assert "counts.tsv" in str(err.value)


@pytest.mark.parametrize("contents", [None, "not-a-digest  counts.tsv\n"])
def test_handoff_refuses_missing_or_malformed_output_checksums(
        library, finished_run, tmp_path, contents):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {"counts.tsv": "original\n"})
    index = up / "provenance" / "outputs.sha256"
    index.unlink() if contents is None else index.write_text(contents)
    with pytest.raises(NfclawError) as err:
        handoff.materialize(_rule({"params": {"fasta": {"file": "counts.tsv"}}}),
                            upstream_outdir=up, downstream_tree=down, dest=tmp_path / "handoff")
    assert err.value.code is ErrorCode.HANDOFF_FAILED


@pytest.mark.parametrize("relative", ["samplesheet/samplesheet.csv", "fastq/A_1.fastq.gz"])
def test_status_detects_changed_upstream_artifacts(library, fake_runs, tmp_path, relative):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    (out / "01-mini_up" / relative).write_text("changed after success\n")
    state, problems = chain.status(out)
    assert any(relative in problem for problem in problems)
    assert chain.status_exit_code(state, problems) == 1


def test_resume_refuses_changed_frozen_upstream_outputs_before_downstream(
        library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    (out / "01-mini_up" / "fastq/A_1.fastq.gz").write_text("modified reads")
    with pytest.raises(NfclawError) as err:
        chain.run_chain(None, repo_root=root, outdir=out, resume=True)
    assert "fastq/A_1.fastq.gz" in str(err.value)
    state, problems = chain.status(out)
    assert chain.status_exit_code(state, problems) == 1


@pytest.mark.parametrize("stage", ["01-mini_up", "02-mini"])
def test_status_refuses_a_successful_stage_without_its_manifest(
        library, fake_runs, tmp_path, stage):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    (out / stage / "provenance" / "run_manifest.json").unlink()
    state, problems = chain.status(out)
    assert problems
    assert chain.status_exit_code(state, problems) == 1


def test_status_refuses_a_stage_manifest_that_reports_failure(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    path = out / "01-mini_up" / "provenance" / "run_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["outcome"] = "failed"
    path.write_text(json.dumps(manifest))
    state, problems = chain.status(out)
    assert problems
    assert chain.status_exit_code(state, problems) == 1


def test_explicit_input_override_has_truthful_lineage(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    mine = tmp_path / "mine.csv"
    mine.write_text("sample,fastq_1\nA,/external/A.fastq.gz\n")
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                        {"pipeline": "mini", "input": str(mine)}]})
    out = tmp_path / "chain"
    chain.run_chain(spec, repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert problems == []
    assert chain.status_exit_code(state, problems) == 0
    record = json.loads((out / "chain/handoffs/02-mini/handoff.json").read_text())
    assert "input" not in record["params"]


def test_explicit_input_override_can_replace_an_unavailable_handoff(
        library, fake_runs, tmp_path):
    unavailable = {**RULE, "params": {"input": {"samplesheet": "absent.csv",
                                                "provides": ["sample", "fastq_1"]}}}
    root = library("mini_up", "mini", rules={("mini_up", "mini"): unavailable})
    mine = tmp_path / "mine.csv"
    mine.write_text("sample,fastq_1\nA,/external/A.fastq.gz\n")
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                        {"pipeline": "mini", "input": str(mine)}]})
    result = chain.run_chain(spec, repo_root=root, outdir=tmp_path / "chain")
    assert result.outcome == "success"


@pytest.mark.parametrize("change", [
    {"profile": "singularity"}, {"nxf_ver": "25.10.4"},
    {"nxf_env": {"NXF_OFFLINE": "true"}}, {"limits": {"cpus": 2}},
])
def test_resume_refuses_changed_run_options_of_a_succeeded_stage(
        library, fake_runs, tmp_path, change):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    changed = chain.parse_spec({"stages": [
        {"pipeline": "mini_up", "input": "/data/ids.csv", **change},
        {"pipeline": "mini", "params": {"aligner": "hisat2"}}]})
    with pytest.raises(NfclawError, match="already succeeded with a different definition"):
        chain.run_chain(changed, repo_root=root, outdir=out, resume=True)


def test_resume_refuses_a_changed_resolved_pipeline_commit(
        library, fake_runs, tmp_path, monkeypatch):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    original = chain.versions.ensure
    commit = "a" * 40

    def resolved(name, *args, **kwargs):
        tree = original(name, *args, **kwargs)
        return replace(tree, commit=commit) if name == "mini_up" else tree

    monkeypatch.setattr(chain.versions, "ensure", resolved)
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    commit = "b" * 40
    with pytest.raises(NfclawError, match="already succeeded with a different definition"):
        chain.run_chain(None, repo_root=root, outdir=out, resume=True)


def test_resume_refuses_a_changed_extra_config(library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    config = tmp_path / "custom.config"
    config.write_text("params.aligner = 'star'\n")
    spec = _spec(config=[str(config)])
    out = tmp_path / "chain"
    with pytest.raises(NfclawError):
        chain.run_chain(spec, repo_root=root, outdir=out)
    config.write_text("params.aligner = 'hisat2'\n")
    with pytest.raises(NfclawError, match="already succeeded with a different definition"):
        chain.run_chain(None, repo_root=root, outdir=out, resume=True)


def test_timeout_budget_includes_validation_before_launch(
        library, fake_runs, tmp_path, monkeypatch):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    monotonic = 0.0
    check = chain._check

    def slow_validation(*args, **kwargs):
        nonlocal monotonic
        result = check(*args, **kwargs)
        monotonic = 10.0
        return result

    monkeypatch.setattr(chain.time, "monotonic", lambda: monotonic)
    monkeypatch.setattr(chain, "_check", slow_validation)
    with pytest.raises(NfclawError) as err:
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "chain", timeout_seconds=5)
    assert err.value.details.get("timeout_seconds") == 5


@pytest.mark.parametrize("malformed", [[1], {"params": []}, {"params": {"input": 1}}])
def test_malformed_handoff_records_report_broken_lineage(
        library, fake_runs, tmp_path, malformed):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    (out / "chain/handoffs/02-mini/handoff.json").write_text(json.dumps(malformed))
    state, problems = chain.status(out)
    assert problems
    assert chain.status_exit_code(state, problems) == 1


def test_resume_refuses_a_legacy_fingerprint_without_immutable_evidence(
        library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    path = out / "chain/state.json"
    state = json.loads(path.read_text())
    for entry in state["stages"]:
        entry.pop("fingerprint_version", None)
    path.write_text(json.dumps(state))
    with pytest.raises(NfclawError, match="older fingerprint format"):
        chain.run_chain(None, repo_root=root, outdir=out, resume=True)


def test_status_rejects_a_stage_manifest_belonging_to_another_chain(
        library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    path = out / "01-mini_up/provenance/run_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["chain"]["id"] = "different-chain"
    path.write_text(json.dumps(manifest))
    state, problems = chain.status(out)
    assert problems
    assert chain.status_exit_code(state, problems) == 1


@pytest.mark.parametrize("malformed", [{"stages": []}, {"stages": [1]}, {"stages": {}}])
def test_malformed_chain_state_reports_a_readable_failure(library, fake_runs, tmp_path, malformed):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    path = out / "chain/state.json"
    path.write_text(json.dumps({"outcome": "success", **malformed}))
    state, problems = chain.status(out)
    assert "lineage: BROKEN" in chain.format_status(state, problems)
    assert chain.status_exit_code(state, problems) == 1


def test_stale_resume_state_is_reread_after_acquiring_the_lock(library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    stale = json.loads((out / "chain/state.json").read_text())
    chain.run_chain(None, repo_root=root, outdir=out, resume=True)
    spec = _spec()
    completed_launches = len(fake_runs.calls)
    result = chain._execute(spec, chain.plan(spec, repo_root=root), stale, repo_root=root,
                            outdir=out, timeout_seconds=None, on_warning=None)
    assert len(result.stages[1]["attempts"]) == 2
    assert len(fake_runs.calls) == completed_launches


def test_a_concurrent_fresh_chain_cannot_overwrite_an_existing_record(
        library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    spec = _spec()
    before = (out / "chain/state.json").read_bytes()
    with pytest.raises(NfclawError):
        chain._execute(spec, chain.plan(spec, repo_root=root), None, repo_root=root,
                       outdir=out, timeout_seconds=None, on_warning=None)
    assert (out / "chain/state.json").read_bytes() == before


def test_stages_use_the_commit_resolved_before_checks_even_if_dev_moves(
        library, fake_runs, tmp_path, monkeypatch):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    ensure = chain.versions.ensure
    launch = chain.orchestration.run_pipeline
    current_commit = "a" * 40

    def resolve(name, *args, **kw):
        return replace(ensure(name, *args, **kw), commit=current_commit)

    def dev_moved(spec, p, **kw):
        nonlocal current_commit
        current_commit = "b" * 40
        return []

    def execute_resolved(name, **kw):
        result = launch(name, **kw)
        if not kw["check_only"]:
            tree = kw.get("resolved_tree") or resolve(name, kw.get("pipeline_version"),
                                                     pipelines_dir=root / "pipelines", repo_root=root)
            path = kw["outdir"] / "provenance/run_manifest.json"
            manifest = json.loads(path.read_text())
            manifest["commit"] = tree.commit
            path.write_text(json.dumps(manifest))
        return result

    monkeypatch.setattr(chain.versions, "ensure", resolve)
    monkeypatch.setattr(chain, "_probe_config", dev_moved)
    monkeypatch.setattr(chain.orchestration, "run_pipeline", execute_resolved)
    result = chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "chain")
    assert [entry["commit"] for entry in result.stages] == ["a" * 40, "a" * 40]


@pytest.mark.parametrize("sheet", [
    "sample,fastq_1,fastq_1\nA,{outdir}/a.fq.gz,{outdir}/b.fq.gz\n",
    "sample,fastq_1\nA,{outdir}/a.fq.gz,unexpected-field\n",
])
def test_handoff_does_not_hide_duplicate_columns_or_surplus_values(
        library, finished_run, tmp_path, sheet):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {"s.csv": sheet, "a.fq.gz": "a", "b.fq.gz": "b"})
    rule = _rule({"params": {"input": {"samplesheet": "s.csv",
                                       "provides": ["sample", "fastq_1"]}}})
    with pytest.raises(NfclawError) as err:
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")
    assert err.value.code is ErrorCode.HANDOFF_FAILED


def test_handoff_refuses_a_many_to_one_column_rename(library, finished_run, tmp_path):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {
        "s.csv": "sample,read1,r1\nA,{outdir}/a.fq.gz,{outdir}/b.fq.gz\n",
        "a.fq.gz": "a", "b.fq.gz": "b"})
    rule = _rule({"params": {"input": {"samplesheet": "s.csv",
                                       "provides": ["sample", "read1", "r1"],
                                       "rename": {"read1": "fastq_1", "r1": "fastq_1"}}}})
    with pytest.raises(NfclawError) as err:
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")
    assert err.value.code is ErrorCode.HANDOFF_FAILED
    assert "rename" in str(err.value).lower()


@pytest.mark.parametrize("historical", [False, True])
def test_handoff_refuses_an_unverified_or_changed_external_reference(
        library, finished_run, tmp_path, historical):
    import hashlib
    _, down = _trees(library("mini_up", "mini"))
    reference = tmp_path / "external.gtf"
    reference.write_text("original annotation\n")
    up = finished_run(tmp_path / "up", {}, params={"gtf": str(reference)})
    if not historical:
        (up / "provenance/inputs.sha256").write_text("")
        (up / "provenance/inputs.inventory.json").write_text("{}")
    if historical:
        digest = hashlib.sha256(reference.read_bytes()).hexdigest()
        (up / "provenance/inputs.sha256").write_text(f"{digest}  {reference}\n")
        reference.write_text("different annotation\n")
    rule = _rule({"params": {"fasta": {"upstream_param": "gtf", "optional": True}}})
    with pytest.raises(NfclawError) as err:
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")
    assert err.value.code is ErrorCode.HANDOFF_FAILED
    assert "reference" in str(err.value).lower()


def test_handoff_records_a_verified_external_reference(library, finished_run, tmp_path):
    import hashlib
    _, down = _trees(library("mini_up", "mini"))
    reference = tmp_path / "external.gtf"
    reference.write_text("original annotation\n")
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    up = finished_run(tmp_path / "up", {}, params={"gtf": str(reference)})
    (up / "provenance/inputs.sha256").write_text(f"{digest}  {reference}\n")
    rule = _rule({"params": {"fasta": {"upstream_param": "gtf"}}})
    result = handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")
    assert result.record["params"]["fasta"]["input_dependencies"] == {str(reference): digest}


def test_status_detects_a_changed_external_handoff_reference(
        library, fake_runs, tmp_path, monkeypatch):
    import hashlib
    reference = tmp_path / "external.gtf"
    reference.write_text("original annotation\n")
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    rule = {"params": {"fasta": {"upstream_param": "gtf"}}}
    root = library("mini_up", "mini", rules={("mini_up", "mini"): rule})
    launch = chain.orchestration.run_pipeline

    def with_reference(name, **kw):
        result = launch(name, **kw)
        if not kw["check_only"]:
            prov = kw["outdir"] / "provenance"
            if name == "mini_up":
                (prov / "params.json").write_text(json.dumps({"gtf": str(reference)}))
            from runner import provenance
            hashes = provenance.read_checksums(prov / "inputs.sha256", relative=False)
            hashes[str(reference)] = digest
            nodes = provenance.read_input_inventory(prov / "inputs.inventory.json")
            nodes.update(provenance.snapshot_inputs([reference])[1])
            (prov / "inputs.inventory.json").write_text(json.dumps(nodes))
            (prov / "inputs.sha256").write_text("".join(f"{value}  {path}\n" for path, value in hashes.items()))
        return result

    monkeypatch.setattr(chain.orchestration, "run_pipeline", with_reference)
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert problems == []
    reference.write_text("different annotation\n")
    state, problems = chain.status(out)
    assert any("external.gtf" in problem for problem in problems)
    assert chain.status_exit_code(state, problems) == 1


def test_status_detects_added_files_in_a_reference_directory(
        library, fake_runs, tmp_path, monkeypatch):
    from runner import provenance
    reference = tmp_path / "index"
    reference.mkdir()
    (reference / "index.bin").write_bytes(b"original")
    hashes, nodes = provenance.snapshot_inputs([reference])
    rule = {"params": {"fasta": {"upstream_param": "gtf"}}}
    root = library("mini_up", "mini", rules={("mini_up", "mini"): rule})
    launch = chain.orchestration.run_pipeline

    def with_reference(name, **kw):
        result = launch(name, **kw)
        if not kw["check_only"]:
            prov = kw["outdir"] / "provenance"
            if name == "mini_up":
                (prov / "params.json").write_text(json.dumps({"gtf": str(reference)}))
            recorded = provenance.read_checksums(prov / "inputs.sha256", relative=False)
            (prov / "inputs.sha256").write_text("".join(
                f"{digest}  {path}\n" for path, digest in {**recorded, **hashes}.items()))
            recorded_nodes = json.loads((prov / "inputs.inventory.json").read_text())
            (prov / "inputs.inventory.json").write_text(json.dumps({**recorded_nodes, **nodes}))
        return result

    monkeypatch.setattr(chain.orchestration, "run_pipeline", with_reference)
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert problems == []
    (reference / "new.bin").write_bytes(b"extra")
    state, problems = chain.status(out)
    assert any("directory" in problem for problem in problems)
    assert chain.status_exit_code(state, problems) == 1


def test_resume_refuses_changed_inherited_nextflow_environment(
        library, fake_runs, tmp_path, monkeypatch):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    monkeypatch.setenv("NXF_OFFLINE", "true")
    with pytest.raises(NfclawError, match="already succeeded with a different definition"):
        chain.run_chain(None, repo_root=root, outdir=out, resume=True)


@pytest.mark.parametrize("change", ["changed", "missing", "extra"])
@pytest.mark.parametrize("published_symlink", [False, True])
def test_status_checks_downstream_input_inventory_for_internal_directory_handoff(
        library, fake_runs, tmp_path, monkeypatch, change, published_symlink):
    import hashlib
    from runner import provenance
    tmp_path = tmp_path.resolve()
    rule = {"params": {"fasta": {"upstream_param": "gtf"}}}
    root = library("mini_up", "mini", rules={("mini_up", "mini"): rule})
    launch = chain.orchestration.run_pipeline
    reference = tmp_path / "chain/01-mini_up/index"

    def with_index(name, **kw):
        result = launch(name, **kw)
        if not kw["check_only"]:
            prov = kw["outdir"] / "provenance"
            if name == "mini_up":
                if published_symlink:
                    target = tmp_path / "work-index"
                    target.mkdir()
                    reference.symlink_to(target, target_is_directory=True)
                else:
                    reference.mkdir()
                (reference / "index.bin").write_bytes(b"original index")
                (prov / "params.json").write_text(json.dumps({"gtf": str(reference)}))
                from runner import outputs
                hashes, nodes, _ = outputs.snapshot(kw["outdir"], provenance._sha256)
                (prov / "outputs.inventory.json").write_text(json.dumps({"version": 1, "entries": nodes}))
                (prov / "outputs.sha256").write_text("".join(
                    f"{digest}  {path}\n" for path, digest in hashes.items()))
            else:
                # The real runner resolves the directory parameter before snapshotting inputs.
                hashes, nodes = provenance.snapshot_inputs([reference.resolve()])
                (prov / "inputs.inventory.json").write_text(json.dumps(nodes))
                (prov / "inputs.sha256").write_text("".join(
                    f"{digest}  {path}\n" for path, digest in hashes.items()))
        return result

    monkeypatch.setattr(chain.orchestration, "run_pipeline", with_index)
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert problems == []
    snapshot = out / "02-mini/provenance/inputs.sha256"
    original = snapshot.read_text()
    different = hashlib.sha256(b"different prelaunch index").hexdigest()
    if change == "changed":
        snapshot.write_text(f"{different}  {reference.resolve() / 'index.bin'}\n")
    elif change == "missing":
        snapshot.write_text("")
    else:
        snapshot.write_text(original + f"{different}  {reference.resolve() / 'extra.bin'}\n")
    state, problems = chain.status(out)
    assert any("input inventory" in problem for problem in problems)
    assert chain.status_exit_code(state, problems) == 1


def test_chain_lock_reports_environment_error_on_oserror(tmp_path, monkeypatch):
    import os
    record = tmp_path / "chain"
    def fail_open(*args, **kwargs):
        raise PermissionError("read-only filesystem")
    monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(NfclawError) as exc:
        with chain._lock(record, tmp_path):
            pass
    assert exc.value.code == ErrorCode.ENVIRONMENT
    assert "could not be created or locked" in str(exc.value)
