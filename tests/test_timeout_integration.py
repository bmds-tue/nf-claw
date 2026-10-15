"""Real-engine detached execution, chaining and replay with an independent DNA oracle.

NFCLAW_LONG_TEST_SECONDS extends the task for server soak validation; normal CI uses
two seconds. This checks execution and attribution, not biological algorithm accuracy.
"""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from runner import chain, runlog

pytestmark = pytest.mark.skipif(shutil.which("nextflow") is None,
                                reason="requires a real Nextflow engine")


def _library(root: Path, delay: float):
    sequence = b"ACGTACGA\n"
    source = root / "sequence.txt"
    source.write_bytes(sequence)
    ready, count = root / "ready", root / "executions"
    for name in ("producer", "consumer"):
        tree = root / "pipelines" / name / "upstream"
        tree.mkdir(parents=True)
        (tree.parent / "skill.md").write_text(f"---\nname: {name}\n---\n")
        (tree / "nextflow.config").write_text(
            "nextflow.enable.dsl=2\nprofiles { standard { } }\n")
        (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
            "input": {"type": "string", "format": "file-path", "exists": True},
            "outdir": {"type": "string", "format": "directory-path"}}}))
        operation = (f"touch {ready}\nsleep {delay}\n"
                     "tr 'ACGT' 'TGCA' < ${data} | rev > complement.txt" if name == "producer"
                     else "cat ${data} > final.txt\nsha256sum final.txt | cut -d' ' -f1 > digest.txt")
        output = ("path 'complement.txt'" if name == "producer"
                  else "path 'final.txt'\n path 'digest.txt'")
        (tree / "main.nf").write_text('''process TRANSFORM {
 publishDir params.outdir, mode: 'copy'
 input:
 path data
 output:
 OUTPUT
 script:
 """
 echo NAME >> COUNTER
 OPERATION
 """
}
workflow { TRANSFORM(file(params.input)) }
'''.replace("OUTPUT", output).replace("NAME", name).replace("COUNTER", str(count))
            .replace("OPERATION", operation))
    rules = root / "handoffs/producer"
    rules.mkdir(parents=True)
    (rules / "consumer.json").write_text(json.dumps({"params": {
        "input": {"file": "complement.txt"}}}))
    expected = sequence.strip().translate(bytes.maketrans(b"ACGT", b"TGCA"))[::-1] + b"\n"
    return source, ready, count, expected


@pytest.mark.parametrize("engine", ["25.10.4", "26.04.0"])
def test_unlimited_detached_chain_survives_hangup_and_preserves_scientific_bytes(
        tmp_path, engine):
    delay = float(os.environ.get("NFCLAW_LONG_TEST_SECONDS", "2"))
    assert 0 < delay < 1800
    root = tmp_path / "library"
    root.mkdir()
    source, ready, count, expected = _library(root, delay)
    out = tmp_path / "results"
    spec = tmp_path / "chain.json"
    spec.write_text(json.dumps({"profile": "standard", "nxf_ver": engine,
        "nxf_env": {"NXF_WORK": str(tmp_path / "work")},
        "stages": [{"pipeline": "producer", "input": str(source)},
                   {"pipeline": "consumer"}]}))
    entry = ("import sys; from pathlib import Path; from runner import cli; "
             "cli._repo_root = lambda: Path(sys.argv[2]); "
             "raise SystemExit(cli.main(sys.argv[3:]))")
    with (tmp_path / "controller.log").open("wb") as terminal:
        proc = subprocess.Popen(["nohup", sys.executable, "-c", entry, "nfclaw", str(root),
                                 "chain", "run", str(spec), "--outdir", str(out)],
                                stdout=terminal, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        observation_end = time.monotonic() + 180
        while not ready.exists():
            assert proc.poll() is None, (tmp_path / "controller.log").read_text()
            assert time.monotonic() < observation_end, "native task did not start"
            time.sleep(0.1)
        # A disconnected terminal must not cancel the controller or sever stage ownership.
        proc.send_signal(signal.SIGHUP)
        assert proc.poll() is None
        state, problems = chain.status(out, quick=True)
        assert state["lineage_verification"] == "not_checked" and not problems
        assert chain.status_exit_code(state, problems) == 3
        assert proc.wait(timeout=delay + 240) == 0, (tmp_path / "controller.log").read_text()
    finally:
        if proc.poll() is None:
            proc.terminate()  # Only this test's controller, which owns and cleans its tasks.
            proc.wait(timeout=40)
    state, problems = chain.status(out)
    assert not problems and chain.status_exit_code(state, problems) == 0
    assert (out / "02-consumer/final.txt").read_bytes() == expected
    assert (out / "02-consumer/digest.txt").read_text().strip() == hashlib.sha256(expected).hexdigest()
    assert count.read_text().splitlines() == ["producer", "consumer"]
    assert runlog.read_state(out / "chain/logs/chain.log").state == "success"
    # Frozen stages stay frozen on resume: no hidden recomputation of scientific outputs.
    chain.run_chain(None, repo_root=root, outdir=out, resume=True)
    assert count.read_text().splitlines() == ["producer", "consumer"]
    assert source.read_bytes() == b"ACGTACGA\n"
    # A replay uses the recorded task input and an independent fresh publication directory.
    replay = tmp_path / "producer-replay"
    result = subprocess.run([str(out / "01-producer/provenance/commands.sh"), str(replay)],
                            capture_output=True, text=True, timeout=delay + 180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (replay / "complement.txt").read_bytes() == expected
    assert runlog.read_state(replay / "provenance/logs/run.log").state == "success"
    # Cheap polling must never conceal a failed scientific integrity check in normal status.
    (out / "01-producer/complement.txt").write_bytes(b"CHANGED\n")
    quick, _ = chain.status(out, quick=True)
    assert quick["lineage_verification"] == "not_checked"
    full, issues = chain.status(out)
    assert issues and chain.status_exit_code(full, issues) == 1
