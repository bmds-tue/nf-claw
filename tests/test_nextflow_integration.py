"""Real-engine validation using a deterministic, local fixture with an independent oracle.

This exercises nfclaw's execution contract; it makes no claim about biological algorithms.
"""
import hashlib
import json
import os
import shutil
import subprocess

import pytest

from runner import chain, orchestration, resources, runlog, verify


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_execution_writes_are_separated_from_directory_inputs(tmp_path, engine):
    from runner.errors import NfclawError
    from test_input_output_separation import run, tree
    root = tree(tmp_path)
    data = tmp_path / "data"
    (data / "sample_A").mkdir(parents=True)
    (data / "index.bin").write_bytes(b"fixed scientific input")
    before = data.stat().st_mtime_ns
    for output, environment in ((data / "analysis", {}),
                                (tmp_path / "unsafe_work", {"NXF_WORK": str(data / "work")})):
        with pytest.raises(NfclawError, match="overlaps local dependency"):
            run(root, data, output, nxf_ver=engine, nxf_env=environment)
        assert not output.exists()
        assert not (output.parent / f".{output.name}.nfclaw.lock").exists()
        assert sorted(p.name for p in data.iterdir()) == ["index.bin", "sample_A"]
        assert data.stat().st_mtime_ns == before
    safe = tmp_path / "safe"
    result = run(root, data, safe, nxf_ver=engine)
    assert not result.checked_only
    assert (safe / "entries.txt").read_text() == "index.bin\nsample_A\n"
    assert runlog.read_state(safe / "provenance/logs/run.log").state == "success"
    replay = subprocess.run(["bash", str(safe / "provenance/commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=90)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert verify.compare(safe, tmp_path / "replay").byte_identical
    assert (data / "index.bin").read_bytes() == b"fixed scientific input"
    assert sorted(p.name for p in data.iterdir()) == ["index.bin", "sample_A"]
    assert data.stat().st_mtime_ns == before


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_staged_file_alias_names_survive_run_replay_and_reference_handoff(tmp_path, engine):
    root = tmp_path / "library"
    upstream = root / "pipelines/fixture/upstream"
    upstream.mkdir(parents=True)
    (upstream.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (upstream / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "exists": True, "pattern": r"\.csv$"},
        "reference": {"type": "string", "format": "file-path", "exists": True, "pattern": r"\.csv$"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    (upstream / "nextflow.config").write_text(
        "nextflow.enable.dsl=2\nprofiles { standard { process.executor = 'local' } }\n")
    (upstream / "main.nf").write_text('''process OBSERVE {
 publishDir params.outdir, mode: 'copy'
 input:
 path data
 output:
 path 'observed.txt'
 script:
 """
 printf '%s\\n' ${data.name} > observed.txt
 shasum -a 256 ${data} >> observed.txt
 """
}
workflow { OBSERVE(Channel.fromPath(params.input)) }
''')
    target = tmp_path / "stored.data"
    target.write_bytes(b"sample,count\nS,17\n")
    primary, reference = tmp_path / "samples.csv", tmp_path / "reference.csv"
    primary.symlink_to("stored.data")
    reference.symlink_to("stored.data")
    options = dict(repo_root=root, profile="standard", params_file=None,
                   cli_overrides={"reference": str(reference)}, resume=False, demo=False,
                   check_only=False, write_provenance=True, timeout_seconds=90, nxf_ver=engine)
    out = tmp_path / "run"
    orchestration.run_pipeline("fixture", input_path=primary, outdir=out, **options)
    digest = hashlib.sha256(b"sample,count\nS,17\n").hexdigest()
    assert (out / "observed.txt").read_text() == f"samples.csv\n{digest}  samples.csv\n"
    recorded = json.loads((out / "provenance/params.json").read_text())
    assert recorded["input"] == str(primary) and recorded["reference"] == str(reference)
    nodes = json.loads((out / "provenance/inputs.inventory.json").read_text())
    assert nodes[str(primary)]["link_target"] == "stored.data"
    assert nodes[str(reference)]["link_target"] == "stored.data"
    replay = subprocess.run(["bash", str(out / "provenance/commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=90)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert verify.compare(out, tmp_path / "replay").byte_identical
    spec = chain.parse_spec({"profile": "standard", "nxf_ver": engine, "stages": [
        {"pipeline": "fixture", "input": str(primary), "params": {"reference": str(reference)}},
        {"pipeline": "fixture", "id": "consumer", "handoff": {"params": {
            "input": {"upstream_param": "reference"}}}}]})
    chained = tmp_path / "chain"
    result = chain.run_chain(spec, repo_root=root, outdir=chained, timeout_seconds=120)
    assert result.outcome == "success"
    assert (chained / "02-consumer/observed.txt").read_text() == f"reference.csv\n{digest}  reference.csv\n"
    state, problems = chain.status(chained)
    assert problems == [] and chain.status_exit_code(state, problems) == 0
    # Identical data cannot hide a retargeted alias from the stored dependency identity.
    second = tmp_path / "second.data"
    second.write_bytes(target.read_bytes())
    reference.unlink()
    reference.symlink_to("second.data")
    refused = subprocess.run(["bash", str(out / "provenance/commands.sh"), str(tmp_path / "refused")],
                             capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and "dependency check failed" in refused.stderr
    assert not (tmp_path / "refused/observed.txt").exists()
    assert not (tmp_path / "refused/.nextflow").exists()
    assert list((tmp_path / "refused").iterdir()) == []
    state, problems = chain.status(chained)
    assert problems and chain.status_exit_code(state, problems) == 1


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
def test_real_run_relocated_replay_and_mutated_input_guard(tmp_path, tmp_path_factory):
    root = tmp_path / "library"
    upstream = root / "pipelines/fixture/upstream"
    upstream.mkdir(parents=True)
    (upstream.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (upstream / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "exists": True},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    (upstream / "nextflow.config").write_text(
        "nextflow.enable.dsl=2\nprofiles { standard { process.executor = 'local' } }\n")
    (upstream / "main.nf").write_text('''process DIGEST {
    publishDir params.outdir, mode: 'copy'
    input:
    path data
    output:
    path 'result'
    script:
    """
    mkdir result
    shasum -a 256 ${data} > result/digest.txt
    """
}
workflow {
    DIGEST(Channel.fromPath(params.input))
}
''')
    data = tmp_path / "data.txt"
    data.write_bytes(b"known deterministic input\n")
    out = tmp_path_factory.mktemp("real-run") / "results"
    result = orchestration.run_pipeline(
        "fixture", repo_root=root, input_path=data, outdir=out, profile="",
        params_file=None, cli_overrides={}, resume=False, demo=False, check_only=False,
        write_provenance=True, timeout_seconds=90, nxf_ver="25.10.4",
        limits=resources.parse(1, None, None))
    expected = hashlib.sha256(data.read_bytes()).hexdigest() + "  data.txt\n"
    assert (out / "result/digest.txt").read_text() == expected
    assert result.outputs_report.files == ("result/digest.txt",)
    assert runlog.read_state(out / "provenance/logs/run.log").state == "success"
    relocated = out.with_name("archive")
    out.rename(relocated)
    # Relative script path plus a relocated bundle exercise both path-resolution boundaries.
    script = "archive/provenance/commands.sh"
    replay = subprocess.run(["bash", script, "replay"], cwd=relocated.parent,
                            capture_output=True, text=True, timeout=90)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    comparison = verify.compare(relocated, relocated.parent / "replay")
    assert comparison.byte_identical
    assert comparison.identical == ["result/digest.txt"]
    data.write_bytes(b"changed scientific input\n")
    refused = subprocess.run(["bash", script, "refused"], cwd=relocated.parent,
                             capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0
    assert "dependency check failed" in refused.stderr
    assert not (relocated.parent / "refused/result/digest.txt").exists()
    spec = chain.parse_spec({"profile": "standard", "nxf_ver": "25.10.4", "stages": [
        {"pipeline": "fixture", "input": str(data)},
        {"pipeline": "fixture", "id": "second",
         "handoff": {"params": {"input": {"file": "result/digest.txt"}}}}]})
    chain_out = relocated.parent / "chain"
    result = chain.run_chain(spec, repo_root=root, outdir=chain_out, timeout_seconds=120)
    assert result.outcome == "success"
    first_digest = hashlib.sha256(data.read_bytes()).hexdigest() + "  data.txt\n"
    expected_second = hashlib.sha256(first_digest.encode()).hexdigest() + "  digest.txt\n"
    assert (chain_out / "02-second/result/digest.txt").read_text() == expected_second
    state, problems = chain.status(chain_out)
    assert problems == [] and chain.status_exit_code(state, problems) == 0
    (chain_out / "01-fixture/result/digest.txt").write_bytes(b"changed upstream result\n")
    state, problems = chain.status(chain_out)
    assert problems and chain.status_exit_code(state, problems) == 1
@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
def test_recorded_repair_publishers_preserve_mates_and_honor_runtime_mode(tmp_path):
    import os
    from runner import fastqrepair_compat

    fastqrepair_compat.write_config(tmp_path / "compat.config")
    (tmp_path / "nextflow.config").write_text("params.publish_dir_mode = 'copy'\nparams.outdir = 'wrong'\n")
    report = (fastqrepair_compat._zero_report().replace("(not applicable)", "(0.0%)")
              .replace("Total lines: 0", "Total lines: 12")
              .replace("Well-formed lines: 0 (0.0%)", "Well-formed lines: 12 (100.0%)")
              .replace("Clean reads: 0", "Clean reads: 3"))
    (tmp_path / "chunk.report").write_text(report)
    # The pinned recipe's shape: the recorded hook replaces its report gatherer before it runs.
    (tmp_path / "main.nf").write_text('''process WIPERTOOLS_REPORTGATHER {
 input:
 val meta
 output:
 path "${meta.id}.report"
 path 'versions.yml'
 script:
 """
 cp ''' + str(tmp_path / "chunk.report") + ''' chunk.txt
 wipertools \\\\
     reportgather \\\\
     -r chunk.txt \\\\
     -f ${meta.id}.report

 cat <<-END_VERSIONS > versions.yml
 "${task.process}":
     wipertools reportgather: \\$(wipertools reportgather --version)
 END_VERSIONS
 """
}
workflow {
 WIPERTOOLS_REPORTGATHER(channel.of([id:'left',sample_id:'paired_probe',single_end:false],
                                  [id:'right',sample_id:'paired_probe',single_end:false]))
}
''')
    result = subprocess.run(["nextflow", "run", "main.nf", "-c", "compat.config", "-ansi-log", "false",
                             "--outdir", "results", "--publish_dir_mode", "symlink"],
                            cwd=tmp_path, env={**os.environ, "NXF_VER": "25.10.4"},
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    published = tmp_path / "results/repaired/reports/paired_probe"
    assert sorted(path.name for path in published.iterdir()) == ["left.report", "right.report"]
    assert all(path.is_symlink() and path.read_text() == report for path in published.iterdir())
    assert not (tmp_path / "wrong").exists()


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_remote_staging_names_match_preflight_without_decoding(engine, tmp_path):
    """A local HTTP oracle checks actual staged bytes/names, with no unsafe interpolation."""
    import http.server
    import os
    import threading

    from runner.inputs import local_name_issues

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"known remote data\n")

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    names = ["reads$(id).txt", "reads%20space.txt", "safe.txt?token=x&y=2", "reads#fragment.txt"]
    urls = [f"http://127.0.0.1:{server.server_port}/{name}" for name in names]
    (tmp_path / "params.json").write_text(json.dumps({"inputs": urls}))
    (tmp_path / "main.nf").write_text('''process INVENTORY {
 input:
 path data
 output:
 path 'observed.tsv'
 script:
 """
 printf '%s\\n' *.txt > observed.tsv
 """
}
workflow {
 INVENTORY(channel.fromList(params.inputs).map { file(it, glob: false) })
}
''')
    try:
        result = subprocess.run(["nextflow", "run", "main.nf", "-params-file", "params.json",
                                 "-ansi-log", "false"], cwd=tmp_path,
                                env={**os.environ, "NXF_VER": engine},
                                capture_output=True, text=True, timeout=120)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = list((tmp_path / "work").rglob("observed.tsv"))
    assert sorted(path.read_text().strip() for path in outputs) == [
        "reads#fragment.txt", "reads$(id).txt", "reads%20space.txt", "safe.txt"]
    for path in outputs:
        assert (path.parent / path.read_text().strip()).read_bytes() == b"known remote data\n"
    assert local_name_issues(urls[0], "file-path")
    assert local_name_issues(urls[1], "file-path") == []
    assert local_name_issues(urls[2], "file-path") == []
    assert local_name_issues(urls[3], "file-path")
    assert local_name_issues("s3://bucket/reads.txt?x=1&y=2", "file-path")


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_directory_children_become_individual_staged_inputs(engine, tmp_path):
    import os
    from runner.inputs import local_name_issues

    source = tmp_path / "safe_directory"
    source.mkdir()
    names = ["reads$(id).txt", "safe_é.txt"]
    for name in names:
        (source / name).write_bytes(b"known directory data\n")
    (tmp_path / "params.json").write_text(json.dumps({"input": str(source)}))
    (tmp_path / "main.nf").write_text('''process INVENTORY {
 input:
 path data
 output:
 path 'observed.tsv'
 script:
 """
 printf '%s\\n' *.txt > observed.tsv
 """
}
workflow { INVENTORY(channel.fromPath(params.input + '/*.txt')) }
''')
    result = subprocess.run(["nextflow", "run", "main.nf", "-params-file", "params.json",
                             "-ansi-log", "false"], cwd=tmp_path,
                            env={**os.environ, "NXF_VER": engine},
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = list((tmp_path / "work").rglob("observed.tsv"))
    assert sorted(path.read_text().strip() for path in outputs) == sorted(names)
    for path in outputs:
        assert (path.parent / path.read_text().strip()).read_bytes() == b"known directory data\n"
    assert local_name_issues(str(source), "directory-path")
    (source / names[0]).unlink()
    assert local_name_issues(str(source), "directory-path") == []


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_empty_directory_namespace_is_guarded_and_resume_is_current(engine, tmp_path):
    import csv
    import os
    root = tmp_path / "library"
    tree = root / "pipelines/fixture/upstream"
    tree.mkdir(parents=True)
    (tree.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path", "exists": True},
        "counter": {"type": "string"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    (tree / "nextflow.config").write_text('''nextflow.enable.dsl=2
trace {
 enabled = true
 file = "${params.outdir}/pipeline_info/trace.txt"
}
''')
    (tree / "main.nf").write_text('''process NAMESPACE {
 publishDir params.outdir, mode: 'copy', overwrite: true
 input:
 path data
 output:
 path 'result'
 script:
 """
 mkdir result
 echo executed >> ${params.counter}
 find -L ${data} -mindepth 1 -maxdepth 1 -type d -print | sed 's#^.*/##' | LC_ALL=C sort > result/namespace.txt
 for sample in ${data}/*; do basename "\\$sample" > "result/\\$(basename "\\$sample").txt"; done
 """
}
workflow { NAMESPACE(file(params.input)) }
''')
    data = tmp_path / "data"
    data.mkdir()
    first = data / "sample_A"
    first.mkdir()
    stamp = data.stat()
    out = tmp_path / "analysis"
    counter = tmp_path / "executions.txt"

    def run(resume):
        return orchestration.run_pipeline("fixture", repo_root=root, input_path=data,
            outdir=out, profile="", params_file=None, cli_overrides={"counter": str(counter)}, resume=resume,
            demo=False, check_only=False, write_provenance=True, timeout_seconds=90,
            nxf_ver=engine, limits=resources.parse(1, None, None))

    run(False)
    assert (out / "result/namespace.txt").read_text() == "sample_A\n"
    assert (out / "result/sample_A.txt").read_text() == "sample_A\n"
    assert counter.read_text().splitlines() == ["executed"]
    unchanged = run(True)
    assert "-resume" in unchanged.command
    assert counter.read_text().splitlines() == ["executed"]
    script = out / "provenance/commands.sh"
    result = subprocess.run([str(script), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "replay/result/namespace.txt").read_text() == "sample_A\n"
    assert counter.read_text().splitlines() == ["executed"] * 2
    first.rename(data / "sample_B")
    os.utime(data, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert data.stat().st_size == stamp.st_size
    assert data.stat().st_mtime_ns == stamp.st_mtime_ns
    refused = subprocess.run([str(script), str(tmp_path / "refused")],
                             capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and "inventory changed" in refused.stderr
    assert not (tmp_path / "refused/result/namespace.txt").exists()
    assert counter.read_text().splitlines() == ["executed"] * 2
    changed = run(True)
    assert "-resume" not in changed.command
    assert any("all tasks will be recomputed" in warning for warning in changed.warnings)
    assert (out / "result/namespace.txt").read_text() == "sample_B\n"
    assert counter.read_text().splitlines() == ["executed"] * 3
    trace = list(csv.DictReader((out / "pipeline_info/trace.txt").read_text().splitlines(),
                               delimiter="\t"))
    assert len(trace) == 1 and trace[0]["name"] == "NAMESPACE" and trace[0]["status"] == "COMPLETED"
    assert not (out / "result/sample_A.txt").exists()
    archives = list(tmp_path.glob("analysis.previous-*"))
    assert len(archives) == 1
    assert (archives[0] / "result/sample_A.txt").read_text() == "sample_A\n"
    assert (archives[0] / "provenance/commands.sh").is_file()
    current = run(True)
    assert "-resume" in current.command
    assert (out / "result/namespace.txt").read_text() == "sample_B\n"
    assert counter.read_text().splitlines() == ["executed"] * 3


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_archiving_respects_the_real_engines_active_session_lock(engine, tmp_path):
    import os
    import signal
    import time
    from runner import resume_safety
    from runner.errors import NfclawError
    tree = tmp_path / "pipeline"
    tree.mkdir()
    (tree / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    marker = tmp_path / "task-running"
    (tree / "main.nf").write_text('''process WAIT {
 output:
 path 'result.txt'
 script:
 """
 touch ${params.marker}
 sleep 60
 echo finished > result.txt
 """
}
workflow { WAIT() }
''')
    out = tmp_path / "analysis"
    out.mkdir()
    process = subprocess.Popen(["nextflow", "run", str(tree), "--marker", str(marker),
                                "-work-dir", str(tmp_path / "work")], cwd=out,
        env={**os.environ, "NXF_VER": engine}, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 30
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        assert marker.exists(), "the real task did not start"
        assert list((out / ".nextflow/cache").glob("*/db/LOCK"))
        with pytest.raises(NfclawError, match="session is active or locked"):
            resume_safety.archive_previous_run(out, {}, [])
        assert (out / ".nextflow/cache").is_dir()
        assert not list(tmp_path.glob("analysis.previous-*"))
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=10)


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("source", ["external", "external_alias", "published", "bundle"])
def test_real_chain_refuses_changed_reference_namespace_and_resumes_after_restoration(tmp_path, monkeypatch, source):
    from runner.errors import ErrorCode, NfclawError
    root = tmp_path / "library"
    for name in ("producer", "consumer"):
        tree = root / "pipelines" / name / "upstream"
        tree.mkdir(parents=True)
        (tree.parent / "skill.md").write_text(f"---\nname: {name}\n---\n")
        (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
            "input": {"type": "string", "format": "directory-path", "exists": True},
            "reference_out": {"type": "string", "enum": ["reference"]},
            "outdir": {"type": "string", "format": "directory-path"}}}))
        (tree / "nextflow.config").write_text(
            "nextflow.enable.dsl=2\nprofiles { standard { process.executor = 'local' } }\n")
    (root / "pipelines/producer/upstream/main.nf").write_text('''process PRODUCE {
 publishDir params.outdir, mode: 'copy'
 input:
 path data, stageAs: 'source_data'
 output:
 path params.reference_out
 script:
 """
 mkdir ${params.reference_out}
 cp -RL ${data}/. ${params.reference_out}/
 """
}
workflow { PRODUCE(file(params.input)) }
''')
    (root / "pipelines/consumer/upstream/main.nf").write_text('''process CONSUME {
 publishDir params.outdir, mode: 'copy'
 input:
 path data
 output:
 path 'namespace.txt'
 script:
 """
 find -L ${data} -mindepth 1 -maxdepth 1 -type d -print | sed 's#^.*/##' | LC_ALL=C sort > namespace.txt
 """
}
workflow { CONSUME(file(params.input)) }
''')
    rule = root / "handoffs/producer/consumer.json"
    rule.parent.mkdir(parents=True)
    rule.write_text(json.dumps({"params": {"input": {"upstream_param":
        {"external": "input", "external_alias": "input", "published": "reference_out", "bundle": "outdir"}[source]}}}))
    reference = tmp_path / "reference"
    if source == "external_alias":
        target = tmp_path / "stored_reference"
        target.mkdir()
        reference.symlink_to("stored_reference", target_is_directory=True)
    (reference / "sample_A").mkdir(parents=True)
    (reference / "index.bin").write_bytes(b"unchanged reference bytes")
    spec = chain.parse_spec({"profile": "standard", "nxf_ver": "25.10.4", "stages": [
        {"pipeline": "producer", "input": str(reference), "params": {"reference_out": "reference"}},
        {"pipeline": "consumer"}]})
    original = chain.orchestration.run_pipeline
    launches = []

    def mutate_after_real_producer(name, **options):
        result = original(name, **options)
        if not options["check_only"]:
            launches.append(name)
            if name == "producer":
                affected = reference if source.startswith("external") else options["outdir"] / "reference"
                (affected / "sample_A").rename(affected / "sample_B")
        return result

    monkeypatch.setattr(chain.orchestration, "run_pipeline", mutate_after_real_producer)
    out = tmp_path / "analysis"
    with pytest.raises(NfclawError) as error:
        chain.run_chain(spec, repo_root=root, outdir=out, timeout_seconds=90)
    assert error.value.code == ErrorCode.HANDOFF_FAILED
    assert "reference" in str(error.value) or "namespace" in str(error.value)
    assert launches == ["producer"]
    assert not (out / "02-consumer/namespace.txt").exists()
    affected = reference if source.startswith("external") else out / "01-producer/reference"
    assert (out / "01-producer/reference" / ("sample_A" if source.startswith("external") else "sample_B")).is_dir()
    assert (out / "01-producer/reference/index.bin").read_bytes() == b"unchanged reference bytes"
    (affected / "sample_B").rename(affected / "sample_A")
    result = chain.run_chain(None, repo_root=root, outdir=out, resume=True, timeout_seconds=90)
    assert result.outcome == "success" and launches == ["producer", "consumer"]
    expected = ".nextflow\nprovenance\nreference\n" if source == "bundle" else "sample_A\n"
    assert (out / "02-consumer/namespace.txt").read_text() == expected
    if source == "external_alias":
        params = json.loads((out / "02-consumer/provenance/params.json").read_text())
        nodes = json.loads((out / "02-consumer/provenance/inputs.inventory.json").read_text())
        assert params["input"] == str(reference)
        assert nodes[str(reference)]["link_target"] == "stored_reference"
    state, problems = chain.status(out)
    assert problems == [] and chain.status_exit_code(state, problems) == 0
    (affected / "sample_A").rename(affected / "sample_C")
    state, problems = chain.status(out)
    assert problems and chain.status_exit_code(state, problems) == 1


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_resume_recomputes_when_a_file_inside_an_input_directory_changes(engine, tmp_path):
    # Nextflow's cache key for a directory input is its path, size and mtime; editing a file in a
    # subdirectory changes none of them, so a plain -resume reuses the task and republishes the
    # result computed from the old bytes (verified: it printed the old content). Same names, same
    # types: only the content differs, so the namespace comparison alone cannot see it.
    root = tmp_path / "library"
    tree = root / "pipelines/fixture/upstream"
    tree.mkdir(parents=True)
    (tree.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path", "exists": True},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    (tree / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    (tree / "main.nf").write_text('''process READ {
 publishDir params.outdir, mode: 'copy', overwrite: true
 input:
 path data
 output:
 path 'value.txt'
 script:
 """
 cat ${data}/nested/value.txt > value.txt
 """
}
workflow { READ(file(params.input)) }
''')
    data = tmp_path / "data"
    (data / "nested").mkdir(parents=True)
    value = data / "nested" / "value.txt"
    value.write_text("AAAA\n")
    out = tmp_path / "analysis"

    def run(resume):
        return orchestration.run_pipeline("fixture", repo_root=root, input_path=data,
            outdir=out, profile="", params_file=None, cli_overrides={}, resume=resume,
            demo=False, check_only=False, write_provenance=True, timeout_seconds=90,
            nxf_ver=engine, limits=resources.parse(1, None, None))

    run(False)
    assert (out / "value.txt").read_text() == "AAAA\n"
    stamp = data.stat(), (data / "nested").stat()
    value.write_text("BBBB\n")                                   # same size, same names
    for path, before in zip((data, data / "nested"), stamp):
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    changed = run(True)
    assert "-resume" not in changed.command
    assert any("all tasks will be recomputed" in warning for warning in changed.warnings)
    assert (out / "value.txt").read_text() == "BBBB\n"
    unchanged = run(True)                                       # nothing changed since: reuse
    assert "-resume" in unchanged.command
    assert (out / "value.txt").read_text() == "BBBB\n"


@pytest.mark.skipif(shutil.which("nextflow") is None, reason="requires a real Nextflow engine")
@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_generated_samplesheet_runs_relocates_and_replays_as_recorded(engine, tmp_path):
    """--input names a directory of FastQ files: the generated sheet drives a real run, its moved
    bundle replays its own copy, files added later are not rescanned, and a changed read file is
    refused. The oracle digests are computed here, independently of the run."""
    import gzip
    root = tmp_path / "library"
    upstream = root / "pipelines/sheetfixture/upstream"
    (upstream / "assets").mkdir(parents=True)
    (upstream.parent / "skill.md").write_text("---\nname: sheetfixture\n---\n")
    (upstream / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "exists": True,
                  "schema": "assets/schema_input.json", "pattern": "^\\S+\\.csv$"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    fastq = "^\\S+\\.f(ast)?q\\.gz$"
    (upstream / "assets/schema_input.json").write_text(json.dumps({"items": {"properties": {
        "sample": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "fastq_1": {"type": "string", "format": "file-path", "pattern": fastq},
        "fastq_2": {"type": "string", "format": "file-path", "pattern": fastq},
        "condition": {"type": "string", "enum": ["treated", "control"]},
    }, "required": ["sample", "fastq_1", "condition"]}}))
    (upstream / "nextflow.config").write_text(
        "nextflow.enable.dsl=2\nprofiles { standard { process.executor = 'local' } }\n")
    (upstream / "main.nf").write_text('''process DIGEST {
    publishDir params.outdir, mode: 'copy'
    input:
    tuple val(sample), val(condition), path(reads)
    output:
    path "${sample}.txt"
    script:
    """
    echo "${condition}" > ${sample}.txt
    shasum -a 256 ${reads} >> ${sample}.txt
    """
}
workflow {
    Channel.fromPath(params.input).splitCsv(header: true)
        .map { row -> tuple(row.sample, row.condition,
                            [row.fastq_1, row.fastq_2].findAll { it }.collect { file(it) }) }
        | DIGEST
}
''')
    data = tmp_path / "reads"
    data.mkdir()

    def write(name: str, read: str) -> bytes:
        payload = gzip.compress(f"@{read}\nACGT\n+\nIIII\n".encode(), mtime=0)
        (data / name).write_bytes(payload)
        return payload

    files = {"A_R1.fastq.gz": write("A_R1.fastq.gz", "r1 1:N:0:1"),
             "A_R2.fastq.gz": write("A_R2.fastq.gz", "r1 2:N:0:1"),
             "B.fastq.gz": write("B.fastq.gz", "b1")}
    (data / "md5sums.txt").write_text("not data\n")
    out = tmp_path / "run" / "results"
    out.parent.mkdir()
    result = orchestration.run_pipeline(
        "sheetfixture", repo_root=root, input_path=str(data), outdir=out, profile="",
        params_file=None, cli_overrides={}, resume=False, demo=False, check_only=False,
        write_provenance=True, timeout_seconds=120, nxf_ver=engine,
        sheet_set={"condition": "treated"})

    def digest(name):
        return f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n"

    assert (out / "A.txt").read_text() == "treated\n" + digest("A_R1.fastq.gz") + digest("A_R2.fastq.gz")
    assert (out / "B.txt").read_text() == "treated\n" + digest("B.fastq.gz")
    assert result.generated_samplesheet == out / "provenance/samplesheet.csv"
    assert sorted(result.outputs_report.files) == ["A.txt", "B.txt"]
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["generated_samplesheet"]["samples"] == 2
    assert manifest["generated_samplesheet"]["ignored"] == ["md5sums.txt"]
    relocated = out.with_name("archive")
    out.rename(relocated)
    write("C.fastq.gz", "c1")                 # a later file: not part of the recorded decision
    replay = subprocess.run(["bash", "archive/provenance/commands.sh", "replay"],
                            cwd=relocated.parent, capture_output=True, text=True, timeout=120)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    comparison = verify.compare(relocated, relocated.parent / "replay")
    assert comparison.byte_identical and sorted(comparison.identical) == ["A.txt", "B.txt"]
    write("B.fastq.gz", "b2")                 # a recorded read file changed: refused
    refused = subprocess.run(["bash", "archive/provenance/commands.sh", "refused"],
                             cwd=relocated.parent, capture_output=True, text=True, timeout=60)
    assert refused.returncode != 0 and "dependency check failed" in refused.stderr
    assert not (relocated.parent / "refused/B.txt").exists()
