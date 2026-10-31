"""nfclaw's MCP tools (runner.mcp_tools): arguments become the CLI command a person would type, docs
are served as they are, and runs become detached jobs followed through `nfclaw status`.

Job tests swap the CLI for a small stand-in script (FAKE_NFCLAW) so a "run" can be made to refuse,
succeed or hang on demand; one test runs the real CLI to prove the job path reaches it unmodified.
Nothing here needs an initialised submodule, Nextflow or Docker.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

from runner import jobs, mcp_tools
from runner.mcp_server import Context, RpcError

ROOT = Path(__file__).resolve().parent.parent

# Stands in for `python -m runner`: `run` refuses (--mode=refuse), succeeds after writing its run
# log (--mode=succeed), or writes the log and waits for SIGTERM (--mode=hang); `status` reads
# that log.
FAKE_NFCLAW = textwrap.dedent("""
    import os, signal, sys, time
    from pathlib import Path
    argv = sys.argv[1:]
    opts = dict(a[2:].split("=", 1) for a in argv if a.startswith("--") and "=" in a)
    if argv[0] == "status":
        log = Path(argv[1]) / "provenance" / "logs" / "run.log"
        text = log.read_text() if log.is_file() else ""
        if "finished" in text and "success" in text:
            print("status: success"); sys.exit(0)
        if "finished" in text:
            print("status: terminated by SIGTERM"); sys.exit(1)
        if text:
            print("status: running (nfclaw pid 1 on host)"); sys.exit(3)
        print("status: no run log"); sys.exit(1)
    if argv[0] == "chain":
        print("chain:", " ".join(argv)); sys.exit(0)
    print("argv:", " ".join(argv), flush=True)
    if "--check" in argv:
        print("nextflow run pipelines/demo/upstream -profile docker"); sys.exit(0)
    mode = opts.get("mode", "succeed")
    if mode == "refuse":
        print("[params_invalid] Parameters failed validation", file=sys.stderr); sys.exit(1)
    log = Path(opts["outdir"]) / "provenance" / "logs" / "run.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("==> nfclaw run started 2026-10-26T00:00:00Z\\n")
    with log.open("a") as fh:
        fh.write(f"    pid: {os.getpid()}\\n")
    if mode == "hang":
        def stop(*_):
            with log.open("a") as fh:
                fh.write("==> nfclaw run finished 2026-10-26T00:00:01Z: terminated by SIGTERM\\n")
            sys.exit(143)
        signal.signal(signal.SIGTERM, stop)
        while True:
            time.sleep(0.1)
    with log.open("a") as fh:
        fh.write("==> nfclaw run finished 2026-10-26T00:00:01Z: success\\n")
