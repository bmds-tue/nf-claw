"""Chains: spec, plan, execution, failure/retry/stop, resume and lineage.

Nextflow never runs here: `run_pipeline` is replaced by a fake that lays out what a finished run
leaves behind (results, provenance bundle). `mini_up` writes a samplesheet for `mini`.
"""
import json
import signal

import pytest

from runner import chain, execution, orchestration
from runner.errors import ErrorCode, NfclawError

RULE = {"description": "mini_up writes a mini sheet",
        "upstream_params": {"nf_core_pipeline": "mini"},
        "params": {"input": {"samplesheet": "samplesheet/samplesheet.csv",
                             "provides": ["sample", "fastq_1", "fastq_2"]}}}
SHEET = ("sample,fastq_1,fastq_2\n"
         "A,{outdir}/fastq/A_1.fastq.gz,{outdir}/fastq/A_2.fastq.gz\n")


def _spec(**over):
    data = {"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                       {"pipeline": "mini", "params": {"aligner": "hisat2"}}]}
    data.update(over)
    return chain.parse_spec(data)


def _boom(code=ErrorCode.EXECUTION_FAILED, **details):
    return NfclawError(code, "Nextflow execution failed (exit status 1).",
                       details={"exit_code": 1, **details})


def _state(out):
    return json.loads((out / "chain" / "state.json").read_text())


def _last_log_line(out):
    return (out / "chain" / "logs" / "chain.log").read_text().splitlines()[-1]


@pytest.fixture
def fake_runs(monkeypatch, finished_run):
    """Replace run_pipeline: record each call, lay out a finished run, or fail on cue.
    `calls` are real launches; `checks` the check-only validations a chain does first."""
    from types import SimpleNamespace
    runs = SimpleNamespace(calls=[], checks=[], failures={}, check_failures={})

    def fake(name, **kw):
        if kw["check_only"]:
            runs.checks.append({"name": name, **kw})
            if name in runs.check_failures:
                raise runs.check_failures[name]
            return orchestration.RunResult(command=f"nextflow run {name}", outdir=kw["outdir"],
                                           checked_only=True, outputs_report=None)
        runs.calls.append({"name": name, **kw})
        if runs.failures.get(name):
            raise runs.failures[name].pop(0)
        files = ({"samplesheet/samplesheet.csv": SHEET, "fastq/A_1.fastq.gz": "1",
                  "fastq/A_2.fastq.gz": "2"} if name == "mini_up" else {"result.txt": "ok"})
        finished_run(kw["outdir"], files)
        manifest = kw["outdir"] / "provenance" / "run_manifest.json"
        manifest.write_text(json.dumps({**json.loads(manifest.read_text()),
                                        "dependency_inventory_version": 1,
                                        "chain": kw.get("chain_link")}))
        from runner import inputs, provenance, schema
        from pathlib import Path
        path_params = schema.load_param_schema(kw["repo_root"] / "pipelines" / name / "upstream").reference_path_params()
        given = kw["input_path"] if isinstance(kw["input_path"], list) else [kw["input_path"]]
        candidates = given + [value for key, value in kw["cli_overrides"].items()
                                                 if key in path_params and isinstance(value, str)]
        sources = [inputs.absolute_local_path(value) for value in candidates if value and Path(value).exists()]
        for key, value in {"input": kw["input_path"], **kw["cli_overrides"]}.items():
            reference = inputs.samplesheet_schema(kw["repo_root"] / "pipelines" / name / "upstream", key)
            if isinstance(value, (str, Path)) and value and reference and Path(value).is_file():
                sheet_schema = schema.load_input_schema(kw["repo_root"] / "pipelines" / name / "upstream", reference)
                sources.extend(path for path in provenance.samplesheet_input_paths(Path(value), sheet_schema)
                               if path.exists())
        hashes, inventory = provenance.snapshot_inputs(sources)
        (kw["outdir"] / "provenance/inputs.sha256").write_text("".join(
            f"{digest}  {path}\n" for path, digest in hashes.items()))
        (kw["outdir"] / "provenance/inputs.inventory.json").write_text(json.dumps(inventory))
        return orchestration.RunResult(command=f"nextflow run {name}", outdir=kw["outdir"],
                                       checked_only=False, outputs_report=None)

    monkeypatch.setattr(chain.orchestration, "run_pipeline", fake)
    monkeypatch.setattr(chain, "_probe_config", lambda spec, p, **kw: [])   # no Nextflow here
    return runs


# --- the spec ------------------------------------------------------------------------------

def test_spec_defaults_ids_dirnames_and_profile():
    spec = _spec()
    assert [s.dirname for s in spec.stages] == ["01-mini_up", "02-mini"]
    assert spec.profile == "docker" and spec.stages[1].retries == 0


def test_spec_param_keys_mean_what_they_mean_on_the_command_line():
    spec = chain.parse_spec({"stages": [{"pipeline": "a", "params": {"skip-busco": True}}]})
    assert spec.stages[0].params == {"skip_busco": True}


def test_an_input_written_as_a_param_is_the_stages_input():
    # --input gets the samplesheet pre-check and path resolution, wherever the spec puts it.
    spec = chain.parse_spec({"stages": [{"pipeline": "a", "params": {"input": "/x.csv", "k": 1}}]})
    assert spec.stages[0].input == "/x.csv" and spec.stages[0].params == {"k": 1}
    with pytest.raises(NfclawError, match="give its input once"):
        chain.parse_spec({"stages": [{"pipeline": "a", "input": "/x", "params": {"input": "/y"}}]})


def test_spec_run_options_are_validated_like_the_run_flags():
    spec = chain.parse_spec({"stages": [{"pipeline": "a"}], "nxf_ver": "25.10.4",
                             "nxf_env": {"NXF_OFFLINE": "true"},
                             "limits": {"cpus": 4, "memory": "15.GB"}})
    assert spec.nxf_ver == "25.10.4" and spec.nxf_env == {"NXF_OFFLINE": "true"}
    assert spec.limits.cpus == 4 and spec.limits.memory == "15.GB"


def test_a_stage_overrides_the_chains_run_options():
    # Releases of different ages need different engines: fetchngs 1.13 wants >= 25.10.4, an older
    # atacseq a parser before Nextflow 26's strict one.
    spec = chain.parse_spec({
        "nxf_env": {"NXF_JVM_ARGS": "-Dipv6", "NXF_OFFLINE": "false"}, "limits": {"cpus": 8},
        "stages": [{"pipeline": "a"},
                   {"pipeline": "b", "nxf_ver": "25.10.4", "nxf_env": {"NXF_OFFLINE": "true"},
                    "profile": "singularity", "limits": {"memory": "4.GB"}}]})
    first, second = (chain.options(spec, s) for s in spec.stages)
    assert first.nxf_ver is None and first.profile == "docker" and first.limits.cpus == 8
    assert second.nxf_ver == "25.10.4" and second.profile == "singularity"
    assert second.nxf_env == {"NXF_JVM_ARGS": "-Dipv6", "NXF_OFFLINE": "true"}   # merged
    assert second.limits.memory == "4.GB" and second.limits.cpus is None         # replaced


def test_stage_run_options_round_trip_through_chain_json(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                        {"pipeline": "mini", "nxf_ver": "25.10.4",
                                         "limits": {"cpus": 2}}]})
    again = chain.parse_spec(chain.normalized(spec, chain.plan(spec, repo_root=root)))
    assert chain.options(again, again.stages[1]) == chain.options(spec, spec.stages[1])


