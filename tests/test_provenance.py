import json
import os
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import time

import pytest

from runner import provenance, replay_guard, runlog
from runner.nextflow_command import shell_line
from runner.submodule import SubmoduleStatus
from result_checksums import output_checksums


pytestmark = pytest.mark.usefixtures("no_engine_probe")


def _st(path):
    return SubmoduleStatus("mini", path, True, True, "1.0.0", "deadbeef", ())


def test_writes_manifest_and_checksums(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "result.txt").write_text("data")
    inp = tmp_path / "ss.csv"
    inp.write_text("sample\nA\n")
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[inp])
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["commit"] == "deadbeef" and manifest["version"] == "1.0.0"
    assert "result.txt" in (prov / "outputs.sha256").read_text()
    assert (prov / "commands.sh").exists()


def test_manifest_names_the_nfclaw_that_wrote_it(tmp_path):
    # The pipeline's revision was recorded, but not the wrapper's: a bundle could not say which
    # nfclaw validated, launched and recorded it.
    from runner import version
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nfclaw"] == version.identity()
    assert manifest["nfclaw"]["version"] == version.package_version()


def test_defensive_without_pipeline_info(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert (prov / "run_manifest.json").exists()


def test_excludes_nextflow_internals(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "result.txt").write_text("data")
    (out / ".nextflow").mkdir()
    (out / ".nextflow" / "history").write_text("h")
    (out / ".nextflow.log").write_text("log")
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    sha = (prov / "outputs.sha256").read_text()
    assert "result.txt" in sha and ".nextflow" not in sha          # internals not checksummed


def test_copies_legacy_software_versions_yaml(tmp_path):
    out = tmp_path / "out"
    (out / "pipeline_info").mkdir(parents=True)
    (out / "pipeline_info" / "software_versions.yml").write_text("FASTQC: 0.12.1\n")
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert (prov / "software_versions.yml").read_text() == "FASTQC: 0.12.1\n"


def test_copies_modern_mqc_software_versions_yaml(tmp_path):
    # The newer nf-core template names it `nf_core_<pipeline>_software_mqc_versions.yml` (rnaseq,
    # chipseq, fetchngs, …). The hardcoded `software_versions.yml` never matched it, so versions
    # were silently missing from the bundle for every such pipeline. The file's own name
    # is preserved.
    out = tmp_path / "out"
    (out / "pipeline_info").mkdir(parents=True)
    name = "nf_core_rnaseq_software_mqc_versions.yml"
    (out / "pipeline_info" / name).write_text("STAR: 2.7.11\n")
    prov = provenance.write(outdir=out, pipeline="rnaseq", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert (prov / name).read_text() == "STAR: 2.7.11\n"


def test_no_versions_yaml_is_fine(tmp_path):
    # No pipeline_info/ (or no versions file) must not raise — a run can fail before producing one.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert not list(prov.glob("*software*version*.yml"))


def test_replay_reproduces_into_a_fresh_outdir_not_the_original(tmp_path):
    # An nf-core pipeline publishes into --outdir and cannot re-publish over a previous run's files:
    # Nextflow will not overwrite pipeline_info/execution_trace_*.txt, and sarek's BCO manifest
    # collides outright. Replaying in place therefore failed on contact. --outdir on the command
    # line overrides the params file, so the whole run is redirected by one argument.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    script = (prov / "commands.sh").read_text()
    assert f"default_target='{out}.replay'" in script or f"default_target={out}.replay" in script
    assert 'cd -- "$target"' in script                  # engine state lands beside the new results
    assert 'nextflow run x --outdir "$target"' in script
    assert f"cd {out}\n" not in script                  # never the original directory


def test_replay_refuses_a_target_that_already_holds_results(tmp_path):
    # Executed, not just string-matched: the guard is the whole point of the script.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="true",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "results.txt").write_text("a previous run")
    r = subprocess.run([str(prov / "commands.sh"), str(occupied)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "not empty" in r.stderr
    assert (occupied / "results.txt").read_text() == "a previous run"      # left untouched


def test_replay_runs_in_the_target_directory(tmp_path):
    # The replay must launch from the target, so `.nextflow/` state never lands in the original run.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="pwd >pwd.txt; echo",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    target = tmp_path / "fresh"
    r = subprocess.run([str(prov / "commands.sh"), str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (target / "pwd.txt").read_text().strip() == str(target)


def test_replay_into_a_relative_target_publishes_into_that_target(tmp_path):
    # The script cds into the target before launching, so a relative target passed through as-is
    # became <target>/<target>: `./commands.sh fresh` published into fresh/fresh/, and
    # `nfclaw verify fresh --against out` then reported every file missing. --outdir must
    # be absolute.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="pwd >pwd.txt; echo",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    r = subprocess.run([str(prov / "commands.sh"), "fresh"], cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "fresh" / "pwd.txt").read_text().strip() == str(tmp_path / "fresh")
    assert r.stdout.strip() == f"--outdir {tmp_path / 'fresh'}"


def test_records_nextflow_env_and_probes_version_with_it(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    seen = {}
    monkeypatch.setattr(provenance, "_nextflow_version",
                        lambda env_extra=None: seen.setdefault("env", env_extra) or "ver 25.10.2")
    overlay = {"NXF_VER": "25.10.2", "NXF_JVM_ARGS": "-Dx=y"}
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[], env_extra=overlay)
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow_env"] == overlay          # the overlay nfclaw applied is recorded
    assert seen["env"] == overlay  # version probed with the overlay (reports the pin)


def test_nextflow_env_empty_by_default(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert json.loads((prov / "run_manifest.json").read_text())["nextflow_env"] == {}


def test_commands_sh_reexports_nxf_env_for_faithful_replay(tmp_path):
    # The manifest records the NXF_* overrides, but the *replay script* must apply them too — a run
    # that only works with a pinned engine or an IPv6/offline flag would not reproduce otherwise.
    out = tmp_path / "out"
    out.mkdir()
    overlay = {"NXF_VER": "25.10.2", "NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"}
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[], env_extra=overlay)
    lines = (prov / "commands.sh").read_text().splitlines()
    # Deterministic order (sorted), exported before the command, then the command itself.
    assert "export NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true" in lines
    assert "export NXF_VER=25.10.2" in lines
    run_line = next(i for i, line in enumerate(lines) if line.startswith("nextflow run x"))
    assert lines.index("export NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true") \
        < lines.index("export NXF_VER=25.10.2") < run_line


def test_commands_sh_quotes_env_values_with_spaces(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[],
                            env_extra={"NXF_JVM_ARGS": "-Dx=y -Dz=w"})
    assert "export NXF_JVM_ARGS='-Dx=y -Dz=w'" in (prov / "commands.sh").read_text()


def test_sensitive_nxf_env_is_redacted_and_omitted_from_replay(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    overlay = {
        "NXF_GITHUB_TOKEN": "top-secret-token",
        "NXF_JVM_ARGS": "-DproxyPassword=hunter2",
        "NXF_VER": "25.10.2",
    }
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[], env_extra=overlay)
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow_env"] == {
        "NXF_GITHUB_TOKEN": "<redacted>",
        "NXF_JVM_ARGS": "<redacted>",
        "NXF_VER": "25.10.2",
    }
    assert manifest["redacted_nextflow_env"] == ["NXF_GITHUB_TOKEN", "NXF_JVM_ARGS"]
    replay = (prov / "commands.sh").read_text()
    assert "top-secret-token" not in replay and "hunter2" not in replay
    assert "export NXF_VER=25.10.2" in replay
    assert "Export these before replay: NXF_GITHUB_TOKEN NXF_JVM_ARGS" in replay


def test_uri_userinfo_credentials_are_redacted_without_a_sensitive_variable_name(tmp_path):
    overlay = {"NXF_JVM_ARGS": "-Dhttps.proxy=http://alice:private-value@proxy.example:8080",
               "NXF_ASSETS": "https://opaque-credential@source.example/repository"}
    prov = provenance.write(outdir=tmp_path / "out", pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[], env_extra=overlay)
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow_env"] == {name: "<redacted>" for name in overlay}
    assert manifest["redacted_nextflow_env"] == sorted(overlay)
    replay = (prov / "commands.sh").read_text()
    assert "private-value" not in replay and "opaque-credential" not in replay
    assert not any(f"export {name}=" in replay for name in overlay)
    displayed = shell_line("nextflow run x", overlay)
    assert "private-value" not in displayed and "opaque-credential" not in displayed


def test_public_urls_and_noncredential_at_signs_remain_replayable(tmp_path):
    overlay = {"NXF_ASSETS": "https://source.example/repository", "NXF_CUSTOM": "owner@example.org"}
    prov = provenance.write(outdir=tmp_path / "out", pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[], env_extra=overlay)
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow_env"] == overlay
    assert not manifest.get("redacted_nextflow_env")


def test_commands_sh_has_no_exports_without_env_or_observed_engine(tmp_path, monkeypatch):
    # No environment or observed engine version → no invented export lines.
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "")
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert "export " not in (prov / "commands.sh").read_text()


def test_inherited_nxf_env_is_recorded_and_replayed(tmp_path, monkeypatch):
    # NXF_OFFLINE exported in the shell (not via --nxf-env) still shapes the run, so the bundle must
    # carry it: replaying elsewhere without it would try to reach the network and fail.
    monkeypatch.setenv("NXF_OFFLINE", "true")
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert json.loads((prov / "run_manifest.json").read_text())["nextflow_env"] == {
        "NXF_OFFLINE": "true"}
    assert "export NXF_OFFLINE=true" in (prov / "commands.sh").read_text()


def test_overlay_wins_over_inherited_nxf_env(tmp_path, monkeypatch):
    # --nxf-ver overrides an exported NXF_VER at launch, so provenance must record the pin that
    # actually ran, not the shell's value.
    monkeypatch.setenv("NXF_VER", "24.04.0")
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[],
                            env_extra={"NXF_VER": "25.10.2"})
    assert json.loads((prov / "run_manifest.json").read_text())["nextflow_env"] == {
        "NXF_VER": "25.10.2"}
    assert "export NXF_VER=25.10.2" in (prov / "commands.sh").read_text()


def test_inherited_sensitive_nxf_env_is_redacted(tmp_path, monkeypatch):
    # The shell is a far larger surface than the overlay, so redaction has to cover it too.
    monkeypatch.setenv("NXF_GITHUB_TOKEN", "top-secret-token")
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["nextflow_env"] == {"NXF_GITHUB_TOKEN": "<redacted>"}
    assert "top-secret-token" not in (prov / "commands.sh").read_text()


def test_outcome_is_recorded(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert json.loads((prov / "run_manifest.json").read_text())["outcome"] == "success"
    prov = provenance.write(outdir=out, pipeline="mini", command_str="x",
                            submodule=_st(tmp_path / "up"), input_paths=[], outcome="failed")
    assert json.loads((prov / "run_manifest.json").read_text())["outcome"] == "failed"


def test_commands_sh_is_executable(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    assert (prov / "commands.sh").stat().st_mode & 0o111        # user/group/other execute bit set


def test_bundle_files_are_as_readable_as_any_new_file(tmp_path):
    # commands.sh is executable for all, so a replay by another member of the results' group must
    # read the manifest and the replay scripts too. Written through tempfile, every other bundle
    # file was 0o600. The source archive is written by replay_guard, the rest by runner.atomic.
    up = tmp_path / "up"
    up.mkdir()
    (up / "main.nf").write_text("workflow {}\n")
    out = tmp_path / "out"
    out.mkdir()
    previous = os.umask(0o022)
    try:
        prov = provenance.write(outdir=out, pipeline="mini", command_str="nextflow run x",
                                submodule=_st(up), input_paths=[])
    finally:
        os.umask(previous)
    modes = {p.name: stat.S_IMODE(p.stat().st_mode) for p in prov.iterdir() if p.is_file()}
    assert modes.pop("commands.sh") == 0o755
    assert {"run_manifest.json", "replay_guard.py", provenance.PIPELINE_ARCHIVE} <= modes.keys()
    assert set(modes.values()) == {0o644}, modes
    assert not [p.name for p in prov.iterdir() if p.name.startswith(".")]


def test_the_run_logs_seek_index_is_as_readable_as_the_log(tmp_path):
    # Another member of the results' group polls `nfclaw status` from run.log; its seek index was
    # written through tempfile, so it was 0o600 beside a 0o644 log and their poll lost it.
    previous = os.umask(0o022)
    try:
        log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    finally:
        os.umask(previous)
    cursor = replay_guard.log_cursor_path(log.path)
    assert stat.S_IMODE(cursor.stat().st_mode) == stat.S_IMODE(log.path.stat().st_mode) == 0o644
    assert not [p.name for p in log.path.parent.iterdir() if p.name.startswith(".")]


def test_replay_logs_itself_into_the_target_bundle(tmp_path):
    # A replay is a run too: it logs to <target>/provenance/logs/run.log exactly like the original,
    # so it needs no `> replay.log 2>&1` of its own — and the log ends with the outcome.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="echo REPLAYED",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    target = tmp_path / "fresh"
    r = subprocess.run([str(prov / "commands.sh"), str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "REPLAYED" in r.stdout                                  # still on the terminal
    log = (target / "provenance" / "logs" / "run.log").read_text()
    assert "==> nfclaw replay started" in log and "REPLAYED" in log
    assert log.rstrip().splitlines()[-1].endswith(": success")
    assert f"logging this replay to {target / 'provenance' / 'logs' / 'run.log'}" in r.stderr


def test_replay_failure_keeps_its_exit_status_and_is_logged(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="sh -c 'echo NOPE; exit 7'",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    target = tmp_path / "fresh"
    r = subprocess.run([str(prov / "commands.sh"), str(target)], capture_output=True, text=True)
    assert r.returncode == 7
    log = (target / "provenance" / "logs" / "run.log").read_text()
    assert "NOPE" in log
    assert log.rstrip().splitlines()[-1].endswith(": failed (exit status 7)")


def test_replay_log_is_not_counted_as_a_replayed_output(tmp_path):
    # `nfclaw verify` hashes the replay directory; its log must not show up as an "extra" result.
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="echo",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    target = tmp_path / "fresh"
    subprocess.run([str(prov / "commands.sh"), str(target)], capture_output=True, check=True)
    assert output_checksums(target) == {}


def test_manifest_records_the_chain_link_only_when_given(tmp_path):
    # A plain run's manifest is unchanged; a chain stage's names the chain and the run feeding it.
    provenance.write(outdir=tmp_path / "a", pipeline="mini", command_str="nextflow run x",
                     submodule=_st(tmp_path / "up"), input_paths=[])
    assert "chain" not in json.loads((tmp_path / "a/provenance/run_manifest.json").read_text())
    link = {"id": "c1", "stage": "mini", "index": 2, "upstream": {"stage": "up"}}
    provenance.write(outdir=tmp_path / "b", pipeline="mini", command_str="nextflow run x",
                     submodule=_st(tmp_path / "up"), input_paths=[], chain=link)
    assert json.loads((tmp_path / "b/provenance/run_manifest.json").read_text())["chain"] == link


def test_replay_header_records_who_runs_it(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini", command_str="echo",
                            submodule=_st(tmp_path / "up"), input_paths=[])
    target = tmp_path / "fresh"
    subprocess.run([str(prov / "commands.sh"), str(target)], capture_output=True, check=True)
    log = (target / "provenance" / "logs" / "run.log").read_text()
    assert f"    host: {socket.gethostname()}\n" in log and "    pid: " in log
    if identity := runlog.host_identity():
        assert f"    host id: {identity}\n" in log


def test_a_stopped_replay_stops_nextflow_and_logs_the_outcome(tmp_path):
    # Like `nfclaw run`: `kill <replay pid>` must not leave Nextflow running with the
    # log open-ended.
    pidfile = tmp_path / "child.pid"
    out = tmp_path / "out"
    out.mkdir()
    prov = provenance.write(outdir=out, pipeline="mini",
                            command_str=(f"sh -c 'echo started; echo $$ > {pidfile}.tmp; "
                                         f"mv {pidfile}.tmp {pidfile}; exec sleep 30'"),
                            submodule=_st(tmp_path / "up"), input_paths=[])
    target = tmp_path / "fresh"
    for bash in ("/bin/bash", "bash"):                       # macOS ships bash 3.2 as /bin/bash
        if target.exists():
            shutil.rmtree(target)
        pidfile.unlink(missing_ok=True)
        replay = subprocess.Popen([bash, str(prov / "commands.sh"), str(target)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + 10
        while not pidfile.exists() and time.time() < deadline:
            time.sleep(0.1)
        child = int(pidfile.read_text())
        replay.send_signal(signal.SIGTERM)
        _, err = replay.communicate(timeout=20)
        assert replay.returncode != 0
        try:
            os.kill(child, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        assert not alive, f"{bash}: the replayed command outlived the replay"
        log = (target / "provenance" / "logs" / "run.log").read_text()
        assert "started" in log
        assert log.rstrip().splitlines()[-1].endswith(": terminated by SIGTERM"), bash
        assert not (target / "provenance" / "logs" / ".replay-console").exists()


@pytest.mark.parametrize("bash", ["/bin/bash", "bash"])
def test_replay_verification_can_be_stopped_without_claiming_success(tmp_path, bash):
    completed = tmp_path / "command_completed"
    pidfile = tmp_path / "verification.pid"
    out = tmp_path / "out"
    out.mkdir()
    # The replay appends `--outdir <target>`; GNU touch would parse it as an option, so the
    # recorded command ignores trailing arguments, like the other replay tests here.
    prov = provenance.write(outdir=out, pipeline="mini",
                            command_str=shlex.join(["sh", "-c", "touch "
                                                                f"{shlex.quote(str(completed))}"]),
                            submodule=_st(tmp_path / "up"), input_paths=[])
    guard = prov / "replay_guard.py"
    text = guard.read_text()
    marker = 'def verify_dependencies(bundle: Path, replay_target: Path | None = None) -> None:\n'
    gate = (f'    if Path({str(completed)!r}).exists():\n'
            f'        Path({str(pidfile)!r}).write_text(str(os.getpid()))\n'
            '        import time\n        time.sleep(30)\n')
    assert marker in text
    guard.write_text(text.replace(marker, marker + gate, 1))
    target = tmp_path / "fresh"
    replay = subprocess.Popen([bash, str(prov / "commands.sh"), str(target)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        while not pidfile.exists():
            assert replay.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.05)
        child = int(pidfile.read_text())
        replay.send_signal(signal.SIGTERM)
        _, stderr = replay.communicate(timeout=10)
        assert replay.returncode == 143, stderr
        with pytest.raises(ProcessLookupError):
            os.kill(child, 0)
        log = (target / "provenance/logs/run.log").read_text()
        assert log.rstrip().splitlines()[-1].endswith(": terminated by SIGTERM")
        assert not (target / "provenance/logs/.replay-verification").exists()
    finally:
        if replay.poll() is None:
            replay.kill()
            replay.communicate(timeout=5)
