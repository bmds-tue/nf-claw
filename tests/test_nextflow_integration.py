"""Real-engine validation using a deterministic, local fixture with an independent oracle.

This exercises nfclaw's execution contract; it makes no claim about biological algorithms.
"""
import base64
import csv
import ctypes
import gzip
import hashlib
import http.server
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from runner import (chain, fastqrepair_compat, orchestration, replay_guard, resources,
                    resume_safety, runlog, verify)
from runner.errors import ErrorCode, NfclawError
from runner.inputs import local_name_issues
from test_input_output_separation import run, tree

# How long a real Nextflow run, replay or config resolution may take before the test calls it
# hung. It bounds a hang, not speed: under a loaded host and parallel test workers, one launch
# of a 25.10 engine took over 90 seconds.
NEXTFLOW_TIMEOUT = 300

pytestmark = pytest.mark.skipif(shutil.which("nextflow") is None,
                                reason="requires a real Nextflow engine")


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
@pytest.mark.parametrize("kind,provenance", [("data", True), ("data", False), ("config", True),
                                           ("source", True), ("unchanged", True)])
def test_dependencies_changing_during_native_execution_cannot_claim_success(tmp_path, engine,
                                                                            kind, provenance):
    root = tmp_path / "library"
    tree = root / "pipelines/fixture/upstream"
    tree.mkdir(parents=True)
    (tree.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (tree / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "exists": True},
        "ready": {"type": "string"}, "release": {"type": "string"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    script = tree / "main.nf"
    script.write_text(r'''process OBSERVE {
 publishDir params.outdir, mode: 'copy'
 input:
 path data
 output:
 path 'digest.txt'
 script:
 """
 touch ${params.ready}
 for attempt in \$(seq 1 1200); do
   [ -f ${params.release} ] && break
   sleep 0.05
 done
 test -f ${params.release}
 echo executed >> COUNTER
 shasum -a 256 ${data} > digest.txt
 """
}
workflow { OBSERVE(file(params.input)) }
'''.replace("COUNTER", shlex.quote(str(tmp_path / "counter"))))
    original = b"@S\nACGT\n+\nIIII\n"
    changed = b"@S\nACGA\n+\nIIII\n"
    source = tmp_path / "reads.fastq"
    source.write_bytes(original)
    config = tmp_path / "extra.config"
    config.write_text("params.receipt_note = 'before'\n")
    ready, release = tmp_path / "ready", tmp_path / "release"
    counter = tmp_path / "counter"
    out = tmp_path / "result"
    def launch(resume=False):
        return orchestration.run_pipeline("fixture", repo_root=root, input_path=source, outdir=out,
            profile="", params_file=None,
            cli_overrides={"ready": str(ready), "release": str(release)},
            resume=resume, demo=False, check_only=False, write_provenance=provenance,
            timeout_seconds=90, nxf_ver=engine, configs=[str(config)])
    restore = None
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(launch)
        deadline = time.monotonic() + 70
        try:
            while not ready.exists():
                if future.done():
                    future.result()
                    pytest.fail("run finished without opening the task gate")
                assert time.monotonic() < deadline, "native task gate timed out"
                time.sleep(0.05)
            if kind == "data":
                stat = source.stat()
                source.write_bytes(changed)
                os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                def restore():
                    source.write_bytes(original)
                    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            elif kind == "config":
                config.write_text("params.receipt_note = 'after'\n")
                def restore():
                    config.write_text("params.receipt_note = 'before'\n")
            elif kind == "source":
                before = script.read_bytes()
                script.write_bytes(before + b"\n// changed after compilation\n")
                def restore():
                    script.write_bytes(before)
        finally:
            release.touch()
        if kind == "unchanged":
            future.result(timeout=30)
        else:
            with pytest.raises(NfclawError, match="during execution") as error:
                future.result(timeout=30)
            assert error.value.code == ErrorCode.ENVIRONMENT
    expected = hashlib.sha256(changed if kind == "data" else original).hexdigest()
    assert (out / "digest.txt").read_text().split()[0] == expected
    state = runlog.read_state(out / "provenance/logs/run.log")
    assert state.state == ("success" if kind == "unchanged" else "ended")
    if kind != "unchanged":
        assert state.outcome.startswith("failed after Nextflow succeeded")
    if provenance:
        bundle = out / "provenance"
        manifest = json.loads((bundle / "run_manifest.json").read_text())
        assert manifest["outcome"] == ("success" if kind == "unchanged" else "failed")
        stability = manifest["dependency_stability"]
        assert stability["status"] == ("unchanged" if kind == "unchanged" else "changed")
        recorded = replay_guard.read_checksums(bundle / "inputs.sha256", relative=False)
        assert recorded[str(source)] == hashlib.sha256(original).hexdigest()
        if kind == "unchanged":
            ready.unlink()
            release.unlink()
            target = tmp_path / "tainted_replay"
            process = subprocess.Popen(["bash", str(bundle / "commands.sh"), str(target)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            deadline = time.monotonic() + 70
            try:
                while not ready.exists():
                    if process.poll() is not None:
                        stdout, stderr = process.communicate(timeout=10)
                        pytest.fail(stdout + stderr)
                    assert time.monotonic() < deadline, "replay task gate timed out"
                    time.sleep(0.05)
                source.write_bytes(changed)
            finally:
                release.touch()
            stdout, stderr = process.communicate(timeout=30)
            assert process.returncode != 0, stdout + stderr
            assert "local dependencies changed" in stderr
            assert ((target / "digest.txt").read_text().split()[0]
                    == hashlib.sha256(changed).hexdigest())
            replay_state = runlog.read_state(target / "provenance/logs/run.log")
            assert replay_state.state == "ended"
            assert replay_state.outcome == ("failed after Nextflow succeeded "
                                            "(local dependencies changed)")
        if restore:
            restore()
            replay = subprocess.run(
                ["bash", str(bundle / "commands.sh"), str(tmp_path / "refused")],
                capture_output=True, text=True, timeout=15)
            assert replay.returncode != 0 and "original run" in replay.stderr
            assert not (tmp_path / "refused/.nextflow").exists()
            if kind == "data":
                result = launch(resume=True)
                assert any("previous execution" in warning for warning in result.warnings)
                assert ((out / "digest.txt").read_text().split()[0]
                        == hashlib.sha256(original).hexdigest())
                assert counter.read_text().splitlines() == ["executed", "executed"]
                archives = list(tmp_path.glob("result.previous-*"))
                assert len(archives) == 1
                assert ((archives[0] / "digest.txt").read_text().split()[0]
                        == hashlib.sha256(changed).hexdigest())
    else:
        assert not (out / "provenance/run_manifest.json").exists()


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
@pytest.mark.parametrize("source_kind", ["cli", "json", "yaml"])
def test_exact_numeric_parameters_reach_native_tasks_and_standalone_replay(tmp_path,
                                                                           engine, source_kind):
    if source_kind == "yaml":
        pytest.importorskip("yaml")
    root = tmp_path / "library"
    tree = root / "pipelines/fixture/upstream"
    tree.mkdir(parents=True)
    (tree.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (tree / "nextflow_schema.json").write_text('''{"properties": {
      "choice": {"type":"integer", "enum":[9007199254740993]},
      "count": {"type":"integer", "enum":[1e23]},
      "values": {"type":"object"},
      "outdir": {"type":"string", "format":"directory-path"}}}''')
    (tree / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    (tree / "main.nf").write_text('''process OBSERVE {
 publishDir params.outdir, mode: 'copy'
 input:
 val values
 output:
 path 'observed.json'
 script:
 def text = groovy.json.JsonOutput.toJson(values.collectEntries { key, value -> [key, value.toString()] })
 """
 cat > observed.json <<'NFCLAW_VALUES'
 ${text}
 NFCLAW_VALUES
 """
}
workflow { OBSERVE(params.values + [choice: params.choice, count: params.count]) }
''')  # noqa: E501
    tokens = {"tiny": "1e-9999", "large": "1e9999", "precise": "0.1000000000000000000001",
              "whole_decimal": "100000000000000000000001e0"}
    choice = "9007199254740993e0"
    raw_values = ",".join(json.dumps(key) + ":" + value for key, value in tokens.items())
    params_path = tmp_path / "params.json"
    params_path.write_text('{"choice":' + choice + ',"count":1e23,"values":{' + raw_values + '}}')
    expected = {**tokens, "choice": choice, "count": "1e23"}

    def observe(outdir):
        observed = json.loads((outdir / "observed.json").read_text())
        assert observed.keys() == expected.keys()
        assert {key: Decimal(value) for key, value in observed.items()} == {
            key: Decimal(value) for key, value in expected.items()}

    # Independent direct-Nextflow control: these decimal values are supported by the engine.
    if source_kind == "cli":
        raw = tmp_path / "raw"
        raw.mkdir()
        result = subprocess.run(["nextflow", "run", str(tree), "-params-file", str(params_path),
            "--outdir", str(raw), "-ansi-log", "false"], cwd=raw,
            env={**os.environ, "NXF_VER": engine}, capture_output=True, text=True,
            timeout=NEXTFLOW_TIMEOUT)
        assert result.returncode == 0, result.stdout + result.stderr
        observe(raw)
        # Plain integer literals beyond signed-long range wrap in these engines. The decimal
        # notation above is a separate direct control; the wrapper must avoid this corruption.
        overflowing = tmp_path / "overflowing.json"
        overflowing.write_text(params_path.read_text().replace('"count":1e23',
                                                               '"count":100000000000000000000000'))
        raw_wrapped = tmp_path / "raw_wrapped"
        raw_wrapped.mkdir()
        result = subprocess.run(["nextflow", "run", str(tree), "-params-file", str(overflowing),
            "--outdir", str(raw_wrapped), "-ansi-log", "false"], cwd=raw_wrapped,
            env={**os.environ, "NXF_VER": engine}, capture_output=True, text=True,
            timeout=NEXTFLOW_TIMEOUT)
        assert result.returncode == 0, result.stdout + result.stderr
        wrapped = json.loads((raw_wrapped / "observed.json").read_text())["count"]
        assert Decimal(wrapped) == ctypes.c_longlong(10 ** 23).value
        assert Decimal(wrapped) != Decimal("1e23")

    overrides = {}
    if source_kind == "cli":
        overrides["choice"] = choice
        overrides["count"] = "100000000000000000000000"
        # An object comes from the JSON params file; its nested numbers also need preservation.
    elif source_kind == "yaml":
        params_path = tmp_path / "params.yaml"
        params_path.write_text("choice: 9007199254740993.0\ncount: 1.0e+23\nvalues:\n"
                               "  tiny: 1.0e-9999\n"
                               "  large: 1.0e+9999\n  precise: 0.1000000000000000000001\n"
                               "  whole_decimal: 100000000000000000000001.0\n")
    out = tmp_path / "original"
    orchestration.run_pipeline("fixture", repo_root=root, input_path=None, outdir=out, profile="",
        params_file=params_path, cli_overrides=overrides, resume=False, demo=False,
        check_only=False, write_provenance=True, timeout_seconds=90, nxf_ver=engine)
    observe(out)
    recorded = json.loads((out / "provenance/params.json").read_text(), parse_float=Decimal)
    assert recorded["choice"] == Decimal(choice)
    assert recorded["count"] == Decimal("1e23")
    assert recorded["values"] == {key: Decimal(value) for key, value in tokens.items()}
    replay = tmp_path / "replay"
    result = subprocess.run(["bash", str(out / "provenance/commands.sh"), str(replay)],
                            capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert result.returncode == 0, result.stdout + result.stderr
    observe(replay)
    assert verify.compare(out, replay).byte_identical


def _path_route_fixture(tmp_path):
    root = tmp_path / "library"
    upstream = root / "pipelines/fixture/upstream"
    upstream.mkdir(parents=True)
    (upstream.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (upstream / "assets").mkdir()
    (upstream / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "exists": True,
                  "schema": "assets/schema_input.json"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    (upstream / "assets/schema_input.json").write_text(json.dumps({"items": {
        "properties": {"sample": {"type": "string"},
                       "reads": {"type": "string", "format": "file-path"}},
        "required": ["sample", "reads"]}}))
    (upstream / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    (upstream / "main.nf").write_text('''process DIGEST {
 publishDir params.outdir, mode: 'copy'
 input:
 path data
 output:
 path 'digest.txt'
 script:
 """
 shasum -a 256 ${data} > digest.txt
 """
}
workflow {
 def rows = new groovy.json.JsonSlurper().parseText(file(params.input).text)
 DIGEST(Channel.fromPath(rows[0].reads))
}
''')
    return root


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
@pytest.mark.parametrize("mode", ["line_break", "symlink_traversal"])
def test_native_staging_hazards_are_refused_before_wrapper_launch(tmp_path, engine, mode):
    root = _path_route_fixture(tmp_path)
    payload = b"@R1\nACGT\n+\nIIII\n"
    if mode == "line_break":
        parent = tmp_path / "parent\npwd\nrest"
        parent.mkdir()
        source = parent / "reads.fastq"
        source.write_bytes(payload)
    else:
        (tmp_path / "real/nested").mkdir(parents=True)
        (tmp_path / "route").symlink_to("real/nested", target_is_directory=True)
        (tmp_path / "real/reads.fastq").write_bytes(payload)
        (tmp_path / "reads.fastq").write_bytes(b"wrong decoy")
        source = tmp_path / "route/../reads.fastq"
    sheet = tmp_path / "samples.json"
    sheet.write_text(json.dumps([{"sample": "S", "reads": str(source)}]))
    params = tmp_path / "raw_params.json"
    params.write_text(json.dumps({"input": str(sheet), "outdir": str(tmp_path / "raw_outputs")}))
    launch = tmp_path / "raw_launch"
    launch.mkdir()
    raw_work = tmp_path / "raw_work"
    raw = subprocess.run(["nextflow", "run", str(root / "pipelines/fixture/upstream"),
                          "-params-file", str(params), "-work-dir", str(raw_work),
                          "-ansi-log", "false"],
                         cwd=launch, env={**os.environ, "NXF_VER": engine},
                         capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    if mode == "line_break":
        assert raw.returncode != 0
        task = next(raw_work.glob("*/*/.command.run"))
        # The source's newline became a real shell command, not just a display artifact.
        assert b"\n    pwd\n" in task.read_bytes()
        assert str(task.parent) in (task.parent / ".command.log").read_text()
    else:
        assert raw.returncode == 0, raw.stdout + raw.stderr
        actual = (tmp_path / "raw_outputs/digest.txt").read_text()
        assert actual == hashlib.sha256(b"wrong decoy").hexdigest() + "  reads.fastq\n"
        assert source.read_bytes() == payload  # the checksum preflight would read different bytes
    out = tmp_path / "refused"
    with pytest.raises(NfclawError) as error:
        orchestration.run_pipeline("fixture", repo_root=root, input_path=sheet, outdir=out,
            profile="", params_file=None, cli_overrides={}, resume=False, demo=False,
            check_only=False, write_provenance=True, timeout_seconds=90, nxf_ver=engine)
    assert error.value.code == ErrorCode.SAMPLESHEET_INVALID
    assert ("line break" if mode == "line_break" else "different data") in str(error.value)
    assert not out.exists() and not (tmp_path / ".refused.nfclaw.lock").exists()
    assert source.read_bytes() == payload


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
@pytest.mark.parametrize("parent_kind", ["escaped", "colon_separator"])
def test_samplesheet_path_routes_and_escaped_parent_names_replay_without_renaming(
        tmp_path, engine, parent_kind):
    root = _path_route_fixture(tmp_path)
    parent = tmp_path / ("parentwith\\slash\u2028separator" if parent_kind == "escaped"
                         else "parent:")
    (parent / "real/nested").mkdir(parents=True)
    (parent / "route").symlink_to("real/nested", target_is_directory=True)
    target = parent / "real/stored.data"
    payload = b"@R1\nACGT\n+\nIIII\n"
    target.write_bytes(payload)
    (parent / "real/reads.fastq").symlink_to("stored.data")
    (parent / "reads.fastq").write_bytes(b"wrong decoy")
    source = parent / "real/nested/../reads.fastq"
    sheet = tmp_path / "samples.json"
    value = (str(source) if parent_kind == "escaped"
             else str(source).replace("parent:/", "parent://", 1))
    sheet.write_text(json.dumps([{"sample": "S", "reads": value}]))
    out = tmp_path / "original"
    orchestration.run_pipeline("fixture", repo_root=root, input_path=sheet, outdir=out, profile="",
        params_file=None, cli_overrides={}, resume=False, demo=False, check_only=False,
        write_provenance=True, timeout_seconds=90, nxf_ver=engine)
    expected = hashlib.sha256(payload).hexdigest() + "  reads.fastq\n"
    assert (out / "digest.txt").read_text() == expected
    moved = tmp_path / "moved"
    out.rename(moved)
    replay = subprocess.run(
        ["bash", str(moved / "provenance/commands.sh"), str(tmp_path / "replay")],
        capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert (tmp_path / "replay/digest.txt").read_text() == expected
    assert verify.compare(moved, tmp_path / "replay").byte_identical
    target.write_bytes(b"changed scientific input")
    refused = subprocess.run(
        ["bash", str(moved / "provenance/commands.sh"), str(tmp_path / "refused")],
        capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and "content changed" in refused.stderr
    assert not (tmp_path / "refused/.nextflow").exists()


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_execution_writes_are_separated_from_directory_inputs(tmp_path, engine):
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
    replay = subprocess.run(
        ["bash", str(safe / "provenance/commands.sh"), str(tmp_path / "replay")],
        capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert verify.compare(safe, tmp_path / "replay").byte_identical
    assert (data / "index.bin").read_bytes() == b"fixed scientific input"
    assert sorted(p.name for p in data.iterdir()) == ["index.bin", "sample_A"]
    assert data.stat().st_mtime_ns == before


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_staged_file_alias_names_survive_run_replay_and_reference_handoff(tmp_path, engine):
    root = tmp_path / "library"
    upstream = root / "pipelines/fixture/upstream"
    upstream.mkdir(parents=True)
    (upstream.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (upstream / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "exists": True, "pattern": r"\.csv$"},
        "reference": {"type": "string", "format": "file-path", "exists": True,
                      "pattern": r"\.csv$"},
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
                            capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert verify.compare(out, tmp_path / "replay").byte_identical
    spec = chain.parse_spec({"profile": "standard", "nxf_ver": engine, "stages": [
        {"pipeline": "fixture", "input": str(primary), "params": {"reference": str(reference)}},
        {"pipeline": "fixture", "id": "consumer", "handoff": {"params": {
            "input": {"upstream_param": "reference"}}}}]})
    chained = tmp_path / "chain"
    result = chain.run_chain(spec, repo_root=root, outdir=chained, timeout_seconds=120)
    assert result.outcome == "success"
    assert ((chained / "02-consumer/observed.txt").read_text()
            == f"reference.csv\n{digest}  reference.csv\n")
    state, problems = chain.status(chained)
    assert problems == [] and chain.status_exit_code(state, problems) == 0
    # Identical data cannot hide a retargeted alias from the stored dependency identity.
    second = tmp_path / "second.data"
    second.write_bytes(target.read_bytes())
    reference.unlink()
    reference.symlink_to("second.data")
    refused = subprocess.run(
        ["bash", str(out / "provenance/commands.sh"), str(tmp_path / "refused")],
        capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and "dependency check failed" in refused.stderr
    assert not (tmp_path / "refused/observed.txt").exists()
    assert not (tmp_path / "refused/.nextflow").exists()
    assert list((tmp_path / "refused").iterdir()) == []
    state, problems = chain.status(chained)
    assert problems and chain.status_exit_code(state, problems) == 1


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
                            capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
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


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_recorded_repair_publishers_preserve_mates_and_honor_runtime_mode(tmp_path, engine):
    # 26.04 made the strict config parser the default; the recorded corrections run under the
    # legacy parser nfclaw selects for them (fastqrepair_compat.nextflow_env).
    fastqrepair_compat.write_config(tmp_path / "compat.config")
    (tmp_path / "nextflow.config").write_text("params.publish_dir_mode = 'copy'\n"
                                              "params.outdir = 'wrong'\n")
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
    result = subprocess.run(
        ["nextflow", "run", "main.nf", "-c", "compat.config", "-ansi-log", "false",
         "--outdir", "results", "--publish_dir_mode", "symlink"],
        cwd=tmp_path, env={**os.environ, "NXF_VER": engine, **fastqrepair_compat.nextflow_env({})},
        capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert result.returncode == 0, result.stdout + result.stderr
    published = tmp_path / "results/repaired/reports/paired_probe"
    assert sorted(path.name for path in published.iterdir()) == ["left.report", "right.report"]
    assert all(path.is_symlink() and path.read_text() == report for path in published.iterdir())
    assert not (tmp_path / "wrong").exists()


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_remote_staging_names_match_preflight_without_decoding(engine, tmp_path):
    """A local HTTP oracle checks actual staged bytes/names, with no unsafe interpolation."""
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
                                capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    finally:
        server.shutdown()
        server.server_close()
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


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_directory_children_become_individual_staged_inputs(engine, tmp_path):
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
                            capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = list((tmp_path / "work").rglob("observed.tsv"))
    assert sorted(path.read_text().strip() for path in outputs) == sorted(names)
    for path in outputs:
        assert (path.parent / path.read_text().strip()).read_bytes() == b"known directory data\n"
    assert local_name_issues(str(source), "directory-path")
    (source / names[0]).unlink()
    assert local_name_issues(str(source), "directory-path") == []


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_empty_directory_namespace_is_guarded_and_resume_is_current(engine, tmp_path):
    root = tmp_path / "library"
    tree = root / "pipelines/fixture/upstream"
    tree.mkdir(parents=True)
    (tree.parent / "skill.md").write_text("---\nname: fixture\n---\n")
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path", "exists": True},
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
 echo executed >> COUNTER
 find -L ${data} -mindepth 1 -maxdepth 1 -type d -print | sed 's#^.*/##' | LC_ALL=C sort > result/namespace.txt
 for sample in ${data}/*; do basename "\\$sample" > "result/\\$(basename "\\$sample").txt"; done
 """
}
workflow { NAMESPACE(file(params.input)) }
'''.replace("COUNTER", shlex.quote(str(tmp_path / "executions.txt"))))  # noqa: E501
    data = tmp_path / "data"
    data.mkdir()
    first = data / "sample_A"
    first.mkdir()
    stamp = data.stat()
    out = tmp_path / "analysis"
    counter = tmp_path / "executions.txt"

    def run(resume):
        return orchestration.run_pipeline("fixture", repo_root=root, input_path=data,
            outdir=out, profile="", params_file=None, cli_overrides={}, resume=resume,
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
                            capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
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


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_archiving_respects_the_real_engines_active_session_lock(engine, tmp_path):
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


@pytest.mark.parametrize("source", ["external", "external_alias", "published", "bundle"])
def test_real_chain_refuses_changed_reference_namespace_and_resumes_after_restoration(
        tmp_path, monkeypatch, source):
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
''')  # noqa: E501
    rule = root / "handoffs/producer/consumer.json"
    rule.parent.mkdir(parents=True)
    upstream_param = {"external": "input", "external_alias": "input", "published": "reference_out",
                      "bundle": "outdir"}[source]
    rule.write_text(json.dumps({"params": {"input": {"upstream_param": upstream_param}}}))
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
                affected = (reference if source.startswith("external")
                            else options["outdir"] / "reference")
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
    kept = "sample_A" if source.startswith("external") else "sample_B"
    assert (out / "01-producer/reference" / kept).is_dir()
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
    for path, before in zip((data, data / "nested"), stamp, strict=True):
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    changed = run(True)
    assert "-resume" not in changed.command
    assert any("all tasks will be recomputed" in warning for warning in changed.warnings)
    assert (out / "value.txt").read_text() == "BBBB\n"
    unchanged = run(True)                                       # nothing changed since: reuse
    assert "-resume" in unchanged.command
    assert (out / "value.txt").read_text() == "BBBB\n"


@pytest.mark.parametrize('engine', ['25.10.4', '26.04.0'])
@pytest.mark.parametrize('write_provenance', [True, False])
def test_resume_recomputes_same_metadata_file_bytes_and_reuses_unchanged_inputs(
        tmp_path, engine, write_provenance):
    root = _path_route_fixture(tmp_path)
    counter = tmp_path / 'executions.txt'
    script = root / 'pipelines/fixture/upstream/main.nf'
    script.write_text(script.read_text().replace('shasum -a 256 ${data} > digest.txt',
        f'echo executed >> {shlex.quote(str(counter))}\n shasum -a 256 ${{data}} > digest.txt'))
    source = tmp_path / 'reads.fastq'
    original = b'@R1\nACGT\n+\nIIII\n'
    modified = b'@R1\nTGCA\n+\nIIII\n'
    source.write_bytes(original)
    sheet = tmp_path / 'samples.json'
    sheet.write_text(json.dumps([{'sample': 'S1', 'reads': str(source)}]))
    outdir = tmp_path / 'results'

    def run(resume):
        return orchestration.run_pipeline('fixture', repo_root=root, input_path=sheet,
            outdir=outdir, profile='standard', params_file=None, cli_overrides={},
            resume=resume, demo=False, check_only=False, write_provenance=write_provenance,
            timeout_seconds=90, nxf_ver=engine)

    run(False)
    assert (outdir / 'digest.txt').read_text().split()[0] == hashlib.sha256(original).hexdigest()
    assert len(counter.read_text().splitlines()) == 1
    stamp = source.stat()
    source.write_bytes(modified)
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert source.stat().st_size == stamp.st_size
    assert source.stat().st_mtime_ns == stamp.st_mtime_ns
    changed = run(True)
    assert '-resume' not in changed.command
    reason = 'local input file changed' if write_provenance else 'inventory is unavailable'
    assert any(reason in warning for warning in changed.warnings)
    assert (outdir / 'digest.txt').read_text().split()[0] == hashlib.sha256(modified).hexdigest()
    assert len(counter.read_text().splitlines()) == 2
    unchanged = run(True)
    assert ('-resume' in unchanged.command) is write_provenance
    assert len(counter.read_text().splitlines()) == (2 if write_provenance else 3)
    assert (outdir / 'digest.txt').read_text().split()[0] == hashlib.sha256(modified).hexdigest()


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_generated_samplesheet_runs_relocates_and_replays_as_recorded(engine, tmp_path):
    """--input names a directory of FastQ files: the generated sheet drives a real run, its moved
    bundle replays its own copy, files added later are not rescanned, and a changed read file is
    refused. The oracle digests are computed here, independently of the run."""
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

    assert (out / "A.txt").read_text() == ("treated\n" + digest("A_R1.fastq.gz")
                                           + digest("A_R2.fastq.gz"))
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
                            cwd=relocated.parent, capture_output=True, text=True,
                            timeout=NEXTFLOW_TIMEOUT)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    comparison = verify.compare(relocated, relocated.parent / "replay")
    assert comparison.byte_identical and sorted(comparison.identical) == ["A.txt", "B.txt"]
    write("B.fastq.gz", "b2")                 # a recorded read file changed: refused
    refused = subprocess.run(["bash", "archive/provenance/commands.sh", "refused"],
                             cwd=relocated.parent, capture_output=True, text=True, timeout=60)
    assert refused.returncode != 0 and "dependency check failed" in refused.stderr
    assert not (relocated.parent / "refused/B.txt").exists()


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_chain_refuses_success_when_a_real_consumer_hashes_different_producer_data(
        tmp_path, monkeypatch, engine):
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
workflow { DIGEST(Channel.fromPath(params.input)) }
''')
    initial = tmp_path / "data.txt"
    initial.write_bytes(b"original scientific data\n")
    out = tmp_path / "chain"
    spec = chain.parse_spec({"profile": "standard", "nxf_ver": engine, "stages": [
        {"id": "producer", "pipeline": "fixture", "input": str(initial)},
        {"id": "consumer", "pipeline": "fixture", "handoff": {
            "params": {"input": {"file": "result/digest.txt"}}}}]})
    real_run = orchestration.run_pipeline
    altered = b"different data actually consumed\n"

    def mutate_after_handoff(name, **options):
        if options["check_only"] or options["outdir"] != out / "02-consumer":
            return real_run(name, **options)
        produced = out / "01-producer/result/digest.txt"
        original = produced.read_bytes()
        produced.write_bytes(altered)
        try:
            return real_run(name, **options)
        finally:
            produced.write_bytes(original)

    monkeypatch.setattr(orchestration, "run_pipeline", mutate_after_handoff)
    with pytest.raises(NfclawError, match="lineage"):
        chain.run_chain(spec, repo_root=root, outdir=out, timeout_seconds=180)
    assert ((out / "02-consumer/result/digest.txt").read_text().split()[0]
            == hashlib.sha256(altered).hexdigest())
    state, problems = chain.status(out)
    assert state["outcome"] != "success" and problems
    assert chain.status_exit_code(state, problems) == 1


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_fastqrepair_large_cohort_role_config_compiles_without_jvm_string_overflow(
        tmp_path, engine):
    sheet = tmp_path / "cohort.csv"
    sheet.write_text("sample,fastq_1,fastq_2\n" + "".join(
        f"S{index},/data/left.fastq,/data/right.fastq\n" for index in range(10000)))
    config = fastqrepair_compat.write_config(tmp_path / "recorded.config", input_path=sheet)
    compat_env = fastqrepair_compat.nextflow_env({})
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    (pipeline / "nextflow.config").write_text("nextflow.enable.dsl=2\n")
    # Nextflow stringifies meta-dependent closures; embedding even fragmented
    # cohort data inside such a closure overflows one JVM string constant.
    result = subprocess.run(["nextflow", "-c", str(config), "config", str(pipeline), "-flat"],
                            cwd=tmp_path, env={**os.environ, "NXF_VER": engine, **compat_env},
                            capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert result.returncode == 0, result.stdout + result.stderr

    # Exercise first/last keys through real task closures, using an argument
    # recorder in place of BBMap. This validates transport and command order;
    # the separate native scientific controls execute the real repair tools.
    left, right = (tmp_path / f"{role}_gather__nfclaw_0123456789abcdef.fastq.gz"
                   for role in ("left", "right"))
    left.write_bytes(b"")
    right.write_bytes(b"")
    (pipeline / "nextflow.config").write_text(
        "nextflow.enable.dsl=2\nparams.publish_dir_mode='copy'\n")
    (pipeline / "main.nf").write_text(r'''process BBMAP_REPAIR {
    input:
    tuple val(meta), path(left), path(right)
    output:
    path '*.repair.sh.log'
    script:
    """
    repair.sh() { printf '%s\\n' "\$@"; }
    repair.sh \\
        threads=1
        qin=33 \\
        in=${right} in2=${left} \\
        out=${task.ext.prefix}_1_repaired.fastq.gz \\
        &> ${task.ext.prefix}.repair.sh.log
    """
}
workflow {
    Channel.of(tuple([id:'S0', single_end:false], file(params.left), file(params.right)),
               tuple([id:'S9999', single_end:false], file(params.left), file(params.right)))
        | BBMAP_REPAIR
}
''')
    out, work = tmp_path / "results", tmp_path / "work"
    executed = subprocess.run(["nextflow", "run", str(pipeline), "-c", str(config),
                               "--left", str(left), "--right", str(right),
                               "--outdir", str(out), "-work-dir", str(work)],
                              cwd=tmp_path, env={**os.environ, "NXF_VER": engine, **compat_env},
                              capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    selections = []
    for wrapper in work.rglob(".command.run"):
        payloads = re.findall(r"--mate-orders ([A-Za-z0-9+/=]+)", wrapper.read_text())
        assert len(payloads) == 1
        selections.append(json.loads(base64.b64decode(payloads[0])))
    assert sorted(selections, key=lambda item: next(iter(item))) == [
        {"S0": ["left", "right"]}, {"S9999": ["left", "right"]}]
    for sample in ("S0", "S9999"):
        arguments = (out / "repaired" / f"{sample}.repair.sh.log").read_text().splitlines()
        assert arguments[:2] == ["threads=1", "qin=33"]
        assert arguments[2:4] == [f"in={left.name}", f"in2={right.name}"]
