"""Replay dependency guards and failure-safe provenance publication."""
import hashlib
import json
import subprocess

import pytest

from runner import provenance
from runner.schema import Column, InputSchema
from runner.submodule import SubmoduleStatus


def _write(outdir, *, command_str="echo REPLAY_RAN", submodule=None, **kwargs):
    return provenance.write(
        outdir=outdir, pipeline="mini", command_str=command_str,
        submodule=submodule or SubmoduleStatus("mini", outdir.parent / "up", True, True,
                                               "1.0.0", "deadbeef", ()), **kwargs)


@pytest.fixture(autouse=True)
def _no_engine_probe(monkeypatch):
    # No engine is launched in these dependency/bundle tests.
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "test engine")


@pytest.mark.parametrize("prior_bundle", [False, True])
def test_checksum_failure_cannot_leave_a_success_manifest(tmp_path, monkeypatch, prior_bundle):
    out = tmp_path / "out"
    if prior_bundle:
        _write(out, input_paths=[])

    out.mkdir(exist_ok=True)
    result_file = out / "counts.tsv"
    result_file.write_text("scientific counts\n")
    original = provenance._sha256

    def fail(path):
        if path == result_file:
            raise PermissionError("unreadable result")
        return original(path)

    monkeypatch.setattr(provenance, "_sha256", fail)
    with pytest.raises(PermissionError):
        _write(out, input_paths=[])
    manifest = out / "provenance" / "run_manifest.json"
    assert not manifest.exists() or json.loads(manifest.read_text())["outcome"] != "success"
    if prior_bundle:
        result = subprocess.run([str(out / "provenance" / "commands.sh"), str(tmp_path / "fresh")],
                                capture_output=True, text=True)
        assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout


def test_replay_refuses_changed_external_config_before_launch(tmp_path):
    config = tmp_path / "analysis.config"
    config.write_text("params.threshold = 0.01\n")
    prov = _write(tmp_path / "out", input_paths=[], config_paths=(config,))
    config.write_text("params.threshold = 0.99\n")
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "REPLAY_RAN" not in result.stdout
    assert "analysis.config" in result.stderr


def test_prelaunch_input_hash_is_preserved_if_input_changes_during_run(tmp_path):
    reads = tmp_path / "reads.fastq"
    original = b"@r\nACGT\n+\nIIII\n"
    reads.write_bytes(original)
    snapshot = {str(reads): hashlib.sha256(original).hexdigest()}
    reads.write_bytes(b"@r\nTTTT\n+\nIIII\n")
    prov = _write(tmp_path / "out", input_paths=[reads], input_checksums=snapshot)
    assert (prov / "inputs.sha256").read_text() == (
        "386b5921e18396f227d1c7cca34b80fa323518ef1b9d29db0bb1d27dc42f3535" + f"  {reads}\n")
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout


def test_directory_input_new_files_invalidate_replay(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "sample.dat").write_text("original")
    prov = _write(tmp_path / "out", input_paths=[data])
    (data / "new-sample.dat").write_text("extra data")
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "new-sample.dat" in result.stderr