@pytest.mark.parametrize("data, msg", [
    ({"stages": [{"pipeline": "a", "nxf_ver": "26"}]}, "stage 'a': --nxf-ver must be"),
    ({"stages": [{"pipeline": "a", "profile": ""}]}, "'profile' must be a profile name"),
    ({"stages": []}, "at least one stage"),
    ({"stages": [{"pipeline": "a"}, {"pipeline": "a"}]}, "duplicate stage id 'a'"),
    ({"stages": [{"pipeline": "a", "retries": -1}]}, "'retries' must be"),
    ({"stages": [{"pipeline": "a", "surprise": 1}]}, "unknown keys"),
    ({"stages": [{"pipeline": "a", "id": "Bad Id"}]}, "must match"),
    ({"stages": [{"pipeline": "a"}], "nxf_env": {"JAVA_HOME": "/x"}}, "only accepts NXF_"),
    ({"stages": [{"pipeline": "a"}], "nxf_ver": "26"}, "full Nextflow version"),
    ({"stages": [{"pipeline": "a"}], "limits": {"memory": "lots"}}, "--limit-memory"),
    ({"stages": [{"pipeline": "a"}], "limits": {"cpus": "4"}}, "'limits.cpus'"),
    ({"stages": [{"pipeline": "a"}], "extra": 1}, "unknown keys"),
])
def test_bad_specs_fail_before_anything_runs(data, msg):
    with pytest.raises(NfclawError, match=msg) as err:
        chain.parse_spec(data)
    assert err.value.code is ErrorCode.PARAMS_INVALID


def test_load_spec_reads_a_json_file(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({"stages": [{"pipeline": "a"}]}))
    assert chain.load_spec(path).stages[0].pipeline == "a"
    path.write_text("{nope")
    with pytest.raises(NfclawError, match="chain spec is not valid JSON"):
        chain.load_spec(path)


# --- the plan --------------------------------------------------------------------------------

def test_plan_injects_upstream_params_and_finds_the_rule(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    planned = chain.plan(_spec(), repo_root=root)
    assert planned[0].params == {"nf_core_pipeline": "mini"}       # set on the upstream run
    assert planned[0].rule is None
    assert planned[1].rule.origin == "handoffs/mini_up/mini.json"
    assert planned[0].input == "/data/ids.csv"


def test_plan_fails_fast_without_a_rule(library):
    root = library("mini_up", "mini")
    with pytest.raises(NfclawError, match="no handoff from mini_up to mini") as err:
        chain.plan(_spec(), repo_root=root)
    assert "inline" in str(err.value)


def test_plan_fails_fast_on_an_incompatible_rule(library):
    bad = {"params": {"input": {"samplesheet": "s.csv", "provides": ["sample"]}}}
    root = library("mini_up", "mini", rules={("mini_up", "mini"): bad})
    with pytest.raises(NfclawError, match="missing required column 'fastq_1'"):
        chain.plan(_spec(), repo_root=root)


def test_plan_reports_a_clash_with_the_upstream_stage_params(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"stages": [
        {"pipeline": "mini_up", "params": {"nf_core_pipeline": "other"}}, {"pipeline": "mini"}]})
    with pytest.raises(NfclawError, match="needs --nf_core_pipeline=mini"):
        chain.plan(spec, repo_root=root)


