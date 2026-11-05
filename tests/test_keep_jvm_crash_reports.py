"""scripts/keep_jvm_crash_reports.py: CI keeps the JVM crash reports a failed test run leaves."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "keep_jvm_crash_reports.py"
RUN = "pytest-of-runner/pytest-0/popen-gw3/test_chain_0/results/02-consumer"


@pytest.fixture
def tmp(tmp_path):
    """A stand-in temporary directory, removed afterwards: the reports planted in it lie inside
    this suite's own pytest tree, where a real failed run's collection would find them."""
    path = tmp_path / "tmp"
    path.mkdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _keep(tmp: Path, dest: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(dest)], capture_output=True,
                          text=True, env={**os.environ, "TMPDIR": str(tmp)}, timeout=60)


def test_reports_are_kept_once_under_their_path_below_the_temporary_directory(tmp, tmp_path):
    stage = tmp / RUN
    stage.mkdir(parents=True)
    (stage / "hs_err_pid15768.log").write_text("# SIGSEGV (0xb) planted by a test\n")
    (stage / "replay_pid15768.log").write_text("planted by a test\n")
    (stage / "core.15768").write_bytes(b"\0" * 64)
    (stage / ".nextflow.log").write_text("planted by a test\n")
    (tmp / "pytest-of-runner/pytest-current").symlink_to(tmp / "pytest-of-runner/pytest-0")
    # The JVM's fallback when its working directory is not writable.
    (tmp / "hs_err_pid7.log").write_text("planted by a test\n")
    (tmp / "elsewhere").mkdir()
    (tmp / "elsewhere/hs_err_pid1.log").write_text("not from a test run\n")
    dest = tmp_path / "evidence/jvm-crashes"

    result = _keep(tmp, dest)

    assert result.returncode == 0, result.stderr
    kept = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    assert kept == ["hs_err_pid7.log", f"{RUN}/hs_err_pid15768.log", f"{RUN}/replay_pid15768.log"]
    assert (dest / RUN / "hs_err_pid15768.log").read_text() == "# SIGSEGV (0xb) planted by a test\n"
    assert result.stdout.count("kept JVM crash report") == 3


def test_a_run_without_crash_reports_succeeds_and_copies_nothing(tmp, tmp_path):
    (tmp / "pytest-of-runner/pytest-0/test_a0").mkdir(parents=True)
    dest = tmp_path / "jvm-crashes"

    result = _keep(tmp, dest)

    assert (result.returncode, result.stdout) == (0, ""), result.stderr
    assert not dest.exists()