def test_directory_and_glob_inputs_have_content_checksums(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.txt").write_bytes(b"a")
    (data / "nested").mkdir()
    (data / "nested" / "b.txt").write_bytes(b"b")
    snapshot = provenance.hash_inputs([data, data / "*.txt"])
    assert snapshot == {
        str(data / "a.txt"): "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        str(data / "nested" / "b.txt"): "3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d",
    }


@pytest.mark.parametrize("pattern", ["sample_{1,2}.txt", "**.txt"])
def test_nextflow_glob_variants_preserve_their_input_files(tmp_path, pattern):
    data = tmp_path / "data"
    data.mkdir()
    first = data / "sample_1.txt"
    first.write_bytes(b"a")
    second = data / "sample_2.txt"
    second.write_bytes(b"b")
    if pattern == "**.txt":
        (data / "nested").mkdir()
        second.rename(data / "nested" / second.name)
        second = data / "nested" / second.name
    assert provenance.hash_inputs([data / pattern]) == {
        str(first): "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        str(second): "3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d",
    }


def test_samplesheet_data_paths_are_part_of_input_identity(tmp_path):
    sheet = tmp_path / "samples.csv"
    reads = tmp_path / "reads.fastq"
    reads.write_bytes(b"reads")
    sheet.write_text(f"sample,fastq,remote\nA,{reads},s3://bucket/remote.fastq\n")
    schema = InputSchema(columns=(
        Column("sample", "string", True, None),
        Column("fastq", "string", True, None, fmt="file-path"),
        Column("remote", "string", False, None, fmt="file-path"),
    ))
    assert provenance.samplesheet_input_paths(sheet, schema) == [reads]


@pytest.mark.parametrize("suffix", [".csv", ".json"])
def test_samplesheet_data_outside_path_fields_is_part_of_input_identity(tmp_path, suffix):
    # hic types fastq_1 by its pattern alone; hgtseq's parser reads input1, which its schema omits.
    reads = tmp_path / "A_1.fastq.gz"
    parsed = tmp_path / "A_input1.fastq.gz"
    declared = tmp_path / "declared.fastq.gz"
    for path in (reads, parsed, declared):
        path.write_bytes(path.name.encode())
    index = tmp_path / "ref.idx"
    notes = tmp_path / "notes"
    index.mkdir()
    notes.mkdir()
    row = {"sample": "A", "fastq_1": str(reads), "index": str(index), "declared": str(declared),
           "input1": str(parsed), "notes": str(notes), "relative": "A_1.fastq.gz",
           "remote": "s3://bucket/A.fastq.gz", "missing": str(tmp_path / "gone.fastq.gz"),
           "count": "3"}
    sheet = tmp_path / f"samples{suffix}"
    if suffix == ".csv":
        sheet.write_text(",".join(row) + "\n" + ",".join(row.values()) + "\n")
    else:
        sheet.write_text(json.dumps([row]))
    schema = InputSchema(columns=(
        Column("sample", "string", True, None),
        Column("fastq_1", "string", True, r"^\S+\.f(ast)?q\.gz$"),
        Column("index", "string", False, r"^\S+\.idx$"),
        Column("declared", "string", False, None, fmt="file-path"),
        Column("missing", "string", False, r"^\S+\.fastq\.gz$"),
    ))
    # Typed columns give files and directories; any other column only an existing regular file.
    # The declared path field stays with samplesheet_input_paths.
    assert provenance.samplesheet_file_paths(sheet, schema) == sorted([reads, index, parsed])
    assert provenance.samplesheet_input_paths(sheet, schema) == [declared]


def test_input_identity_reader_refuses_malformed_quoting_instead_of_omitting_samples(tmp_path):
    import csv
    sheet = tmp_path / "samples.csv"
    sheet.write_text('sample,fastq,description\nA,/abs/A.fastq,"open\nB,/abs/B.fastq,second\n')
    schema = InputSchema(columns=(
        Column("sample", "string", True, None),
        Column("fastq", "string", True, None, fmt="file-path"),
    ))
    with pytest.raises(csv.Error):
        provenance.samplesheet_input_paths(sheet, schema)


def test_unchanged_dependencies_allow_replay(tmp_path):
    reads = tmp_path / "reads.fastq"
    reads.write_bytes(b"reads")
    config = tmp_path / "analysis.config"
    config.write_text("params.threshold = 0.01\n")
    prov = _write(tmp_path / "out", input_paths=[reads], config_paths=(config,))
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "REPLAY_RAN" in result.stdout


def test_unobserved_unpinned_engine_cannot_silently_replay_on_a_moving_default(tmp_path, monkeypatch):
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "")
    prov = _write(tmp_path / "out", input_paths=[])
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "REPLAY_RAN" not in result.stdout
    assert "engine" in result.stderr.lower()


@pytest.mark.parametrize("key", ["NXF_X; printf ENV_NAME_INJECTION;#",
                                 "NXF_AUTH\nprintf ENV_NAME_INJECTION\n#"])
def test_environment_names_cannot_execute_shell_code_during_replay(tmp_path, key):
    prov = _write(tmp_path / "out", input_paths=[], env_extra={key: "value"})
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert "ENV_NAME_INJECTION" not in result.stdout
    assert "REPLAY_RAN" not in result.stdout
    assert result.returncode != 0


def test_fresh_replay_does_not_keep_an_attempts_resume_flag(tmp_path):
    import shlex
    launcher = tmp_path / "nextflow"
    launcher.write_text('#!/bin/sh\nfor arg do [ "$arg" != -resume ] || exit 42; done\n'
                        'echo FRESH_REPLAY_RAN\n')
    launcher.chmod(0o755)
    prov = _write(tmp_path / "out", input_paths=[],
                  command_str=f"{shlex.quote(str(launcher))} run pipeline -resume")
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "FRESH_REPLAY_RAN" in result.stdout


