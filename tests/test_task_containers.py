"""A stopped run removes the task containers it started.

Reproduced on a Docker host (Nextflow 26.04.3): after SIGTERM, each task wrapper runs `docker stop`
on its container, which waits 10 s for a PID 1 that ignores SIGTERM, while nfclaw's grace period
is 10 s too. The wrappers were killed first, so their own `docker rm` never ran: every stopped run
left its task containers behind exited, and with a shorter grace still running.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from runner import execution, replay_guard
from runner.runlog import RunLog

pytestmark = pytest.mark.skipif(not hasattr(os, "killpg"), reason="POSIX process groups")

# Stands in for the engine's client: `run` marks its container as existing and stays in the
# foreground like `docker run -i`, ignoring SIGTERM; `rm -f` removes existing ones by name.
FAKE_ENGINE = """#!/bin/bash
echo "$*" >> "$ENGINE_LOG"
case "$1" in
  run)
    for arg; do case "$arg" in
      nxf-*) touch "$ENGINE_STATE/$arg" ;;
      --name=nxf-*) touch "$ENGINE_STATE/${arg#--name=}" ;;
    esac; done
    trap '' TERM
    while :; do sleep 0.1; done ;;
  rm)
    shift; [ "$1" = -f ] && shift
    for name; do
      if [ -e "$ENGINE_STATE/$name" ]; then rm "$ENGINE_STATE/$name"; echo "$name"
      else echo "Error response from daemon: No such container: $name" >&2; fi
    done ;;
esac
"""


@pytest.fixture
def engine(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    state = tmp_path / "containers"
    bin_dir.mkdir()
    state.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(FAKE_ENGINE)
    docker.chmod(0o755)
    monkeypatch.setenv("ENGINE_LOG", str(tmp_path / "engine.log"))
    monkeypatch.setenv("ENGINE_STATE", str(state))
    return docker, state, tmp_path / "engine.log"


def _group(tmp_path: Path, *tasks: str) -> subprocess.Popen:
    """A process group like Nextflow's: a leader with task clients running in the background."""
    leader = tmp_path / "leader.sh"
    leader.write_text("#!/bin/bash\n" + "".join(f"{task} >/dev/null 2>&1 </dev/null &\n"
                                                 for task in tasks) + "sleep 300\n")
    leader.chmod(0o755)
    return subprocess.Popen([str(leader)], start_new_session=True)


def _wait_for(state: Path, *names: str) -> None:
    deadline = time.monotonic() + 10
    while not all((state / name).exists() for name in names):
        assert time.monotonic() < deadline, f"task containers never started: {names}"
        time.sleep(0.05)


def _kill(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, 9)
    except ProcessLookupError:
        pass
    proc.wait()


def test_the_group_s_task_containers_are_found_by_name(engine, tmp_path):
    docker, state, _ = engine
    other = subprocess.Popen([str(docker), "run", "--name", "nxf-elsewhere", "img"],
                             start_new_session=True)          # another run's task: not ours
    proc = _group(tmp_path, f"{docker} run -i --name nxf-Ab12 img /bin/bash -ue x.sh",
                  f"{docker} run --name=nxf-Cd34 img", f"{docker} run --name not-a-task img",
                  f"{docker} pull img")
    try:
        _wait_for(state, "nxf-Ab12", "nxf-Cd34", "nxf-elsewhere")
        found = replay_guard.task_containers(proc.pid)
    finally:
        _kill(proc)
        _kill(other)
    assert {names for names in map(frozenset, found.values())} == {
        frozenset({"nxf-Ab12", "nxf-Cd34"})}
    (launcher,) = found
    assert Path(launcher[-1]) == docker                # removal uses the same client


def test_removal_reports_what_it_removed_and_what_it_could_not(engine):
    docker, state, log = engine
    (state / "nxf-left").touch()
    removed, problems = replay_guard.remove_task_containers(
        {(str(docker),): {"nxf-left", "nxf-gone"}})
    assert removed == ["nxf-left"]
    assert problems == []                               # already removed by its wrapper: fine
    assert {"rm -f nxf-gone", "rm -f nxf-left"} <= set(log.read_text().splitlines())

    broken = docker.with_name("podman")
    broken.write_text("#!/bin/bash\necho 'Error: cannot connect to the engine' >&2\nexit 125\n")
    broken.chmod(0o755)
    removed, problems = replay_guard.remove_task_containers({(str(broken),): {"nxf-x"}})
    assert removed == [] and problems == ["Error: cannot connect to the engine"]

    removed, problems = replay_guard.remove_task_containers({("/nonexistent/docker",): {"nxf-x"}})
    assert removed == [] and "could not run" in problems[0]


def test_removal_through_sudo_never_waits_for_a_password(engine, tmp_path):
    # Nextflow's `docker.sudo = true` runs `sudo docker run …`; the removal goes the same way, but
    # non-interactively: a password prompt would hold the shutdown for the whole removal limit.
    docker, state, log = engine
    sudo = tmp_path / "bin" / "sudo"
    sudo.write_text('#!/bin/bash\necho "sudo $*" >> "$ENGINE_LOG"\n'
                    '[ "$1" = -n ] && shift\nexec "$@"\n')
    sudo.chmod(0o755)
    (state / "nxf-viasudo").touch()
    removed, problems = replay_guard.remove_task_containers(
        {(str(sudo), str(docker)): {"nxf-viasudo"}})
    assert (removed, problems) == (["nxf-viasudo"], [])
    assert f"sudo -n {docker} rm -f nxf-viasudo" in log.read_text().splitlines()