def test_plan_reports_an_unknown_pipeline(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    with pytest.raises(NfclawError) as err:
        chain.plan(chain.parse_spec({"stages": [{"pipeline": "nope"}]}), repo_root=root)
    assert err.value.code is ErrorCode.PIPELINE_NOT_FOUND


def test_inline_handoff_wins_over_the_registry(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    inline = {"params": {"fasta": {"upstream_param": "gtf"}}}
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up"},
                                        {"pipeline": "mini", "handoff": inline}]})
    assert chain.plan(spec, repo_root=root)[1].rule.origin == "inline handoff of stage 'mini'"


def test_a_handoff_rule_file_can_be_named_per_stage(library, tmp_path):
    root = library("mini_up", "mini")
    rule_file = tmp_path / "my-rule.json"
    rule_file.write_text(json.dumps(RULE))
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up"},
                                        {"pipeline": "mini", "handoff": str(rule_file)}]})
    assert chain.plan(spec, repo_root=root)[1].rule.origin == str(rule_file)


def test_fingerprint_changes_with_what_a_stage_would_do(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    a = chain.fingerprint(chain.plan(_spec(), repo_root=root)[1])
    other = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                         {"pipeline": "mini", "params": {"aligner": "star"}}]})
    assert a == chain.fingerprint(chain.plan(_spec(), repo_root=root)[1])
    assert a != chain.fingerprint(chain.plan(other, repo_root=root)[1])


def test_normalized_spec_round_trips(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = _spec(limits={"memory": "8.GB"})
    planned = chain.plan(spec, repo_root=root)
    again = chain.parse_spec(chain.normalized(spec, planned))
    assert [chain.fingerprint(p) for p in chain.plan(again, repo_root=root)] == \
        [chain.fingerprint(p) for p in planned]
    assert again.limits.memory == "8.GB"


# --- the configuration probe -------------------------------------------------------------------

def test_the_probe_parses_each_stage_config_with_its_own_engine(library, monkeypatch):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"nxf_env": {"NXF_JVM_ARGS": "-Dipv6"}, "stages": [
        {"pipeline": "mini_up"}, {"pipeline": "mini", "nxf_ver": "25.10.4", "demo": True}]})
    planned = chain.plan(spec, repo_root=root)
    seen = []

    def fake_run(cmd, **kw):
        seen.append((cmd, kw["env"]))
        import subprocess
        bad = "mini/upstream" in cmd[2]
        return subprocess.CompletedProcess(cmd, 1 if bad else 0, stdout=(
            "Error nextflow.config:298:14: Unexpected input: '('\n\nERROR ~ Config parsing failed\n"
            if bad else "process {}\n"), stderr="")

    monkeypatch.setattr(chain.shutil, "which", lambda name: "/usr/bin/nextflow")
    monkeypatch.setattr(chain, "capture", fake_run)
    assert chain._probe_config(spec, planned[0]) == []
    [issue] = chain._probe_config(spec, planned[1])
    assert "02-mini (mini): Nextflow 25.10.4 cannot parse its configuration" in issue
    assert "Unexpected input" in issue
    cmd, env = seen[1]
    assert cmd[:2] == ["nextflow", "config"] and cmd[-2:] == ["-profile", "test,docker"]
    assert env["NXF_VER"] == "25.10.4" and env["NXF_JVM_ARGS"] == "-Dipv6"
    assert "NXF_VER" not in seen[0][1]                 # the first stage keeps the default engine


def test_the_probe_passes_extra_configs_to_the_launcher(library, monkeypatch, tmp_path):
    # `nextflow config` takes -c only as the launcher's option: `nextflow -c x config <pipeline>`.
    import subprocess
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    cfg = tmp_path / "extra.config"
    cfg.write_text("process {}\n")
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "config": [str(cfg)]}]})
    planned = chain.plan(spec, repo_root=root)
    seen = []
    monkeypatch.setattr(chain.shutil, "which", lambda name: "/usr/bin/nextflow")
    monkeypatch.setattr(chain, "capture", lambda cmd, **kw: seen.append(cmd)
                        or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
    assert chain._probe_config(spec, planned[0]) == []
    assert seen[0][:4] == ["nextflow", "-c", str(cfg), "config"]


def test_the_probe_suggests_the_engine_the_release_declares(library, monkeypatch):
    import subprocess
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    (root / "pipelines" / "mini" / "upstream" / "nextflow.config").write_text(
        "manifest {\n    nextflowVersion = '!>=23.04.0'\n}\n")
    planned = chain.plan(_spec(), repo_root=root)
    monkeypatch.setattr(chain.shutil, "which", lambda name: "/usr/bin/nextflow")
    monkeypatch.setattr(chain, "capture", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 1, stdout="ERROR ~ Config parsing failed\n", stderr=""))
    [issue] = chain._probe_config(_spec(), planned[1])
    assert 'the release declares Nextflow 23.04.0: try "nxf_ver": "23.04.0"' in issue


