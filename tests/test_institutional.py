"""nf-core institutional configs are read at one recorded nf-core/configs commit."""
import json
import subprocess

import pytest

from runner import institutional

_REAL_LS_REMOTE = institutional._ls_remote          # before the suite's offline stub replaces it
COMMIT = "0123456789abcdef0123456789abcdef01234567"
TEMPLATE = """params {
    custom_config_version      = 'master'
    custom_config_base         = "https://raw.githubusercontent.com/nf-core/configs/${params.custom_config_version}"
}
includeConfig params.custom_config_base && (!System.getenv('NXF_OFFLINE') || !params.custom_config_base.startsWith('http')) ? "${params.custom_config_base}/nfcore_custom.config" : "/dev/null"
"""  # noqa: E501
SCHEMA = {"custom_config_version": {}, "custom_config_base": {}, "outdir": {}}


@pytest.fixture
def upstream(tmp_path):
    (tmp_path / "nextflow.config").write_text(TEMPLATE)
    return tmp_path


@pytest.fixture
def resolver(monkeypatch):
    calls = []

    def resolve(repository, ref):
        calls.append((repository, ref))
        return COMMIT, None
    monkeypatch.setattr(institutional, "_ls_remote", resolve)
    return calls


def test_master_is_resolved_and_passed_as_the_configs_version(upstream, resolver):
    params, record, advisory = institutional.pin({"outdir": "/o"}, SCHEMA, upstream, {})
    assert params == {"outdir": "/o", "custom_config_version": COMMIT}
    assert record == {"repository": "https://github.com/nf-core/configs", "ref": "master",
                      "commit": COMMIT}
    assert resolver == [("https://github.com/nf-core/configs", "master")]
    assert COMMIT[:12] in advisory


@pytest.mark.parametrize("given", [{"custom_config_version": "dev"},
                                   {"custom_config_base": "/local/configs"}])
def test_a_caller_choice_is_kept(upstream, resolver, given):
    params, record, advisory = institutional.pin(dict(given), SCHEMA, upstream, {})
    assert params == given and record is None and advisory is None and resolver == []


def test_a_caller_commit_is_recorded(upstream, resolver):
    params, record, _ = institutional.pin({"custom_config_version": COMMIT}, SCHEMA, upstream, {})
    assert params == {"custom_config_version": COMMIT} and record["commit"] == COMMIT
    assert resolver == []


def test_offline_runs_include_no_configs(upstream, resolver):
    assert institutional.pin({}, SCHEMA, upstream, {"NXF_OFFLINE": "true"}) == ({}, None, None)


def test_a_release_without_the_include_is_left_alone(tmp_path, resolver):
    (tmp_path / "nextflow.config").write_text("params.outdir = null\n")
    assert institutional.pin({}, SCHEMA, tmp_path, {}) == ({}, None, None)
    assert institutional.pin({}, {"outdir": {}}, tmp_path, {}) == ({}, None, None)


def test_a_resolution_failure_is_reported_not_fatal(upstream, monkeypatch):
    monkeypatch.setattr(institutional, "_ls_remote",
                        lambda repository, ref: (None, "git ls-remote failed: network unreachable"))
    params, record, advisory = institutional.pin({}, SCHEMA, upstream, {})
    assert params == {} and record["commit"] is None and "network unreachable" in record["error"]
    assert "not pinned" in advisory


def test_a_resumed_run_keeps_the_commit_its_first_attempt_read(upstream, resolver, tmp_path):
    out = tmp_path / "out"
    (out / "provenance").mkdir(parents=True)
    earlier = "f" * 40
    (out / "provenance" / "params.json").write_text(json.dumps({"custom_config_version": earlier}))
    previous = institutional.previous_commit(out)
    params, record, _ = institutional.pin({}, SCHEMA, upstream, {}, previous=previous)
    assert params["custom_config_version"] == earlier and record["commit"] == earlier
    assert resolver == []


@pytest.mark.parametrize("returncode,stdout,stderr,expected", [
    (0, f"{COMMIT}\trefs/heads/master\n", "", (COMMIT, None)),
    (2, "", "", (None, "git ls-remote https://github.com/nf-core/configs master failed: "
                       "exit status 2")),
    (128, "", "fatal: unable to access: Could not resolve host\n",
     (None, "git ls-remote https://github.com/nf-core/configs master failed: "
            "fatal: unable to access: Could not resolve host")),
])
def test_ls_remote_reads_the_branch_head(monkeypatch, returncode, stdout, stderr, expected):
    seen = {}

    def run(command, **kwargs):
        seen.update(command=command, env=kwargs["env"])
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)
    monkeypatch.setattr(institutional, "capture", run)
    assert _REAL_LS_REMOTE("https://github.com/nf-core/configs", "master") == expected
    assert seen["command"] == ["git", "ls-remote", "--exit-code",
                               "https://github.com/nf-core/configs",
                               "refs/heads/master"]
    assert seen["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_lookup_honours_the_git_timeout_setting(monkeypatch):
    # Every other remote Git probe reads NFCLAW_GIT_TIMEOUT; this one was fixed at 30 seconds.
    seen = {}

    def run(command, **kwargs):
        seen.update(timeout=kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, f"{COMMIT}\trefs/heads/master\n", "")
    monkeypatch.setattr(institutional, "capture", run)
    monkeypatch.setenv("NFCLAW_GIT_TIMEOUT", "95")
    assert _REAL_LS_REMOTE("https://github.com/nf-core/configs", "master") == (COMMIT, None)
    assert seen["timeout"] == 95
    monkeypatch.delenv("NFCLAW_GIT_TIMEOUT")
    _REAL_LS_REMOTE("https://github.com/nf-core/configs", "master")
    assert seen["timeout"] == 30


def test_lookup_obeys_active_budget_and_stops_download_helpers(tmp_path, monkeypatch):
    import os
    import time
    from runner import budget
    from runner.errors import NfclawError
    from test_version_probe_cleanup import _alive
    marker = tmp_path / 'child.pid'
    git = tmp_path / 'git'
    git.write_text(f'#!/bin/sh\nsleep 60 &\necho $! > "{marker}"\nwait\n')
    git.chmod(0o755)
    monkeypatch.setenv('PATH', f'{tmp_path}:{os.environ["PATH"]}')
    popen = subprocess.Popen

    class Started(popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Let the deadline meet a fake git that has started its helper: scheduler delays on a
            # busy host must not turn this into a test of shell startup speed.
            deadline = time.monotonic() + 10
            while (not (marker.exists() and marker.read_text().strip())
                   and self.poll() is None and time.monotonic() < deadline):
                time.sleep(0.02)
    monkeypatch.setattr(subprocess, 'Popen', Started)
    start = time.monotonic()
    with pytest.raises(NfclawError):
        with budget.scope(0.5):
            _REAL_LS_REMOTE('https://github.com/nf-core/configs', 'master')
    assert time.monotonic() - start < 15          # the 60 s helper never sets the pace
    assert marker.exists()
    assert not _alive(int(marker.read_text()))