def test_a_stopped_run_removes_containers_its_wrappers_left_behind(engine, tmp_path, capfd):
    docker, state, log = engine
    proc = _group(tmp_path, f"{docker} run -i --name nxf-Task1 img",
                  f"{docker} run -i --name nxf-Task2 img")
    run_log = RunLog(tmp_path / "logs" / "run.log")
    try:
        _wait_for(state, "nxf-Task1", "nxf-Task2")
        execution._terminate(proc, grace=0.5, run_log=run_log)
    finally:
        _kill(proc)
    run_log.finish()
    assert not list(state.iterdir())
    assert {"rm -f nxf-Task1", "rm -f nxf-Task2"} <= set(log.read_text().splitlines())
    message = "removed 2 task container(s) the stopped run left behind: nxf-Task1, nxf-Task2"
    assert message in capfd.readouterr().err
    assert message in run_log.path.read_text()


def test_a_run_without_task_containers_calls_no_engine(engine, tmp_path):
    _, _, log = engine
    proc = _group(tmp_path, "sleep 300")
    try:
        execution._terminate(proc, grace=0.5)
    finally:
        _kill(proc)
    assert not log.exists()


def test_a_stopped_replay_removes_containers_and_logs_it(engine, tmp_path):
    docker, state, _ = engine
    script = tmp_path / "replay.sh"
    script.write_text(f"#!/bin/bash\n{docker} run -i --name nxf-Replay1 img &\nsleep 300\n")
    script.chmod(0o755)
    log = tmp_path / "logs" / "run.log"
    log.parent.mkdir()
    log.write_text("==> nfclaw replay started 2026-10-30T00:00:00+00:00\n")
    proc = subprocess.Popen(
        [sys.executable, "-c",
         "import sys; from pathlib import Path; from runner import replay_guard; "
         "sys.exit(replay_guard.run_replay_command([sys.argv[1]], log=Path(sys.argv[2]), "
         "grace=0.5))", str(script), str(log)],
        cwd=Path(__file__).resolve().parent.parent, stderr=subprocess.PIPE, text=True)
    try:
        _wait_for(state, "nxf-Replay1")
        proc.terminate()
        _, stderr = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 128 + 15
    assert not list(state.iterdir())
    message = "nfclaw replay: removed 1 task container(s) the stopped replay left behind: " \
              "nxf-Replay1"
    assert message in stderr
    assert log.read_text().splitlines()[-1] == message


def test_a_second_interrupt_during_the_grace_period_still_removes_them(engine, tmp_path,
                                                                      monkeypatch):
    # A second Ctrl-C asks to stop now: the group is killed at once, and its containers go too.
    docker, state, log = engine
    proc = _group(tmp_path, f"{docker} run -i --name nxf-Again1 img")
    _wait_for(state, "nxf-Again1")
    wait = proc.wait

    def interrupted(timeout=None):
        if timeout is not None:
            raise KeyboardInterrupt
        return wait()

    monkeypatch.setattr(proc, "wait", interrupted)
    try:
        with pytest.raises(KeyboardInterrupt):
            execution._terminate(proc, grace=30)
    finally:
        _kill(proc)
    assert not list(state.iterdir())
    assert "rm -f nxf-Again1" in log.read_text().splitlines()


def _signals_after_the_group_ended(monkeypatch, stop) -> tuple[list, list]:
    """Run `stop` on a group whose leader is reaped and whose members are all gone, recording the
    group signals it sends and the container searches it makes."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    proc.wait()
    sent, searched = [], []
    killpg = os.killpg

    def record(pgid, sig):
        sent.append(sig)
        return killpg(pgid, sig)

    monkeypatch.setattr(os, "killpg", record)
    monkeypatch.setattr(replay_guard, "task_containers",
                        lambda pgid: searched.append(pgid) or {})
    stop(proc)
    return sent, searched


def test_a_finished_group_s_number_is_neither_searched_nor_signalled(monkeypatch):
    # Once the leader is reaped and no member is left, the group's number is free for another
    # process group: only a liveness probe (signal 0) may reach it.
    sent, searched = _signals_after_the_group_ended(
        monkeypatch, lambda proc: execution._terminate(proc, grace=0.2))
    assert set(sent) <= {0} and searched == []


def test_a_finished_replay_group_s_number_is_neither_searched_nor_signalled(monkeypatch):
    sent, searched = _signals_after_the_group_ended(
        monkeypatch, lambda proc: replay_guard._stop_replay_group(proc, grace=0.2))
    assert set(sent) <= {0} and searched == []


def test_a_group_that_outlives_its_reaped_leader_is_still_stopped(engine, tmp_path):
    # The leader exits first and is reaped; a task client it left in the group keeps the group's
    # number, so its container is still found and removed and the client killed.
    docker, state, log = engine
    leader = tmp_path / "leader.sh"
    leader.write_text(f"#!/bin/bash\n{docker} run -i --name nxf-Orphan1 img "
                      f">/dev/null 2>&1 </dev/null &\nwhile [ ! -e {state}/nxf-Orphan1 ]; do "
                      "sleep 0.05; done\n")
    leader.chmod(0o755)
    proc = subprocess.Popen([str(leader)], start_new_session=True)
    try:
        proc.wait(timeout=10)
        execution._terminate(proc, grace=0.2)
        assert not execution._group_alive(proc.pid)
    finally:
        _kill(proc)
    assert not list(state.iterdir())
    assert "rm -f nxf-Orphan1" in log.read_text().splitlines()