def test_the_probe_tells_an_engine_that_cannot_start_from_a_config_it_rejects(library,
                                                                             monkeypatch):
    # Nextflow 23.04's launcher fetches its jars on first use; on a host where that fails the stage
    # could not start either — said as what it is, not as a config the engine rejects.
    import subprocess
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up"},
                                        {"pipeline": "mini", "nxf_ver": "23.04.0"}]})
    planned = chain.plan(spec, repo_root=root)
    monkeypatch.setattr(chain.shutil, "which", lambda name: "/usr/bin/nextflow")
    monkeypatch.setattr(chain, "capture", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 1, stdout="", stderr="CAPSULE EXCEPTION: Error resolving dependencies.\n"
                                   "Unable to initialize nextflow environment\n"))
    [issue] = chain._probe_config(spec, planned[1])
    assert "02-mini (mini): Nextflow 23.04.0 could not be started" in issue
    assert "cannot parse" not in issue and "Unable to initialize" in issue


def test_a_probe_that_cannot_run_reports_unverified_configuration(library, monkeypatch):
    import subprocess
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    planned = chain.plan(_spec(), repo_root=root)
    monkeypatch.setattr(chain.shutil, "which", lambda name: None)
    [issue] = chain._probe_config(_spec(), planned[0])
    assert "could not be verified" in issue and "nextflow" in issue
    monkeypatch.setattr(chain.shutil, "which", lambda name: "/usr/bin/nextflow")

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 300)

    monkeypatch.setattr(chain, "capture", slow)
    [issue] = chain._probe_config(_spec(), planned[0])
    assert "could not be verified" in issue and "300" in issue


@pytest.mark.parametrize("check_only", [False, True])
@pytest.mark.parametrize("failure", ["timeout", "oserror"])
def test_an_inconclusive_config_probe_cannot_certify_or_start_a_chain(
        library, monkeypatch, tmp_path, check_only, failure):
    import subprocess
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = _spec()
    planned = chain.plan(spec, repo_root=root)
    monkeypatch.setattr(chain, "plan", lambda *args, **kw: planned)
    monkeypatch.setattr(chain.shutil, "which", lambda name: "/usr/bin/nextflow")
    launches = []

    def fake_pipeline(name, **kw):
        if not kw["check_only"]:
            launches.append(name)
        return orchestration.RunResult(command=f"nextflow run {name}", outdir=kw["outdir"],
                                       checked_only=kw["check_only"], outputs_report=None)

    def unavailable(cmd, **kw):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(cmd, 300)
        raise OSError("engine could not execute")

    monkeypatch.setattr(chain.orchestration, "run_pipeline", fake_pipeline)
    monkeypatch.setattr(chain, "capture", unavailable)
    with pytest.raises(NfclawError) as err:
        chain.run_chain(spec, repo_root=root, outdir=tmp_path / "c", check_only=check_only)
    assert "could not be verified" in str(err.value.details)
    assert launches == [] and not (tmp_path / "c").exists()


def test_an_unparsable_stage_config_stops_the_chain_before_anything_runs(library, fake_runs,
                                                                         monkeypatch, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    monkeypatch.setattr(chain, "_probe_config",
                        lambda spec, p, **kw: ["02-mini (mini): cannot parse"] if p.stage.index == 2
                        else [])
    with pytest.raises(NfclawError, match="its Nextflow engine cannot set it up") as err:
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c")
    assert '"nxf_ver"' in err.value.fix and fake_runs.calls == []
    assert not (tmp_path / "c").exists()


# --- running ---------------------------------------------------------------------------------

def test_two_stages_run_in_order_with_the_handoff_between(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chainout"
    res = chain.run_chain(_spec(), repo_root=root, outdir=out)
    assert res.outcome == "success"
    up, down = fake_runs.calls
    assert up["outdir"] == out / "01-mini_up" and up["cli_overrides"]["nf_core_pipeline"] == "mini"
    snap = out / "chain" / "handoffs" / "02-mini" / "input.csv"
    assert down["input_path"] == str(snap) and down["outdir"] == out / "02-mini"
    assert down["chain_link"]["upstream"]["stage"] == "mini_up"
    assert up["chain_link"]["upstream"] is None
    assert [s["status"] for s in _state(out)["stages"]] == ["success", "success"]
    assert _last_log_line(out).endswith(": success")
    assert json.loads((out / "chain" / "chain.json").read_text())["stages"][0]["input"] \
        == "/data/ids.csv"
    record = json.loads((out / "chain" / "handoffs" / "02-mini" / "handoff.json").read_text())
    assert record["from_stage"] == "mini_up" and record["to_stage"] == "mini"


def test_every_stage_is_validated_before_the_first_one_launches(library, fake_runs, tmp_path):
    fake_runs.check_failures["mini"] = _boom(ErrorCode.PARAMS_INVALID)   # e.g. a typo'd flag
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c")
    assert [c["name"] for c in fake_runs.checks] == ["mini_up", "mini"]
    assert fake_runs.calls == []                                        # nothing launched
    assert fake_runs.checks[1]["deferred_params"] == frozenset({"input"})
    assert not (tmp_path / "c").exists()


def test_a_stage_that_sets_a_handed_over_param_itself_keeps_its_value(library, fake_runs,
                                                                      tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    mine = tmp_path / "mine.csv"
    mine.write_text("sample,fastq_1\n")
    warnings = []
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                        {"pipeline": "mini", "input": str(mine)}]})
    chain.run_chain(spec, repo_root=root, outdir=tmp_path / "c", on_warning=warnings.append)
    assert fake_runs.calls[1]["input_path"] == str(mine)
    assert fake_runs.checks[1]["deferred_params"] == frozenset()
    assert any("--input is set by this stage itself" in w for w in warnings)


