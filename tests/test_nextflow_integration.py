"""Real-engine validation using a deterministic, local fixture with an independent oracle.

This exercises nfclaw's execution contract; it makes no claim about biological algorithms.
"""
import hashlib
import json
import shutil
import subprocess

import pytest

from runner import chain, orchestration, resources, runlog, verify


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
    (tmp_path / "main.nf").write_text('''process WIPERTOOLS_REPORTGATHER {
 input:
 val meta
 output:
 path '*.report'
 path 'versions.yml'
 script:
 """
 echo 'Clean reads: 3' > ${meta.id}.report
 echo 'tool: original' > versions.yml
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
    assert all(path.is_symlink() and path.read_text() == "Clean reads: 3\n" for path in published.iterdir())
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