""")


@pytest.fixture
def tools(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_STATE_DIR", str(tmp_path / "state"))
    return mcp_tools.NfclawTools(ROOT, cwd=str(tmp_path))


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    script = tmp_path / "fake_nfclaw.py"
    script.write_text(FAKE_NFCLAW)
    monkeypatch.setattr(jobs, "cli_command", lambda argv: [sys.executable, str(script), *argv])


def call(tools, name, **arguments):
    return tools.call_tool(name, arguments, Context())


def text(result) -> str:
    return result["content"][0]["text"]


# --- arguments -> the nfclaw command line ---------------------------------------------------------

def test_run_arguments_become_one_token_per_cli_option(tools):
    argv = tools.run_argv({
        "pipeline": "rnaseq", "outdir": "/data/out", "input": ["/data/a.fq.gz", "/data/b.fq.gz"],
        "sheet_set": {"strandedness": "auto"}, "params": {"genome": "GRCh38", "skip_qc": True,
                                                           "min_reads": 1000, "ratio": 0.1},
        "params_file": "/p.json", "profile": "test,docker", "pipeline_version": "3.14.0",
        "nxf_ver": "25.10.4", "nxf_env": {"NXF_OFFLINE": "true"}, "config": ["/c.config"],
        "limit_cpus": 4, "limit_memory": "15.GB", "limit_time": "1.h", "timeout_seconds": 60,
        "demo": True, "resume": True, "check": True, "allow_spaces": True, "no_provenance": True})
    assert argv == [
        "run", "rnaseq", "--outdir=/data/out", "--input=/data/a.fq.gz", "--input=/data/b.fq.gz",
        "--sheet-set=strandedness=auto", "--profile=test,docker", "--pipeline-version=3.14.0",
        "--nxf-ver=25.10.4", "--limit-memory=15.GB", "--limit-time=1.h", "--params-file=/p.json",
        "--nxf-env=NXF_OFFLINE=true", "--config=/c.config", "--limit-cpus=4", "--timeout=60",
        "--demo", "--resume", "--check", "--allow-spaces", "--no-provenance",
        "--genome=GRCh38", "--skip_qc=true", "--min_reads=1000", "--ratio=0.1"]


def test_paths_resolve_against_the_servers_directory_and_input_is_left_as_given(tools, tmp_path):
    argv = tools.run_argv({"pipeline": "fetchngs", "outdir": "out", "input": "ids.csv",
                           "params_file": "p.json"})
    assert f"--outdir={tmp_path.resolve() / 'out'}" in argv
    assert f"--params-file={tmp_path.resolve() / 'p.json'}" in argv
    assert "--input=ids.csv" in argv          # an accession, URL or glob is the CLI's to interpret


def test_a_value_that_looks_like_an_option_stays_a_value(tools):
    argv = tools.run_argv({"pipeline": "demo", "outdir": "/o", "params": {"extra_args": "--foo 1"}})
    assert argv[-1] == "--extra_args=--foo 1"


@pytest.mark.parametrize("params, message", [
    ({"outdir": "/x"}, "nfclaw option"),
    ({"nxf-ver": "25.10.4"}, "nfclaw option"),
    ({"resume": True}, "nfclaw option"),
    ({"genome": ["a", "b"]}, "string, number or boolean"),
    ({"genome": None}, "omit a parameter"),
    ({"ratio": float("nan")}, "finite"),
    ({"bad key": 1}, "not a parameter name"),
])
def test_parameters_that_cannot_be_passed_are_refused_with_the_fix(tools, params, message):
    with pytest.raises(mcp_tools.ToolError, match=message):
        tools.run_argv({"pipeline": "demo", "outdir": "/o", "params": params})


def test_an_unknown_pipeline_is_refused_before_anything_runs(tools):
    result = call(tools, "run_pipeline", pipeline="nosuch", outdir="/o")
    assert result["isError"] and "unknown pipeline" in text(result)


def test_arguments_are_checked_against_the_tool_schema(tools):
    result = call(tools, "run_pipeline", pipeline="demo", limit_cpus="4", wait_seconds=9999,
                  colour="blue")
    message = text(result)
    assert result["isError"]
    for expected in ("unknown argument 'colour'", "missing required argument 'outdir'",
                     "'limit_cpus' must be an integer", "'wait_seconds' must be <= 600"):
        assert expected in message


def test_a_null_argument_counts_as_omitted(tools):
    result = call(tools, "list_pipelines", query=None, limit=None)
    assert not result.get("isError") and len(result["structuredContent"]["pipelines"]) == 25
    missing = call(tools, "run_pipeline", pipeline="demo", outdir=None)
    assert missing["isError"] and "missing required argument 'outdir'" in text(missing)


def test_chain_arguments_become_the_chain_command(tools, tmp_path):
    spec = tmp_path / "spec.json"
    assert tools.chain_argv({"outdir": "/c", "check": True, "timeout_seconds": 5}, spec) == \
        ["chain", "run", str(spec), "--outdir=/c", "--check", "--timeout=5"]
    assert tools.chain_argv({"outdir": "/c", "resume": True}, None) == \
        ["chain", "run", "--outdir=/c", "--resume"]


# --- discovery and docs ---------------------------------------------------------------------------

def test_list_pipelines_ranks_the_named_pipeline_first(tools):
    for query, first in (("rna-seq", "rnaseq"), ("RNAseq", "rnaseq"), ("sarek", "sarek"),
                         ("fetchngs", "fetchngs")):
        result = call(tools, "list_pipelines", query=query, limit=3)
        assert result["structuredContent"]["pipelines"][0]["name"] == first, query


def test_list_pipelines_without_a_query_lists_the_library_up_to_the_limit(tools):
    catalog = json.loads((ROOT / "catalog.json").read_text())
    result = call(tools, "list_pipelines", limit=5)
    assert result["structuredContent"]["total"] == len(catalog)
    assert len(result["structuredContent"]["pipelines"]) == 5
    # A model that listed the library without a query read the first page as the whole of it.
    text = result["content"][0]["text"]
    assert f"{len(catalog) - 5} more not shown" in text and "query" in text and "limit" in text
    narrow = call(tools, "list_pipelines", query="sarek")
    assert "more not shown" not in narrow["content"][0]["text"]


def test_every_tool_is_loaded_up_front_by_antigravity(tools):
    # Antigravity defers MCP tools behind one generic call tool, and its model then called them
    # without reading their schemas (list_pipelines with no query, a made-up `validate_only`) or
    # with the call tool's own `toolSummary` inside their arguments — every deferred call, in
    # every session. Loaded up front, a tool is called with its own schema.
    tools_listed = tools.list_tools(Context())
    assert all((t.get("_meta") or {}).get("antigravity/alwaysLoad") is True for t in tools_listed)
    assert len(tools_listed) == 14


def test_list_pipelines_reports_no_match(tools):
    result = call(tools, "list_pipelines", query="zzqqxx")
    assert result["structuredContent"] == {"total": 0, "pipelines": []}


def test_show_pipeline_returns_the_skill_as_committed(tools):
    result = call(tools, "show_pipeline", pipeline="demo")
    assert text(result) == (ROOT / "pipelines" / "demo" / "skill.md").read_text()


def test_show_pipeline_grep_keeps_headings_and_table_headers(tools):
    out = text(call(tools, "show_pipeline", pipeline="rnaseq", document="reference",
                    grep="aligner"))
    lines = out.splitlines()
    assert any(ln.startswith("#") for ln in lines)
    assert any(ln.startswith("| parameter") for ln in lines)
    assert any("--aligner" in ln for ln in lines)
    reference = (ROOT / "pipelines" / "rnaseq" / "reference.md").read_text()
    assert len(out) < len(reference) / 4


def test_show_pipeline_grep_without_a_match_says_so(tools):
    assert "No line" in text(call(tools, "show_pipeline", pipeline="demo", grep="zzqqxx"))


def test_read_doc_finds_the_sections_about_a_warning(tools):
    # known-issues.md is about 120 KB: an agent checking one warning gets its section, not the file.
    out = text(call(tools, "read_doc", guide="known-issues",
                    search="Unrecognized config option manifest.diagram"))
    whole = (ROOT / "docs" / "known-issues.md").read_text()
    assert out.startswith("1 section(s) of docs/known-issues.md contain all of:")
    assert "### `WARN: Unrecognized config option 'manifest.diagram'`" in out
    assert len(out) < len(whole) / 50


def test_read_doc_without_a_match_lists_the_headings_to_search_again(tools):
    out = text(call(tools, "read_doc", guide="known-issues", search="zzqqxx"))
    assert out.startswith("No section of docs/known-issues.md contains all of: zzqqxx")
    assert "## Warnings a run prints that are not faults" in out


def test_read_doc_returns_a_whole_guide_and_refuses_an_unknown_one(tools):
    assert text(call(tools, "read_doc", guide="chaining")) == \
        (ROOT / "docs" / "chaining.md").read_text()
    assert text(call(tools, "read_doc", guide="chaining.md")) == \
        (ROOT / "docs" / "chaining.md").read_text()
    refused = call(tools, "read_doc", guide="../AGENTS")
    assert refused["isError"] and "unknown guide" in text(refused)


def test_section_search_ignores_headings_inside_code_blocks():
    doc = ("# Guide\n\n## Install\n\n```bash\n# not a heading: pip install\n```\n"
           "then run it\n\n## Other\n\nnothing\n")
    out = mcp_tools._search_sections(doc, "pip run", "doc.md")
    assert out.startswith("1 section(s) of doc.md")
    assert "## Install" in out and "then run it" in out and "## Other" not in out


def test_resources_serve_the_guide_catalog_docs_and_every_skill(tools):
    ctx = Context()
    uris = {r["uri"] for r in tools.list_resources(ctx)}
    assert {"nfclaw://guide", "nfclaw://catalog", "nfclaw://docs/chaining",
            "nfclaw://docs/mcp", "nfclaw://pipelines/rnaseq/skill"} <= uris
    [content] = tools.read_resource("nfclaw://pipelines/sarek/reference", ctx)
    assert content["text"] == (ROOT / "pipelines" / "sarek" / "reference.md").read_text()
    assert tools.read_resource("nfclaw://guide", ctx)[0]["text"] == \
        (ROOT / "AGENTS.md").read_text()


@pytest.mark.parametrize("uri", [
    "nfclaw://pipelines/../AGENTS/skill", "nfclaw://pipelines/nosuch/skill",
    "nfclaw://docs/../README", "nfclaw://docs/nosuch", "nfclaw://pipelines/demo/upstream",
    "file:///etc/passwd", "nfclaw://pipelines/demo/skill/../../../x",
])
def test_resources_outside_the_library_are_not_found(tools, uri):
    with pytest.raises(RpcError) as err:
        tools.read_resource(uri, Context())
    assert err.value.code == -32002


def test_the_prompt_carries_the_pipeline_skill(tools):
    prompt = tools.get_prompt("use_pipeline", {"pipeline": "demo", "goal": "QC my reads"},
                              Context())
    body = prompt["messages"][0]["content"]["text"]
    assert "QC my reads" in body
    assert (ROOT / "pipelines" / "demo" / "skill.md").read_text() in body
    with pytest.raises(RpcError):
        tools.get_prompt("use_pipeline", {"pipeline": "../x"}, Context())


# --- jobs -----------------------------------------------------------------------------------------

def test_a_refused_launch_is_reported_inline_with_the_cli_error(tools, fake_cli, tmp_path):
    result = call(tools, "run_pipeline", pipeline="demo", outdir=str(tmp_path / "o"),
                  params={"mode": "refuse"}, wait_seconds=30)
    view = result["structuredContent"]
    assert result["isError"] and view["state"] == "failed" and view["exit_code"] == 1
    assert "[params_invalid]" in text(result)
    assert "status_report" not in view                  # it never reached a run log


def test_a_successful_run_is_followed_to_its_status_report(tools, fake_cli, tmp_path):
    outdir = tmp_path / "o"
    submitted = call(tools, "run_pipeline", pipeline="demo", outdir=str(outdir), wait_seconds=30)
    job_id = submitted["structuredContent"]["job_id"]
    assert submitted["structuredContent"]["command"].startswith("nfclaw run demo --outdir=")
    result = call(tools, "get_job", job_id=job_id, wait_seconds=30)
    view = result["structuredContent"]
    assert not result.get("isError")
    assert view["state"] == "succeeded" and view["run_state"] == "success"
    assert view["status_report"].splitlines()[0] == "status: success"
    assert view["log"] == str(outdir / "provenance" / "logs" / "run.log")
    assert any("argv: run demo" in line for line in view["output_tail"])


def test_a_running_job_is_launched_and_cancel_stops_it_cleanly(tools, fake_cli, tmp_path):
    outdir = tmp_path / "o"
    submitted = call(tools, "run_pipeline", pipeline="demo", outdir=str(outdir),
                     params={"mode": "hang"}, wait_seconds=30)
    view = submitted["structuredContent"]
    assert view["state"] == "running" and view["phase"] == "launched"
    # A second run into the same directory is refused while the first holds it.
    again = call(tools, "run_pipeline", pipeline="demo", outdir=str(outdir), wait_seconds=0)
    assert again["isError"] and view["job_id"] in text(again)
    listed = call(tools, "list_jobs", state="running")["structuredContent"]["jobs"]
    assert [j["job_id"] for j in listed] == [view["job_id"]]
    stopped = call(tools, "cancel_job", job_id=view["job_id"], wait_seconds=30)
    final = stopped["structuredContent"]
    assert final["state"] == "cancelled" and final["exit_code"] == 143
    assert final["status_report"].splitlines()[0] == "status: terminated by SIGTERM"
    again = call(tools, "cancel_job", job_id=view["job_id"])
    assert "not running" in text(again)


def test_a_check_job_returns_the_command_it_would_run(tools, fake_cli, tmp_path):
    result = call(tools, "run_pipeline", pipeline="demo", outdir=str(tmp_path / "o"), check=True,
                  wait_seconds=30)
    view = result["structuredContent"]
    assert view["state"] == "succeeded" and view["check"]
    assert "nextflow run pipelines/demo/upstream -profile docker" in view["output_tail"]
    assert not (tmp_path / "o").exists()
    assert "without check" in view["next"]


def test_a_chain_job_runs_the_chain_command_on_the_written_spec(tools, fake_cli, tmp_path):
    spec = {"stages": [{"pipeline": "demultiplex", "demo": True},
                       {"pipeline": "seqinspector", "demo": True}]}
    result = call(tools, "run_chain", spec=spec, outdir=str(tmp_path / "c"), check=True,
                  wait_seconds=30)
    view = result["structuredContent"]
    job = jobs.load(view["job_id"])
    assert json.loads((job.dir / "spec.json").read_text()) == spec
    assert job.argv == ["chain", "run", str(job.dir / "spec.json"),
                        f"--outdir={tmp_path.resolve() / 'c'}", "--check"]
    assert view["state"] == "succeeded"
    assert call(tools, "run_chain", outdir=str(tmp_path / "c"))["isError"]   # spec or resume


def test_get_job_of_an_unknown_id_is_a_failed_call(tools):
    result = call(tools, "get_job", job_id="20261016T000000-demo-abcdef")
    assert result["isError"] and "no such job" in text(result)


def test_a_job_reaches_the_real_cli(tools, tmp_path):
    # No stand-in: the job runs `python -m runner run …` itself. An invalid engine version is
    # refused by the CLI's own argument parser — before any submodule, network or engine is needed.
    result = call(tools, "run_pipeline", pipeline="demo", outdir=str(tmp_path / "o"),
                  nxf_ver="not-a-version", check=True, wait_seconds=60)
    view = result["structuredContent"]
    assert view["state"] == "failed" and view["exit_code"] == 2
    assert any("--nxf-ver" in line for line in view["output_tail"])


def test_run_status_reports_a_directory_nfclaw_never_ran_in(tools, tmp_path):
    result = call(tools, "run_status", outdir=str(tmp_path / "never"))
    assert result["structuredContent"]["state"] == "not successful"
    assert "no run log" in text(result)


def test_inline_chain_spec_retains_exact_numbers_in_durable_spec(tools, fake_cli, tmp_path):
    from decimal import Decimal
    from runner import exact_json
    spec = exact_json.loads('{"stages":[{"pipeline":"demo","params":'
                            '{"ratio":0.1000000000000000000001,"tiny":1e-9999}}]}')
    result = call(tools, 'run_chain', spec=spec, outdir=str(tmp_path / 'chain'),
                  check=True, wait_seconds=1)
    assert not result.get('isError'), result
    job = jobs.load(result['structuredContent']['job_id'])
    observed = json.loads((job.dir / 'spec.json').read_text(), parse_float=Decimal)
    assert observed['stages'][0]['params'] == {
        'ratio': Decimal('0.1000000000000000000001'), 'tiny': Decimal('1e-9999')}


def test_a_finished_job_without_its_status_report_says_why(tools, fake_cli, tmp_path):
    # The supervisor could not retain the run's own report: the view says so instead of
    # silently omitting it.
    submitted = call(tools, "run_pipeline", pipeline="demo", outdir=str(tmp_path / "o"),
                     wait_seconds=30)
    job_id = submitted["structuredContent"]["job_id"]
    call(tools, "get_job", job_id=job_id, wait_seconds=30)
    job_dir = jobs.jobs_dir() / job_id
    (job_dir / jobs.STATUS_FILE).unlink()
    record = json.loads((job_dir / jobs.SUPERVISOR_FILE).read_text())
    record["status_error"] = "could not freeze this job's run status: OSError: disk full"
    (job_dir / jobs.SUPERVISOR_FILE).write_text(json.dumps(record))
    result = call(tools, "get_job", job_id=job_id)
    view = result["structuredContent"]
    assert view["state"] == "succeeded" and "status_report" not in view
    assert view["status_error"] == record["status_error"]
    assert "status: could not freeze this job's run status" in result["content"][0]["text"]


def test_finished_job_keeps_its_own_status_when_a_retry_reuses_the_outdir(
        tools, fake_cli, tmp_path):
    out = str(tmp_path / 'retry-out')
    first = call(tools, 'run_pipeline', pipeline='demo', outdir=out, wait_seconds=30)
    first_id = first['structuredContent']['job_id']
    assert call(tools, 'get_job', job_id=first_id, wait_seconds=30)['structuredContent'][
        'run_state'] == 'success'
    second = call(tools, 'run_pipeline', pipeline='demo', outdir=out, resume=True,
                  params={'mode': 'hang'}, wait_seconds=30)
    second_id = second['structuredContent']['job_id']
    try:
        old = call(tools, 'get_job', job_id=first_id)['structuredContent']
        assert old['state'] == 'succeeded'
        assert old['run_state'] == 'success'
        assert old['status_report'].splitlines()[0] == 'status: success'
    finally:
        call(tools, 'cancel_job', job_id=second_id, wait_seconds=30)


def test_mcp_can_require_complete_environment_evidence(tools, tmp_path):
    original, replay = tmp_path / 'original', tmp_path / 'replay'
    original.mkdir()
    replay.mkdir()
    result = call(tools, 'verify_replay', replay=str(replay), against=str(original),
                  require_environment=True)
    assert not result.get('isError'), result
    assert result['structuredContent']['passed'] is False
    assert 'environment' in result['structuredContent']['report']


def test_structured_params_are_merged_privately_without_losing_precision(
        tools, fake_cli, tmp_path):
    import stat
    from decimal import Decimal
    source = tmp_path / 'base.json'
    source.write_text('{"label":"base","values":["base"],"keep":7}')
    result = call(tools, 'run_pipeline', pipeline='demo', outdir=str(tmp_path / 'out'),
                  params_file=str(source), check=True, wait_seconds=30,
                  params={'values': ['A', 'B'], 'label': 'override',
                          'settings': {'threshold': Decimal('0.1000000000000000000001'),
                                       'enabled': True}})
    assert not result.get('isError'), result
    job = jobs.load(result['structuredContent']['job_id'])
    file_arg = next(arg for arg in job.argv if arg.startswith('--params-file='))
    generated = Path(file_arg.split('=', 1)[1])
    assert generated.is_relative_to(job.dir)
    observed = json.loads(generated.read_text(), parse_float=Decimal)
    assert observed == {'label': 'override', 'values': ['A', 'B'], 'keep': 7,
                        'settings': {'threshold': Decimal('0.1000000000000000000001'),
                                     'enabled': True}}
    assert stat.S_IMODE(generated.stat().st_mode) == 0o600
    assert json.loads(source.read_text()) == {'label': 'base', 'values': ['base'], 'keep': 7}


@pytest.mark.parametrize('cancel', [False, True])
@pytest.mark.usefixtures('no_engine_probe')
def test_replays_use_the_job_supervisor_and_can_be_cancelled(tools, tmp_path, cancel):
    from runner import provenance
    from runner.submodule import SubmoduleStatus
    assert 'replay_run' in {tool['name'] for tool in tools.list_tools(Context())}
    original = tmp_path / 'original'
    provenance.write(outdir=original, pipeline='fixture',
        command_str="bash -c 'sleep 60'" if cancel else 'printf replayed > result.txt',
        submodule=SubmoduleStatus('fixture', tmp_path / 'up', True, True, '1', 'abc', ()),
        input_paths=[])
    replay = tmp_path / 'replay'
    submitted = call(tools, 'replay_run', original=str(original), outdir=str(replay),
                     wait_seconds=10)
    assert not submitted.get('isError'), submitted
    job_id = submitted['structuredContent']['job_id']
    final = call(tools, 'cancel_job' if cancel else 'get_job', job_id=job_id,
                 wait_seconds=30)['structuredContent']
    assert final['kind'] == 'replay'
    assert final['state'] == ('cancelled' if cancel else 'succeeded')
    if not cancel:
        assert (replay / 'result.txt').read_text() == 'replayed'
        assert final['run_state'] == 'success'
    else:
        assert 'resume=true' not in final['next']


def _artifact_job(tools, tmp_path):
    assert 'read_artifact' in {tool['name'] for tool in tools.list_tools(Context())}
    out = tmp_path / 'artifacts'
    result = call(tools, 'run_pipeline', pipeline='demo', outdir=str(out), check=True,
                  wait_seconds=30)
    out.mkdir()
    return result['structuredContent']['job_id'], out


def test_artifact_previews_are_bounded_and_report_truncation(tools, fake_cli, tmp_path):
    job_id, out = _artifact_job(tools, tmp_path)
    (out / 'counts.tsv').write_text('gene\tcount\nA\t10\n')
    result = call(tools, 'read_artifact', job_id=job_id, path='counts.tsv', max_bytes=8)
    assert not result.get('isError'), result
    data = result['structuredContent']
    assert data['text'] == 'gene\tcou'
    assert data['truncated'] is True and data['returned_bytes'] == 8
    assert data['size_bytes'] == 16


@pytest.mark.parametrize('kind', ['parent', 'absolute', 'symlink', 'binary'])
def test_artifact_previews_refuse_escape_routes_and_binary_files(
        tools, fake_cli, tmp_path, kind):
    job_id, out = _artifact_job(tools, tmp_path)
    secret = tmp_path / 'private.txt'
    secret.write_text('PRIVATE_BYTES_MUST_NOT_ESCAPE')
    path = '../private.txt' if kind == 'parent' else str(secret) if kind == 'absolute' else 'link'
    if kind == 'symlink':
        (out / path).symlink_to(secret)
    if kind == 'binary':
        (out / path).write_bytes(b'\x00\xff\x01')
    result = call(tools, 'read_artifact', job_id=job_id, path=path)
    assert result.get('isError'), result
    assert 'PRIVATE_BYTES_MUST_NOT_ESCAPE' not in text(result)


def test_artifact_preview_cannot_escape_when_an_ancestor_is_swapped(
        tools, fake_cli, tmp_path, monkeypatch):
    import os
    job_id, out = _artifact_job(tools, tmp_path)
    folder = out / 'reports'
    folder.mkdir()
    (folder / 'counts.tsv').write_text('safe counts')
    outside = tmp_path / 'private'
    outside.mkdir()
    (outside / 'counts.tsv').write_text('PRIVATE_BYTES_MUST_NOT_ESCAPE')
    original_open = os.open
    swapped = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and str(path).endswith('counts.tsv'):
            swapped = True
            folder.rename(out / 'original-reports')
            folder.symlink_to(outside, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, 'open', racing_open)
    result = call(tools, 'read_artifact', job_id=job_id, path='reports/counts.tsv')
    assert swapped
    assert 'PRIVATE_BYTES_MUST_NOT_ESCAPE' not in text(result)
    assert result.get('isError') or result['structuredContent']['text'] == 'safe counts'


def test_run_status_carries_the_parsed_status_record(tools, tmp_path):
    # Clients branch on how a run ended (`failed (exit status 1)`, `timed out …`, a stop) without
    # parsing prose: the structured content carries `nfclaw status --json`'s record.
    logs = tmp_path / "out" / "provenance" / "logs"
    logs.mkdir(parents=True)
    (logs / "run.log").write_text(
        "==> nfclaw run started 2026-10-30T00:00:00+00:00\n"
        "    console format: prefixed\n"
        "    pid: 1\n"
        "| N E X T F L O W  ~  version 26.04.3\n"
        "==> nfclaw error:\n"
        "| Nextflow execution failed (exit status 1).\n"
        "==> nfclaw run finished 2026-10-30T00:01:00+00:00: failed (exit status 1)\n")
    result = call(tools, "run_status", outdir=str(tmp_path / "out"))
    view = result["structuredContent"]
    assert view["state"] == "not successful" and view["exit_code"] == 1
    assert view["run"]["state"] == "ended"
    assert view["run"]["outcome"] == "failed (exit status 1)"
    assert view["run"]["error"] == ["Nextflow execution failed (exit status 1)."]
    assert view["report"] == text(result) == view["run"]["report"].rstrip("\n")
    assert text(result).startswith("status: failed (exit status 1)")


def test_run_status_of_a_missing_chain_says_why_once(tools, tmp_path):
    # `chain status --json` refuses a directory that holds no chain with the same record shape as
    # a found one; the refusal is both its report and its stderr, and the model reads it once.
    result = call(tools, "run_status", outdir=str(tmp_path / "none"), chain=True)
    view = result["structuredContent"]
    assert view["exit_code"] == 1 and view["run"]["chain"] is None
    assert len(view["run"]["error"]) == 1 and "no chain recorded" in view["run"]["error"][0]
    assert text(result).count("no chain recorded") == 1