def test_a_failed_stage_stops_the_chain(library, fake_runs, tmp_path):
    fake_runs.failures["mini_up"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    with pytest.raises(NfclawError, match="exit status 1"):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    assert [c["name"] for c in fake_runs.calls] == ["mini_up"]
    assert [s["status"] for s in _state(out)["stages"]] == ["failed", "pending"]
    assert _state(out)["outcome"] == "failed at stage 01-mini_up: failed (exit status 1)"
    assert _last_log_line(out).endswith("failed at stage 01-mini_up: failed (exit status 1)")


def test_retries_relaunch_with_resume_only_for_execution_failures(library, fake_runs, tmp_path):
    fake_runs.failures["mini_up"] = [_boom(), _boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "retries": 2},
                                        {"pipeline": "mini"}]})
    assert chain.run_chain(spec, repo_root=root, outdir=tmp_path / "c").outcome == "success"
    assert [c["resume"] for c in fake_runs.calls if c["name"] == "mini_up"] == [False, True, True]
    attempts = _state(tmp_path / "c")["stages"][0]["attempts"]
    assert [a["outcome"] for a in attempts] == ["failed (exit status 1)"] * 2 + ["success"]


def test_retries_run_out(library, fake_runs, tmp_path):
    fake_runs.failures["mini_up"] = [_boom(), _boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "retries": 1},
                                        {"pipeline": "mini"}]})
    with pytest.raises(NfclawError):
        chain.run_chain(spec, repo_root=root, outdir=tmp_path / "c")
    assert len(fake_runs.calls) == 2


@pytest.mark.parametrize("error", [_boom(ErrorCode.PARAMS_INVALID),
                                   _boom(timeout_seconds=60)])
def test_validation_errors_and_timeouts_are_never_retried(library, fake_runs, tmp_path, error):
    fake_runs.failures["mini_up"] = [error]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "retries": 3},
                                        {"pipeline": "mini"}]})
    with pytest.raises(NfclawError):
        chain.run_chain(spec, repo_root=root, outdir=tmp_path / "c")
    assert len(fake_runs.calls) == 1


def test_a_stop_signal_stops_the_chain_and_is_recorded(library, fake_runs, tmp_path):
    fake_runs.failures["mini_up"] = [execution.Terminated(signal.SIGTERM)]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    with pytest.raises(execution.Terminated):
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c")
    assert _state(tmp_path / "c")["stages"][0]["status"] == "stopped"
    assert _last_log_line(tmp_path / "c").endswith("terminated by SIGTERM (stage 01-mini_up)")


