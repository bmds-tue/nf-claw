"""Setup operations have finite limits without creating an analysis deadline."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from contextlib import nullcontext

import pytest

from librarian import update_pipelines
from runner import budget, engine_version, path_roles, preflight, settings, submodule, versions
from runner.errors import ErrorCode, NfclawError
from runner.schema import Param, ParamSchema


def test_timeout_setting_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("NFCLAW_GIT_TIMEOUT", raising=False)
    assert settings.seconds("NFCLAW_GIT_TIMEOUT", 120) == 120


@pytest.mark.parametrize("value", ["0.05", "3", " 2.5 ", "1e2"])
def test_timeout_setting_accepts_finite_positive_seconds(monkeypatch, value):
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", value)
    assert settings.seconds("NFCLAW_GIT_TIMEOUT", 120) == float(value)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "", "later"])
def test_timeout_setting_rejects_invalid_values_by_name(monkeypatch, value):
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", value)
    with pytest.raises(NfclawError) as exc:
        settings.seconds("NFCLAW_GIT_TIMEOUT", 120)
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "NFCLAW_GIT_TIMEOUT" in str(exc.value)
    assert "positive" in str(exc.value) and "finite" in str(exc.value)


@pytest.mark.parametrize("probe", ["nextflow", "java"])
def test_engine_version_probes_honor_configured_limit(monkeypatch, probe):
    monkeypatch.setenv("NFCLAW_VERSION_TIMEOUT", "0.25")
    seen = []

    def capture(command, **kwargs):
        seen.append(kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, "nextflow version 25.10.4 build 1",
                                           'openjdk version "17.0.1"')

    monkeypatch.setattr(engine_version, "capture", capture)
    if probe == "nextflow":
        assert engine_version._installed_raw() == "nextflow version 25.10.4 build 1"
    else:
        assert engine_version.java_major_for_nextflow({}) == 17
    assert seen == [0.25]


def test_remote_tags_times_out_and_retains_offline_fallback(monkeypatch, tmp_path):
    fake = tmp_path / "git"
    fake.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(0.5)\n"
                    "print('a' * 40 + '\\trefs/tags/1.0.0')\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", "0.05")
    started = time.monotonic()
    assert versions.remote_tags("https://example.invalid/p.git") == []
    assert time.monotonic() - started < 0.4


@pytest.mark.parametrize("operation,defaults", [
    ("remote_tags", [60]), ("remote_branch_head", [60]),
    ("_fetch_dev", [120]), ("_fetch_tag", [120]),
    ("_record_dev_head", [30]), ("_add_worktree", [30, 120]),
])
@pytest.mark.parametrize("override", [None, "0.25"])
def test_version_git_operations_use_group_capture_and_named_limits(
        monkeypatch, tmp_path, operation, defaults, override):
    if override is None:
        monkeypatch.delenv("NFCLAW_GIT_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", override)
    seen = []

    def capture(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    # Stub the old boundary too, so a missing migration fails immediately without network I/O.
    monkeypatch.setattr(versions, "capture", capture, raising=False)
    monkeypatch.setattr(versions.subprocess, "run",
                        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    calls = {
        "remote_tags": lambda: versions.remote_tags("https://example.invalid/p.git"),
        "remote_branch_head": lambda: versions.remote_branch_head(
            "https://example.invalid/p.git", "dev"),
        "_fetch_dev": lambda: versions._fetch_dev(tmp_path),
        "_fetch_tag": lambda: versions._fetch_tag(tmp_path, "1.0.0"),
        "_record_dev_head": lambda: versions._record_dev_head(tmp_path, "a" * 40),
        "_add_worktree": lambda: versions._add_worktree(tmp_path,
                                                        tmp_path / "cache" / "upstream", "a" * 40),
    }
    calls[operation]()
    assert [kw["timeout"] for _, kw in seen] == ([0.25] * len(defaults) if override else defaults)
    assert all(kw["env"]["GIT_TERMINAL_PROMPT"] == "0" for _, kw in seen)


@pytest.mark.parametrize("operation", ["_fetch_dev", "_fetch_tag", "_add_worktree"])
def test_version_git_mutations_reject_nonzero_exit(monkeypatch, tmp_path, operation):
    def capture(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "network unavailable")

    monkeypatch.setattr(versions, "capture", capture, raising=False)
    monkeypatch.setattr(versions.subprocess, "run",
                        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    with pytest.raises(subprocess.CalledProcessError, match="returned non-zero"):
        if operation == "_fetch_dev":
            versions._fetch_dev(tmp_path)
        elif operation == "_fetch_tag":
            versions._fetch_tag(tmp_path, "1.0.0")
        else:
            versions._add_worktree(tmp_path, tmp_path / "cache" / "upstream", "a" * 40)


def test_local_git_probe_keeps_filesystem_byte_contract(monkeypatch, tmp_path):
    seen = []

    def capture(command, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(command, 0, b"file-\xff\n", b"")

    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", "0.25")
    monkeypatch.setattr(submodule, "capture", capture, raising=False)
    monkeypatch.setattr(submodule.subprocess, "run",
                        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, b"", b""))
    assert submodule._git(tmp_path, "tag", "--list") == os.fsdecode(b"file-\xff")
    assert seen[0]["text"] is False and seen[0]["timeout"] == 0.25
    assert seen[0]["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_modification_probe_uses_bounded_group_capture(monkeypatch, tmp_path):
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", "0.25")
    monkeypatch.setattr(submodule, "_own_head", lambda path: "a" * 40)
    seen = []

    def capture(command, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(command, 0, " M main.nf\0R  new.nf\0old.nf\0", "")

    monkeypatch.setattr(submodule, "capture", capture, raising=False)
    monkeypatch.setattr(submodule.subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, "", ""))
    assert submodule.modified_files(tmp_path) == ["main.nf", "new.nf"]
    assert seen[0]["timeout"] == 0.25
    assert seen[0]["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_submodule_init_uses_its_named_limit_and_checks_exit(monkeypatch, tmp_path):
    incomplete = submodule.SubmoduleStatus("p", tmp_path, False, False, "", "", ("main.nf",))
    monkeypatch.setattr(submodule, "resolve", lambda *args: incomplete)
    monkeypatch.setattr(submodule, "_init_lock", lambda *args: nullcontext())
    monkeypatch.setenv("NFCLAW_INIT_TIMEOUT", "0.25")
    seen = []

    def capture(command, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(command, 1, "", "connection reset")

    monkeypatch.setattr(submodule, "capture", capture, raising=False)
    monkeypatch.setattr(submodule.subprocess, "run",
                        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    with pytest.raises(NfclawError) as exc:
        submodule.ensure_initialized("p", tmp_path / "pipelines", tmp_path)
    assert "connection reset" in str(exc.value)
    assert seen[0]["timeout"] == 0.25
    assert seen[0]["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_maintenance_git_calls_are_bounded_and_noninteractive(monkeypatch, tmp_path):
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", "0.25")
    seen = []

    def capture(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "a\trefs/tags/1.0.0\n", "")

    monkeypatch.setattr(update_pipelines, "capture", capture, raising=False)
    monkeypatch.setattr(subprocess, "run", capture)
    monkeypatch.setattr(update_pipelines.submod, "is_git_tree", lambda path: True)
    monkeypatch.setattr(update_pipelines.write_skill, "generate", lambda *args, **kwargs: None)
    assert update_pipelines.bump("p", "https://example.invalid/p.git", tmp_path) == "1.0.0"
    assert len(seen) == 4
    assert all(kw.get("timeout") == 0.25 for _, kw in seen)
    assert all(kw.get("env", {}).get("GIT_TERMINAL_PROMPT") == "0" for _, kw in seen)


def test_maintenance_reports_git_failure(monkeypatch):
    monkeypatch.setattr(update_pipelines, "capture", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, "", "network unavailable"),
                        raising=False)
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, "", ""))
    with pytest.raises(subprocess.CalledProcessError):
        update_pipelines.remote_tags("https://example.invalid/p.git")


def test_maintenance_keeps_captured_git_diagnostics(monkeypatch, tmp_path, capsys):
    sources = tmp_path / "sources.tsv"
    sources.write_text("p\thttps://example.invalid/p.git\n")
    monkeypatch.setattr(update_pipelines.submod, "_own_head", lambda path: "a" * 40)
    monkeypatch.setattr(update_pipelines.submod, "is_git_tree", lambda path: True)

    def capture(command, **kwargs):
        if "ls-remote" in command:
            return subprocess.CompletedProcess(command, 0, "a\trefs/tags/1.0.0\n", "")
        return subprocess.CompletedProcess(command, 1, "", "fatal: network unavailable")

    monkeypatch.setattr(update_pipelines, "capture", capture)
    assert update_pipelines.main(["--sources", str(sources), "--repo-root", str(tmp_path)]) == 1
    assert "fatal: network unavailable" in capsys.readouterr().out


def test_init_lock_waiting_for_a_thread_honors_explicit_budget(monkeypatch, tmp_path):
    lock = threading.Lock()
    lock.acquire()
    monkeypatch.setattr(submodule, "_thread_lock", lambda key: lock)
    release = threading.Timer(0.3, lock.release)
    release.start()
    started = time.monotonic()
    try:
        with pytest.raises(NfclawError) as exc:
            with budget.scope(0.05):
                with submodule._init_lock(tmp_path):
                    pytest.fail("an expired lock wait must not enter the setup section")
        assert exc.value.code == ErrorCode.EXECUTION_FAILED
        assert time.monotonic() - started < 0.25
    finally:
        release.join()
    assert not lock.locked()


@pytest.mark.skipif(submodule.fcntl is None, reason="requires POSIX file locks")
def test_init_lock_waiting_for_another_process_honors_explicit_budget(monkeypatch, tmp_path):
    lock_path = tmp_path / "init.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    submodule.fcntl.flock(fd, submodule.fcntl.LOCK_EX)
    monkeypatch.setattr(submodule, "_lock_path", lambda root: lock_path)
    release = threading.Timer(0.3, lambda: submodule.fcntl.flock(fd, submodule.fcntl.LOCK_UN))
    release.start()
    started = time.monotonic()
    try:
        with pytest.raises(NfclawError) as exc:
            with budget.scope(0.05):
                with submodule._init_lock(tmp_path):
                    pytest.fail("an expired lock wait must not enter the setup section")
        assert exc.value.code == ErrorCode.EXECUTION_FAILED
        assert time.monotonic() - started < 0.25
    finally:
        release.join()
        os.close(fd)
    # An expired waiter must release its thread lock for the next caller.
    with submodule._init_lock(tmp_path):
        pass


def test_init_lock_has_no_total_wait_limit_without_a_run_budget(monkeypatch, tmp_path):
    lock = threading.Lock()
    lock.acquire()
    monkeypatch.setattr(submodule, "_thread_lock", lambda key: lock)
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", "0.01")
    monkeypatch.setattr(submodule, "_lock_path", lambda root: tmp_path / "init.lock")
    release = threading.Timer(0.1, lock.release)
    release.start()
    started = time.monotonic()
    try:
        with submodule._init_lock(tmp_path):
            assert time.monotonic() - started >= 0.08
    finally:
        release.join()


@pytest.mark.parametrize("probe", ["docker", "git"])
def test_preflight_probe_honors_active_run_budget(monkeypatch, tmp_path, probe):
    binary = tmp_path / probe
    binary.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(0.3)\n")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(preflight.shutil, "which", lambda tool: f"/tools/{tool}")
    root = tmp_path / "repo"
    root.mkdir()
    out = root / "results" if probe == "git" else tmp_path / "results"
    status = submodule.SubmoduleStatus("p", root / "upstream", True, True, "1.0.0", "a" * 40, ())
    with pytest.raises(NfclawError) as exc:
        with budget.scope(0.05):
            preflight.check_environment(profile="docker" if probe == "docker" else "singularity",
                                        output_dir=out, submodule=status,
                                        repo_root=root, resume=False)
    assert exc.value.code == ErrorCode.EXECUTION_FAILED
    assert exc.value.details["timeout_seconds"] == 0.05


@pytest.mark.parametrize("probe,override,expected_timeout", [
    ("docker", None, 10), ("git", None, 10), ("git", "0.25", 0.25),
])
def test_preflight_probe_keeps_default_limit_and_failure_diagnostic(
        monkeypatch, tmp_path, probe, override, expected_timeout):
    if override is None:
        monkeypatch.delenv("NFCLAW_GIT_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", override)
    monkeypatch.setattr(preflight.shutil, "which", lambda tool: f"/tools/{tool}")
    seen = []

    def capture(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1, b"", b"")

    monkeypatch.setattr(preflight, "capture", capture, raising=False)
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, b"", b""))
    root = tmp_path / "repo"
    root.mkdir()
    out = root / "results" if probe == "git" else tmp_path / "results"
    status = submodule.SubmoduleStatus("p", root / "upstream", True, True, "1.0.0", "a" * 40, ())
    issues = preflight.check_environment(profile="docker" if probe == "docker" else "singularity",
                                        output_dir=out, submodule=status,
                                         repo_root=root, resume=False)
    assert [kwargs["timeout"] for _, kwargs in seen] == [expected_timeout]
    if probe == "git":
        assert seen[0][1]["env"]["GIT_TERMINAL_PROMPT"] == "0"
    expected = ("docker daemon not responding" if probe == "docker"
                else "outside the repo or a gitignored path")
    assert any(expected in issue for issue in issues)


@pytest.fixture
def audited_directory_role(monkeypatch, tmp_path):
    commit = "a" * 40
    registry = tmp_path / "path_roles.json"
    registry.write_text(json.dumps({commit: {"temp_dir": {"pipeline": "p"}}}))
    monkeypatch.setattr(path_roles, "_REGISTRY", registry)
    monkeypatch.setattr(path_roles, "_own_head", lambda path: commit)
    loaded = ParamSchema("p", "", {"temp_dir": Param("temp_dir", "string", None, None, "",
                                                    "directory-path", False, "")})
    status = submodule.SubmoduleStatus("p", tmp_path, True, True, "1.0.0", commit, ())
    return status, loaded


def test_path_role_git_status_honors_active_run_budget(monkeypatch, tmp_path,
                                                       audited_directory_role):
    binary = tmp_path / "git"
    binary.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(0.3)\n")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    with pytest.raises(NfclawError) as exc:
        with budget.scope(0.05):
            path_roles.output_only_directories(*audited_directory_role)
    assert exc.value.code == ErrorCode.EXECUTION_FAILED


@pytest.mark.parametrize("override", [None, "0.25"])
def test_path_role_probe_keeps_default_and_accepts_git_limit(
        monkeypatch, audited_directory_role, override):
    if override is None:
        monkeypatch.delenv("NFCLAW_GIT_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", override)
    seen = []

    def capture(command, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(path_roles, "capture", capture, raising=False)
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, "", ""))
    assert path_roles.output_only_directories(*audited_directory_role) == frozenset({"temp_dir"})
    assert [kwargs["timeout"] for kwargs in seen] == [30 if override is None else 0.25]
    assert seen[0]["env"]["GIT_TERMINAL_PROMPT"] == "0"


@pytest.mark.parametrize("returncode,output", [(1, ""), (0, " M main.nf\n")])
def test_path_role_probe_failure_or_dirty_status_never_grants_exemption(
        monkeypatch, audited_directory_role, returncode, output):
    monkeypatch.setattr(path_roles, "capture", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, returncode, output,
                                                    "fatal: cannot inspect"),
                        raising=False)
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, "", ""))
    assert path_roles.output_only_directories(*audited_directory_role) == frozenset()