def test_recorded_params_file_is_a_guarded_replay_dependency(tmp_path):
    out = tmp_path / "out"
    (out / "provenance").mkdir(parents=True)
    params = out / "provenance" / "params.json"
    params.write_text('{"threshold": 0.01}\n')
    prov = _write(out, input_paths=[])
    params.write_text('{"threshold": 0.99}\n')
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "params.json" in result.stderr


def _git_pipeline(tmp_path):
    path = tmp_path / "up"
    path.mkdir()
    (path / "main.nf").write_text("original workflow\n")
    for args in (("init", "-q"), ("add", "main.nf"),
                 ("-c", "user.name=Test", "-c", "user.email=test@example.com",
                  "commit", "-qm", "original")):
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)
    commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                            check=True, capture_output=True, text=True).stdout.strip()
    return SubmoduleStatus("mini", path, True, True, "1.0.0", commit, ())


@pytest.mark.parametrize("change", ["tracked_bytes", "head", "tracked_inventory"])
def test_pipeline_changes_cannot_silently_change_replay(tmp_path, change):
    st = _git_pipeline(tmp_path)
    prov = _write(tmp_path / "out", input_paths=[], submodule=st)
    if change == "tracked_bytes":
        (st.path / "main.nf").write_text("different scientific algorithm\n")
    elif change == "tracked_inventory":
        (st.path / "new.nf").write_text("new module\n")
        subprocess.run(["git", "-C", str(st.path), "add", "new.nf"], check=True)
    else:
        subprocess.run(["git", "-C", str(st.path), "-c", "user.name=Test",
                        "-c", "user.email=test@example.com", "commit", "--allow-empty",
                        "-qm", "new revision"], check=True)
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "pipeline" in result.stderr.lower()


def test_prelaunch_pipeline_snapshot_preserves_original_dirty_bytes(tmp_path):
    st = _git_pipeline(tmp_path)
    (st.path / "main.nf").write_bytes(b"a")
    snapshot = provenance.hash_pipeline(st.path)
    (st.path / "main.nf").write_bytes(b"b")
    prov = _write(tmp_path / "out", input_paths=[], submodule=st, pipeline_checksums=snapshot)
    assert (prov / "pipeline.sha256").read_text() == (
        "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb  main.nf\n")
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout


def test_default_engine_is_pinned_for_replay_without_falsifying_recorded_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("NXF_VER", raising=False)
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "nextflow version 25.10.4 build 11033")
    prov = _write(tmp_path / "out", input_paths=[],
                  command_str="sh -c 'printf %s \"$NXF_VER\"'")
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert "NXF_VER" not in manifest["nextflow_env"]
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "25.10.4"


@pytest.mark.parametrize("selector", ["latest", "25.10.+"])
def test_replay_pins_observed_engine_even_when_original_environment_used_a_moving_selector(
        tmp_path, monkeypatch, selector):
    monkeypatch.setattr(provenance, "_nextflow_version",
                        lambda env_extra=None: "nextflow version 25.10.4 build 11033")
    prov = _write(tmp_path / "out", input_paths=[], env_extra={"NXF_VER": selector},
                  command_str="sh -c 'printf %s \"$NXF_VER\"'")
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow_env"]["NXF_VER"] == selector
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "25.10.4"