def test_ctrl_c_stops_the_chain_and_is_recorded(library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [KeyboardInterrupt()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    with pytest.raises(KeyboardInterrupt):
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c")
    assert [s["status"] for s in _state(tmp_path / "c")["stages"]] == ["success", "stopped"]
    assert _last_log_line(tmp_path / "c").endswith("interrupted (stage 02-mini)")


def test_a_handoff_failure_launches_nothing_downstream(library, fake_runs, tmp_path):
    bad = {**RULE, "params": {"input": {"samplesheet": "nowhere.csv",
                                        "provides": ["sample", "fastq_1"]}}}
    root = library("mini_up", "mini", rules={("mini_up", "mini"): bad})
    with pytest.raises(NfclawError) as err:
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c")
    assert err.value.code is ErrorCode.HANDOFF_FAILED
    assert [c["name"] for c in fake_runs.calls] == ["mini_up"]
    assert [s["status"] for s in _state(tmp_path / "c")["stages"]] == ["success", "failed"]
    assert _last_log_line(tmp_path / "c").endswith("failed at stage 02-mini: handoff")


def test_timeout_is_a_budget_for_the_whole_chain(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c", timeout_seconds=600)
    assert all(0 < c["timeout_seconds"] <= 600 for c in fake_runs.calls)


def test_a_spent_budget_stops_before_the_next_stage(library, fake_runs, tmp_path, monkeypatch):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    clock = 0.0
    run = chain.orchestration.run_pipeline

    def timed_run(name, **kw):
        nonlocal clock
        result = run(name, **kw)
        if name == "mini_up" and not kw["check_only"]:
            clock = 999.0
        return result

    monkeypatch.setattr(chain.time, "monotonic", lambda: clock)
    monkeypatch.setattr(chain.orchestration, "run_pipeline", timed_run)
    with pytest.raises(NfclawError, match="--timeout ran out before stage 02-mini"):
        chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c", timeout_seconds=600)
    assert [c["name"] for c in fake_runs.calls] == ["mini_up"]
    assert _last_log_line(tmp_path / "c").endswith("timed out after 600 s")


def test_a_non_empty_outdir_needs_resume(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    out.mkdir()
    (out / "x").write_text("x")
    with pytest.raises(NfclawError, match="is not empty") as err:
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    assert "to continue that chain" in str(err.value)


def test_one_chain_per_outdir(library, fake_runs, tmp_path):
    import fcntl
    import os
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    (out / "chain").mkdir(parents=True)
    # a chain to resume (so the non-empty guard does not answer first), held by another process
    (out / "chain" / "state.json").write_text(
        json.dumps({"chain_id": "x", "stages": [], "outcome": "failed"}))
    fd = os.open(out / "chain" / ".lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)                 # flock: a second open file conflicts, same process too
    try:
        with pytest.raises(NfclawError, match="another nfclaw chain is running"):
            chain.run_chain(_spec(), repo_root=root, outdir=out, resume=True)
    finally:
        os.close(fd)


# --- --check and --resume ----------------------------------------------------------------------

def test_check_validates_every_stage_and_writes_nothing(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    res = chain.run_chain(_spec(), repo_root=root, outdir=tmp_path / "c", check_only=True)
    assert res.outcome == "checked" and [d for d, _ in res.commands] == [
        "01-mini_up", "02-mini — --input from the stage before it (handoffs/mini_up/mini.json)"]
    assert fake_runs.calls == []
    assert fake_runs.checks[1]["deferred_params"] == frozenset({"input"})
    assert not (tmp_path / "c").exists()


def test_resume_needs_a_recorded_chain(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    with pytest.raises(NfclawError, match="no chain to resume"):
        chain.run_chain(None, repo_root=root, outdir=tmp_path / "c", resume=True)


def test_resume_skips_succeeded_stages_and_resumes_the_failed_one(library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    (out / "02-mini").mkdir(parents=True, exist_ok=True)
    (out / "02-mini" / "partial").write_text("left by the failed attempt")
    fake_runs.calls.clear()
    fake_runs.checks.clear()
    res = chain.run_chain(None, repo_root=root, outdir=out, resume=True)   # spec from chain.json
    assert res.outcome == "success"
    assert [(c["name"], c["resume"]) for c in fake_runs.calls] == [("mini", True)]
    assert [c["name"] for c in fake_runs.checks] == ["mini"]     # succeeded stages not re-checked
    assert [len(s["attempts"]) for s in _state(out)["stages"]] == [1, 2]


def test_resume_refuses_to_redefine_a_succeeded_stage(library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    edited = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/other.csv"},
                                          {"pipeline": "mini"}]})
    with pytest.raises(NfclawError, match="already succeeded with a different definition"):
        chain.run_chain(edited, repo_root=root, outdir=out, resume=True)


def test_resume_accepts_a_fixed_failed_stage(library, fake_runs, tmp_path):
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    fixed = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                         {"pipeline": "mini", "params": {"aligner": "star"}}]})
    assert chain.run_chain(fixed, repo_root=root, outdir=out, resume=True).outcome == "success"
    assert fake_runs.calls[-1]["cli_overrides"]["aligner"] == "star"


def test_resume_extends_a_finished_chain_with_an_appended_stage(library, fake_runs, tmp_path):
    back = {"params": {"gtf": {"upstream_param": "outdir"}}}       # synthetic edge mini → mini_up
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE, ("mini", "mini_up"): back})
    out = tmp_path / "c"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    fake_runs.calls.clear()
    longer = chain.parse_spec({"stages": [
        {"pipeline": "mini_up", "input": "/data/ids.csv"},
        {"pipeline": "mini", "params": {"aligner": "hisat2"}},
        {"pipeline": "mini_up", "id": "again", "input": "/data/more.csv"}]})
    assert chain.run_chain(longer, repo_root=root, outdir=out, resume=True).outcome == "success"
    assert [c["outdir"].name for c in fake_runs.calls] == ["03-again"]
    assert fake_runs.calls[0]["cli_overrides"]["gtf"] == str(out / "02-mini")


def test_resume_refuses_a_succeeded_stage_whose_bundle_is_gone(library, fake_runs, tmp_path):
    import shutil
    fake_runs.failures["mini"] = [_boom()]
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    with pytest.raises(NfclawError):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    shutil.rmtree(out / "01-mini_up" / "provenance")
    with pytest.raises(NfclawError, match="no longer says so"):
        chain.run_chain(None, repo_root=root, outdir=out, resume=True)


# --- lineage ---------------------------------------------------------------------------------

def test_status_reconstructs_the_chain_from_any_stage(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    for where in (out, out / "02-mini"):
        state, problems = chain.status(where)
        assert problems == [] and [s["id"] for s in state["stages"]] == ["mini_up", "mini"]
    text = chain.format_status(*chain.status(out))
    assert "02-mini" in text and "input ← 01-mini_up" in text and "lineage: verified" in text


def test_status_detects_a_tampered_link(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    (out / "01-mini_up" / "provenance" / "outputs.sha256").write_text(
        "d" * 64 + "  fastq/A_1.fastq.gz\n")
    snap = out / "chain" / "handoffs" / "02-mini" / "input.csv"
    snap.write_text(snap.read_text() + "B,x,y\n")
    _, problems = chain.status(out)
    assert any("fastq/A_1.fastq.gz is not what the upstream run produced" in p for p in problems)
    assert any("snapshot" in p and "changed since the handoff" in p for p in problems)
    assert "lineage: BROKEN" in chain.format_status({}, problems)


def test_status_needs_a_chain(tmp_path):
    with pytest.raises(NfclawError, match="no chain recorded"):
        chain.status(tmp_path)


# --- the chain's log speaks for itself (runlog.read_state, as `nfclaw status` reads a run) ------

def test_the_chain_log_is_read_like_a_run_log(library, fake_runs, tmp_path):
    from runner import runlog
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    st = runlog.read_state(out / "chain" / "logs" / "chain.log")
    assert (st.state, st.kind, st.outcome) == ("success", "chain", "success")
    assert st.pid == __import__("os").getpid() and st.host
    assert st.host_id == runlog.host_identity()


def test_status_tells_a_chain_whose_nfclaw_was_killed(library, fake_runs, tmp_path):
    # SIGKILL leaves no last line: state.json still says "running", the log's pid is gone.
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    log = out / "chain" / "logs" / "chain.log"
    lines = log.read_text().splitlines()
    log.write_text("\n".join(lines[:-1]).replace(f"pid: {__import__('os').getpid()}",
                                                 "pid: 999999") + "\n")
    state_file = out / "chain" / "state.json"
    state_file.write_text(state_file.read_text().replace('"outcome": "success"',
                                                         '"outcome": "running"', 1))
    state, problems = chain.status(out)
    assert state["log_state"] == "dead"
    assert "stopped without an outcome" in chain.format_status(state, problems)
    assert chain.status_exit_code(state, problems) == 1


def test_status_exit_codes_follow_nfclaw_status(library, fake_runs, tmp_path):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "c"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert chain.status_exit_code(state, problems) == 0
    assert chain.status_exit_code(state, ["a broken link"]) == 1
    assert chain.status_exit_code({**state, "log_state": "running"}, []) == 3


# --- a stage whose samplesheet nfclaw generates from data files ------------------------------------

def test_spec_sheet_set_and_input_lists_are_validated():
    spec = chain.parse_spec({"stages": [{"pipeline": "rnaseq", "input": ["/d/a.fq.gz", "/d/b.fq.gz"],
                                         "sheet_set": {"strandedness": "auto", "status": 1}}]})
    assert spec.stages[0].input == ["/d/a.fq.gz", "/d/b.fq.gz"]
    assert spec.stages[0].sheet_set == {"strandedness": "auto", "status": "1"}
    for bad, msg in (({"input": []}, "'input' list"), ({"input": ["/a", 3]}, "'input' list"),
                     ({"sheet_set": ["x"]}, "'sheet_set' must map"),
                     ({"sheet_set": []}, "'sheet_set' must map"),
                     ({"sheet_set": ""}, "'sheet_set' must map"),
                     ({"sheet_set": {"x": {"y": 1}}}, "sheet_set")):
        with pytest.raises(NfclawError, match=msg):
            chain.parse_spec({"stages": [{"pipeline": "rnaseq", **bad}]})


def test_fingerprints_without_sheet_set_are_those_of_earlier_chains(library):
    # A succeeded stage is frozen by its fingerprint: adding a spec key must not change the
    # fingerprint of a stage that does not use it, or every recorded chain would refuse to resume.
    import hashlib
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    spec = _spec()
    p = chain.plan(spec, repo_root=root)[1]
    opts = chain.options(spec, p.stage)
    body = {"fingerprint_version": chain.FINGERPRINT_VERSION, "pipeline": "mini",
            "pipeline_version": None, "commit": p.tree.commit, "input": None, "input_sha256": None,
            "params": p.params, "params_file": None, "demo": False, "handoff": p.rule.sha256(),
            "options": chain._options_json({"profile": opts.profile, "nxf_ver": opts.nxf_ver,
                                            "nxf_env": opts.nxf_env, "configs": opts.configs,
                                            "limits": opts.limits}),
            "config_sha256": {}}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    assert chain.fingerprint(p, spec) == hashlib.sha256(text.encode()).hexdigest()
    other = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": "/data/ids.csv"},
                                         {"pipeline": "mini", "params": {"aligner": "hisat2"},
                                          "sheet_set": {"sample": "{sample}"}}]})
    assert chain.fingerprint(chain.plan(other, repo_root=root)[1], other) != chain.fingerprint(p, spec)


def test_a_first_stage_takes_data_files_and_sheet_columns(library, fake_runs, tmp_path):
    import sheetgen_schemas as S
    from test_sheetgen import pair
    root = library("mini")
    S.make_pipeline(root, S.RNASEQ, "rna")
    data = tmp_path / "reads"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    spec = chain.parse_spec({"stages": [{"pipeline": "rna", "input": str(data),
                                         "sheet_set": {"strandedness": "auto"}}]})
    out = tmp_path / "c"
    assert chain.run_chain(spec, repo_root=root, outdir=out).outcome == "success"
    (check,), (call,) = fake_runs.checks, fake_runs.calls
    assert check["input_path"] == call["input_path"] == str(data)
    assert check["sheet_set"] == call["sheet_set"] == {"strandedness": "auto"}
    recorded = json.loads((out / "chain" / "chain.json").read_text())["stages"][0]
    assert recorded["sheet_set"] == {"strandedness": "auto"} and recorded["input"] == str(data)
    again = chain.parse_spec(json.loads((out / "chain" / "chain.json").read_text()))
    assert again.stages[0].sheet_set == {"strandedness": "auto"}


def test_a_chain_check_generates_the_first_stages_samplesheet(library, tmp_path, monkeypatch):
    # Not faked: the real check-only run generates and validates the sheet, and a missing column
    # stops the chain before any stage launches.
    import sheetgen_schemas as S
    from test_sheetgen import pair
    monkeypatch.setattr(chain, "_probe_config", lambda spec, p, **kw: [])
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    root = library("mini")
    S.make_pipeline(root, S.RNASEQ, "rna")
    data = tmp_path / "reads"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    ok = chain.parse_spec({"stages": [{"pipeline": "rna", "input": str(data),
                                       "sheet_set": {"strandedness": "auto"}}]})
    res = chain.run_chain(ok, repo_root=root, outdir=tmp_path / "c", check_only=True)
    assert res.outcome == "checked" and "--input" in res.commands[0][1]
    missing = chain.parse_spec({"stages": [{"pipeline": "rna", "input": str(data)}]})
    with pytest.raises(NfclawError, match="needs values"):
        chain.run_chain(missing, repo_root=root, outdir=tmp_path / "d", check_only=True)
    assert not (tmp_path / "c").exists() and not (tmp_path / "d").exists()