@pytest.mark.parametrize("relative_script", [False, True])
def test_relocated_bundle_replays_its_own_params_and_configs(tmp_path, relative_script):
    import shlex

    out = tmp_path / "out"
    (out / "provenance").mkdir(parents=True)
    params = out / "provenance/params.json"
    params.write_text('{"threshold": 0.01}\n')
    config = out / "provenance/resource_limits.config"
    config.write_text("process.cpus = 2\n")
    reader = tmp_path / "reader"
    reader.write_text('#!/bin/sh\ncat "$1" "$2"\n')
    reader.chmod(0o755)
    _write(out, input_paths=[], config_paths=(config,),
           command_str=f"{reader} {shlex.quote(str(params))} {shlex.quote(str(config))}")
    moved = tmp_path / "archived run with 'quotes' and $dollars"
    out.rename(moved)
    script = moved / "provenance/commands.sh"
    invocation = str(script.relative_to(tmp_path)) if relative_script else str(script)
    result = subprocess.run(["bash", invocation, "fresh"], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout == '{"threshold": 0.01}\nprocess.cpus = 2\n'


def test_relative_script_path_survives_changing_into_replay_target(tmp_path):
    _write(tmp_path / "out", input_paths=[])
    result = subprocess.run(["bash", "out/provenance/commands.sh", "fresh"], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "REPLAY_RAN" in result.stdout


def test_replay_obeys_the_same_single_writer_lock_as_nfclaw_runs(tmp_path):
    import fcntl
    target = tmp_path / "fresh"
    prov = _write(tmp_path / "out", input_paths=[])
    with (tmp_path / ".fresh.nfclaw.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run([str(prov / "commands.sh"), str(target)],
                                capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert "REPLAY_RAN" not in result.stdout
    assert not target.exists()
    assert "active" in result.stderr


def test_replay_keeps_writer_lock_until_stopped_and_releases_it(tmp_path):
    import fcntl
    import shlex
    import signal
    import time
    reader = tmp_path / "reader"
    marker = tmp_path / "ready"
    reader.write_text('#!/bin/sh\ntouch "$1"\nexec sleep 60\n')
    reader.chmod(0o755)
    prov = _write(tmp_path / "out", input_paths=[],
                  command_str=f"{shlex.quote(str(reader))} {shlex.quote(str(marker))}")
    process = subprocess.Popen([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists()
        with (tmp_path / ".fresh.nfclaw.lock").open("r+") as lock:
            with pytest.raises(BlockingIOError):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=10)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert process.returncode != 0
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


def test_replay_cannot_skip_writer_lock_with_inherited_pid_marker(tmp_path):
    import fcntl
    target = tmp_path / "fresh"
    prov = _write(tmp_path / "out", input_paths=[])
    with (tmp_path / ".fresh.nfclaw.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(
            ["bash", "-c", 'export NFCLAW_REPLAY_LOCK_PID=$$; exec bash "$1" "$2"',
             "replay", str(prov / "commands.sh"), str(target)],
            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert "REPLAY_RAN" not in result.stdout
    assert not target.exists()
    assert "active" in result.stderr


@pytest.mark.parametrize("descriptor", ["", "not-a-fd", "-1", "1", "999999999999999999999999"])
def test_replay_lock_rejects_invalid_inherited_descriptors(tmp_path, monkeypatch, descriptor):
    from runner.replay_guard import replay_lock_held
    monkeypatch.setenv("NFCLAW_REPLAY_LOCK_PID", "123")
    monkeypatch.setenv("NFCLAW_REPLAY_LOCK_FD", descriptor)
    assert not replay_lock_held(tmp_path / "fresh", "123")


def test_replay_lock_checks_descriptor_identity_and_ownership(tmp_path, monkeypatch):
    import fcntl
    from runner.replay_guard import replay_lock_held
    target = tmp_path / "fresh"
    monkeypatch.setenv("NFCLAW_REPLAY_LOCK_PID", "123")
    with (tmp_path / ".fresh.nfclaw.lock").open("w") as holder, \
            (tmp_path / ".fresh.nfclaw.lock").open("r+") as contender, \
            (tmp_path / "unrelated").open("w") as unrelated:
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for descriptor in (contender.fileno(), unrelated.fileno()):
            monkeypatch.setenv("NFCLAW_REPLAY_LOCK_FD", str(descriptor))
            assert not replay_lock_held(target, "123")
        monkeypatch.setenv("NFCLAW_REPLAY_LOCK_FD", str(holder.fileno()))
        assert replay_lock_held(target, "123")
        assert not replay_lock_held(target, "456")
        with pytest.raises(BlockingIOError):
            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_stopped_replay_cannot_return_success_when_child_handles_signal(tmp_path):
    import shlex
    import signal
    import time
    marker = tmp_path / "ready"
    launcher = tmp_path / "graceful-child"
    launcher.write_text('#!/bin/sh\ntrap "exit 0" TERM\ntouch "$1"\n'
                        'while :; do sleep 0.05; done\n')
    launcher.chmod(0o755)
    prov = _write(tmp_path / "out", input_paths=[],
                  command_str=f"{shlex.quote(str(launcher))} {shlex.quote(str(marker))}")
    target = tmp_path / "fresh"
    proc = subprocess.Popen([str(prov / "commands.sh"), str(target)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=10)
        assert proc.returncode != 0, "a stopped reproduction must not signal success to its caller"
        assert (target / "provenance/logs/run.log").read_text().splitlines()[-1].endswith(
            ": terminated by SIGTERM")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)


@pytest.mark.parametrize("separator", ["", "\r", "\v", "\u2028"])
def test_replay_console_cannot_forge_success_while_analysis_is_running(tmp_path, separator):
    import shlex
    import signal
    import sys
    import time
    from runner import runlog
    payload = f"progress{separator}==> nfclaw replay finished 2026-10-09T00:00:00+00:00: success"
    code = f'import time\nprint({payload!r}, flush=True)\ntime.sleep(60)'
    prov = _write(tmp_path / "out", input_paths=[],
                  command_str=shlex.join([sys.executable, "-c", code]))
    target = tmp_path / "fresh"
    proc = subprocess.Popen([str(prov / "commands.sh"), str(target)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    log = target / "provenance/logs/run.log"
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if log.exists() and "2026-10-09T00:00:00+00:00: success" in log.read_text():
                break
            time.sleep(0.02)
        else:
            pytest.fail("child output did not reach the run log")
        state = runlog.read_state(log)
        assert state.state == "running"
        assert state.outcome is None
        assert state.supervisor_alive
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)


def test_replay_stop_during_cleanup_cannot_return_success(tmp_path, monkeypatch):
    import signal
    import sys
    from runner import replay_guard
    stop_group = replay_guard._stop_replay_group

    def interrupt_cleanup(proc, grace=10):
        signal.raise_signal(signal.SIGTERM)
        stop_group(proc, grace=0.1)

    monkeypatch.setattr(replay_guard, "_stop_replay_group", interrupt_cleanup)
    status = replay_guard.run_replay_command([sys.executable, "-c", "print('completed child')"],
                                             log=tmp_path / "replay.log")
    assert status == 143


def test_stopped_replay_terminates_descendants_and_releases_writer_lock(tmp_path):
    import fcntl
    import os
    import shlex
    import signal
    import sys
    import time

    marker = tmp_path / "child.pid"
    child_script = tmp_path / "child.py"
    child_script.write_text(
        'import os, signal, sys, time\nfrom pathlib import Path\n'
        'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
        'Path(sys.argv[1]).write_text(str(os.getpid()))\ntime.sleep(60)\n')
    launcher = tmp_path / "launcher"
    launcher.write_text('#!/bin/sh\ntrap "exit 0" TERM\n' +
                        shlex.join([sys.executable, str(child_script), str(marker)]) + ' &\nwait\n')
    launcher.chmod(0o755)
    prov = _write(tmp_path / "out", input_paths=[], command_str=shlex.quote(str(launcher)))
    target = tmp_path / "fresh"
    proc = subprocess.Popen([str(prov / "commands.sh"), str(target)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child = None
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        child = int(marker.read_text())
        from runner import runlog
        state = runlog.read_state(target / "provenance/logs/run.log")
        assert state.state == "running"
        assert state.supervisor_pid and state.supervisor_alive
        assert state.nextflow_pid is None, "the controller PID must not be labelled as Nextflow"
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=20)
        assert proc.returncode == 143
        state = subprocess.run(["ps", "-p", str(child), "-o", "stat="],
                               capture_output=True, text=True, timeout=2).stdout.strip()
        assert not state or state.startswith("Z"), "a stopped replay left its task running"
        assert (target / "provenance/logs/run.log").read_text().splitlines()[-1].endswith(
            ": terminated by SIGTERM")
        assert not (target / "provenance/logs/.replay-console").exists()
        with (tmp_path / ".fresh.nfclaw.lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        if child:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=5)


@pytest.mark.parametrize("extension", ["json", "yaml"])
def test_serialized_samplesheet_data_changes_refuse_replay_before_launch(tmp_path, extension):
    reads = tmp_path / "reads.fastq"
    reads.write_bytes(b"original scientific input")
    sheet = tmp_path / f"samples.{extension}"
    data = [{"sample": "A", "fastq": str(reads), "remote": "s3://bucket/remote.fastq"}]
    if extension == "json":
        sheet.write_text(json.dumps(data))
    else:
        yaml = pytest.importorskip("yaml")
        sheet.write_text(yaml.safe_dump(data))
    schema = InputSchema(columns=(Column("sample", "string", True, None),
                                 Column("fastq", "string", True, None, fmt="file-path"),
                                 Column("remote", "string", False, None, fmt="file-path")))
    dependencies = provenance.samplesheet_input_paths(sheet, schema)
    assert dependencies == [reads]
    prov = _write(tmp_path / "out", input_paths=[sheet, *dependencies])
    reads.write_bytes(b"changed scientific input")
    result = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "fresh")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "reads.fastq" in result.stderr