def test_sheet_set_on_a_handed_over_stage_is_refused_before_anything_runs(library, tmp_path,
                                                                          monkeypatch):
    monkeypatch.setattr(chain, "_probe_config", lambda spec, p, **kw: [])
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    ids = tmp_path / "ids.csv"
    ids.write_text("SRR1\n")
    spec = chain.parse_spec({"stages": [{"pipeline": "mini_up", "input": str(ids)},
                                        {"pipeline": "mini", "sheet_set": {"sample": "{sample}"}}]})
    with pytest.raises(NfclawError, match="a chain stage's sheet_set"):
        chain.run_chain(spec, repo_root=root, outdir=tmp_path / "c", check_only=True)
    assert not (tmp_path / "c").exists()


def _generated_stage(library, tmp_path, fake_runs, data_input):
    """A one-stage chain whose samplesheet is generated from `data_input`, run to success with a
    bundle that records the generated sheet as a real run would."""
    import sheetgen_schemas as S
    from runner import sheetgen
    root = library("mini")
    up = S.make_pipeline(root, S.RNASEQ, "rna")
    spec = chain.parse_spec({"stages": [{"pipeline": "rna", "input": data_input,
                                         "sheet_set": {"strandedness": "auto"}}]})
    out = tmp_path / "c"
    real_fake = chain.orchestration.run_pipeline

    def recording(name, **kw):
        res = real_fake(name, **kw)
        if not kw["check_only"]:
            source = sheetgen.detect(kw["input_path"], up)
            generated = sheetgen.generate(source, up, pipeline=name, assignments=kw["sheet_set"],
                                          outdir=kw["outdir"], work_dir=tmp_path / "work")
            sheetgen.write(generated, kw["outdir"] / "provenance")
            manifest = kw["outdir"] / "provenance" / "run_manifest.json"
            manifest.write_text(json.dumps({**json.loads(manifest.read_text()),
                                            "generated_samplesheet": {"file": generated.filename}}))
        return res

    chain.orchestration.run_pipeline = recording
    try:
        assert chain.run_chain(spec, repo_root=root, outdir=out).outcome == "success"
    finally:
        chain.orchestration.run_pipeline = real_fake
    return root, spec, out


def test_resume_refuses_a_succeeded_stage_whose_data_now_yields_another_sheet(
        library, fake_runs, tmp_path):
    from test_sheetgen import pair
    data = tmp_path / "reads"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    root, spec, out = _generated_stage(library, tmp_path, fake_runs, str(data))
    # Unchanged data: the succeeded stage stays frozen and the chain resumes.
    assert chain.run_chain(spec, repo_root=root, outdir=out, resume=True).outcome == "success"
    pair(data, "B_R1.fastq.gz", "B_R2.fastq.gz")
    with pytest.raises(NfclawError, match="does not match the chain being resumed") as err:
        chain.run_chain(spec, repo_root=root, outdir=out, resume=True)
    assert "added: B" in str(err.value)


def test_resume_tolerates_the_deleted_data_of_a_succeeded_stage(library, fake_runs, tmp_path):
    from test_sheetgen import pair
    data = tmp_path / "reads"
    a1, a2 = pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    root, spec, out = _generated_stage(library, tmp_path, fake_runs, [str(a1), str(a2)])
    a1.unlink()
    a2.unlink()
    assert chain.run_chain(spec, repo_root=root, outdir=out, resume=True).outcome == "success"


def test_resume_tolerates_data_removed_from_a_kept_directory(library, fake_runs, tmp_path):
    from test_sheetgen import pair
    data = tmp_path / "reads"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    pair(data, "B_R1.fastq.gz", "B_R2.fastq.gz")
    root, spec, out = _generated_stage(library, tmp_path, fake_runs, str(data))
    for f in data.glob("B_*"):
        f.unlink()
    assert chain.run_chain(spec, repo_root=root, outdir=out, resume=True).outcome == "success"
    for f in data.glob("A_*"):
        f.unlink()
    assert chain.run_chain(spec, repo_root=root, outdir=out, resume=True).outcome == "success"
