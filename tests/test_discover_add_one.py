"""Pinning a submodule to a release tag must record the gitlink AT THE TAG.

Regression test for the discovery drift bug: `git submodule add` records the default
branch HEAD, and the scaffolding then checks out the tag only in the working tree. If the
recorded gitlink is left at the default HEAD, a later `git submodule update` (run by the
Nextflow-acceptance step) resets the working tree off the tag, so `git describe --tags`
returns `<tag>-N-g<hash>` and the drift gate flags the freshly generated context as stale.
This bit pipelines whose default branch had commits after the release. `add_one` and
`bump` (auto-update) share the same pin-to-tag contract, so both are covered here."""
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from librarian import discover_pipelines as dp
from librarian import update_pipelines as up_mod
from librarian import write_skill
from test_version_probe_cleanup import _alive

_SCHEMA = Path(__file__).parent / "fixtures" / "mini" / "nextflow_schema.json"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), check=True,
                          capture_output=True, text=True).stdout.strip()


def _commit(origin: Path, msg: str) -> None:
    (origin / "main.nf").write_text(f"workflow {{ /* {msg} */ }}\n")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", msg)


def _make_origin(origin: Path) -> dict[str, str]:
    """A pipeline repo with tags 1.0.0 and 1.1.0, whose default branch HEAD is AHEAD of both."""
    origin.mkdir()
    _git(origin, "init", "-q")
    _git(origin, "config", "user.email", "t@t")
    _git(origin, "config", "user.name", "t")
    (origin / "nextflow.config").write_text("manifest { nextflowVersion = '!>=24.04.0' }\n")
    (origin / "nextflow_schema.json").write_text(_SCHEMA.read_text(encoding="utf-8"))
    commits = {}
    _commit(origin, "release 1.0.0")
    _git(origin, "tag", "1.0.0")
    commits["1.0.0"] = _git(origin, "rev-list", "-n1", "1.0.0")
    _commit(origin, "release 1.1.0")
    _git(origin, "tag", "1.1.0")
    commits["1.1.0"] = _git(origin, "rev-list", "-n1", "1.1.0")
    _commit(origin, "post-release dev")                        # default HEAD now != any tag
    return commits


def _make_superproject(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")


def _allow_file_submodules(monkeypatch) -> None:
    # git blocks the file:// transport for submodules by default (CVE-2022-39253); allow it
    # for every child git process in this test via injected config.
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")


def _assert_pinned_to(repo: Path, name: str, tag: str, tag_commit: str) -> None:
    """The recorded gitlink is the tag commit, and a `git submodule update` keeps it there."""
    up = repo / "pipelines" / name / "upstream"
    assert _git(up, "describe", "--tags") == tag
    gitlink = _git(repo, "ls-files", "-s", f"pipelines/{name}/upstream").split()[1]
    assert gitlink == tag_commit
    _git(repo, "submodule", "update", "--init", f"pipelines/{name}/upstream")
    assert _git(up, "describe", "--tags") == tag               # survived the reset
    sk_disk = (repo / "pipelines" / name / "skill.md").read_text(encoding="utf-8")
    sk_ren, _ = write_skill.render(name, pipelines_dir=repo / "pipelines")
    assert sk_disk == sk_ren                                   # no drift


def test_add_one_pins_gitlink_to_tag(tmp_path, monkeypatch):
    _allow_file_submodules(monkeypatch)
    commits = _make_origin(tmp_path / "origin")
    _make_superproject(tmp_path / "repo")
    repo = tmp_path / "repo"

    assert dp.add_one("mini", (tmp_path / "origin").as_uri(), "1.0.0", repo)
    _assert_pinned_to(repo, "mini", "1.0.0", commits["1.0.0"])


@pytest.mark.parametrize("kind", ["directory", "symlink", "broken_symlink"])
def test_failed_discovery_does_not_delete_a_preexisting_pipeline_entry(tmp_path, monkeypatch, kind):
    repo = tmp_path / "repo"
    _make_superproject(repo)
    entry = repo / "pipelines/mini"
    entry.parent.mkdir()
    data = tmp_path / "scientific_data"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"irreplaceable scientific data")
    if kind == "directory":
        entry.mkdir()
        (entry / "notes.txt").write_bytes(b"existing research notes")
    else:
        entry.symlink_to(data if kind == "symlink" else tmp_path / "missing",
                         target_is_directory=True)
    calls = []
    def fail_add(args, **kwargs):
        calls.append(args)
        if "add" in args and "submodule" in args:
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    monkeypatch.setattr(dp, "_run", fail_add)
    assert not dp.add_one("mini", "https://github.com/nf-core/mini", "1.0.0", repo)
    if kind == "directory":
        assert (entry / "notes.txt").read_bytes() == b"existing research notes"
    else:
        assert entry.is_symlink()
    assert source.read_bytes() == b"irreplaceable scientific data"
    assert not calls, "An existing pipeline entry must be refused before Git mutations or rollback"


def test_bump_pins_gitlink_to_new_tag(tmp_path, monkeypatch):
    _allow_file_submodules(monkeypatch)
    commits = _make_origin(tmp_path / "origin")
    _make_superproject(tmp_path / "repo")
    repo = tmp_path / "repo"
    url = (tmp_path / "origin").as_uri()

    assert dp.add_one("mini", url, "1.0.0", repo)              # start pinned at the old release
    assert up_mod.bump("mini", url, repo) == "1.1.0"           # auto-update to the newest tag
    _assert_pinned_to(repo, "mini", "1.1.0", commits["1.1.0"])


@pytest.mark.parametrize("linked_worktree", [False, True])
def test_failed_discovery_preserves_a_preexisting_submodule_object_store(tmp_path, monkeypatch,
                                                                         linked_worktree):
    _allow_file_submodules(monkeypatch)
    _make_origin(tmp_path / "origin")
    repo = tmp_path / "repo"
    _make_superproject(repo)
    if linked_worktree:
        _git(repo, "worktree", "add", "--detach", str(tmp_path / "linked"), "HEAD")
        repo = tmp_path / "linked"
    url = (tmp_path / "origin").as_uri()
    assert dp.add_one("mini", url, "1.0.0", repo)
    relative = "pipelines/mini/upstream"
    administrative = Path(_git(repo, "rev-parse", "--git-path", f"modules/{relative}"))
    if not administrative.is_absolute():
        administrative = repo / administrative
    # Removing a checkout legitimately leaves Git's cached object store. An orphaned store
    # can contain unpublished research history even after its entry disappears from the index.
    _git(repo, "submodule", "deinit", "-f", relative)
    _git(repo, "rm", "-f", relative)
    shutil.rmtree(repo / "pipelines/mini")
    marker = administrative / "research-notes.txt"
    marker.write_bytes(b"irreplaceable cached research history")
    before = _git(repo, "status", "--porcelain")
    assert not dp.add_one("mini", url, "99.0.0", repo)
    assert marker.read_bytes() == b"irreplaceable cached research history"
    assert _git(repo, "status", "--porcelain") == before


@pytest.mark.parametrize("state",
                         ["index", "registration", "custom_registration", "partial_registration",
                                    "local_configuration", "symlink_parent", "nested_root"])
def test_discovery_refuses_preexisting_git_ownership_without_mutation(tmp_path, monkeypatch, state):
    _allow_file_submodules(monkeypatch)
    _make_origin(tmp_path / "origin")
    repo = tmp_path / "repo"
    _make_superproject(repo)
    root = repo
    if state == "index":
        head = _git(repo, "rev-parse", "HEAD")
        _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{head},pipelines/mini/upstream")
    elif state in {"registration", "custom_registration"}:
        name = "pipelines/mini/upstream" if state == "registration" else "research-cache"
        (repo / ".gitmodules").write_text(f'[submodule "{name}"]\n'
            '\tpath = pipelines/mini/upstream\n\turl = https://example.invalid/research.git\n')
        _git(repo, "add", ".gitmodules")
    elif state == "partial_registration":
        (repo / ".gitmodules").write_text('[submodule "pipelines/mini/upstream"]\n'
            '\turl = https://example.invalid/research.git\n')
        _git(repo, "add", ".gitmodules")
    elif state == "local_configuration":
        _git(repo, "config", "submodule.pipelines/mini/upstream.url",
             "https://example.invalid/research.git")
    elif state == "symlink_parent":
        external = tmp_path / "external"
        external.mkdir()
        (repo / "pipelines").symlink_to(external, target_is_directory=True)
    else:
        root = repo / "nested"
        root.mkdir()
    before = (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s"))
    gitmodules = repo / ".gitmodules"
    metadata = gitmodules.read_bytes() if gitmodules.exists() else None
    configuration = _git(repo, "config", "--local", "--list")
    assert not dp.add_one("mini", (tmp_path / "origin").as_uri(), "99.0.0", root)
    assert not (root / "pipelines/mini").exists()
    assert (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s")) == before
    assert (gitmodules.read_bytes() if gitmodules.exists() else None) == metadata
    assert _git(repo, "config", "--local", "--list") == configuration


def test_discovery_serializes_ownership_across_concurrent_additions(tmp_path, monkeypatch):
    _allow_file_submodules(monkeypatch)
    commits = _make_origin(tmp_path / "origin")
    repo = tmp_path / "repo"
    _make_superproject(repo)
    barrier = threading.Barrier(2)
    def add():
        barrier.wait(timeout=10)
        return dp.add_one("mini", (tmp_path / "origin").as_uri(), "1.0.0", repo)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: add(), range(2)))
    assert sorted(results) == [False, True]
    _assert_pinned_to(repo, "mini", "1.0.0", commits["1.0.0"])


@pytest.mark.parametrize("state", ["absent", "untracked", "staged", "conflicted", "symlink",
                                    "assume_unchanged", "skip_worktree", "intent_to_add"])
def test_failed_new_discovery_restores_original_gitmodules_bytes_and_index(tmp_path,
                                                                           monkeypatch, state):
    _allow_file_submodules(monkeypatch)
    _make_origin(tmp_path / "origin")
    repo = tmp_path / "repo"
    _make_superproject(repo)
    path = repo / ".gitmodules"
    if state != "absent":
        path.write_text("# Original research metadata\n")
    if state in {"staged", "assume_unchanged", "skip_worktree"}:
        (repo / ".gitmodules").write_text("# Original staged research metadata\n")
        _git(repo, "add", ".gitmodules")
        (repo / ".gitmodules").write_text("# Unstaged research metadata must stay unstaged\n")
        if state != "staged":
            _git(repo, "update-index", "--" + state.replace("_", "-"), ".gitmodules")
    elif state == "intent_to_add":
        _git(repo, "add", "--intent-to-add", ".gitmodules")
    elif state == "conflicted":
        digest = _git(repo, "hash-object", "-w", ".gitmodules")
        subprocess.run(["git", "update-index", "--index-info"], cwd=repo, check=True,
                       input=f"100644 {digest} 1\t.gitmodules\n100644 {digest} 2\t.gitmodules\n",
                       text=True, capture_output=True)
    elif state == "symlink":
        target = tmp_path / "external_metadata"
        path.rename(target)
        path.symlink_to(target)
    before = (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s"),
              _git(repo, "ls-files", "-v"))
    metadata = path.read_bytes() if path.exists() else None
    assert not dp.add_one("mini", (tmp_path / "origin").as_uri(), "99.0.0", repo)
    assert (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s"),
            _git(repo, "ls-files", "-v")) == before
    assert (path.read_bytes() if path.exists() else None) == metadata
    assert not (repo / "pipelines/mini").exists()
    assert path.is_symlink() == (state == "symlink")


def test_interrupted_discovery_restores_metadata_before_propagating_interrupt(
        tmp_path, monkeypatch):
    _allow_file_submodules(monkeypatch)
    _make_origin(tmp_path / "origin")
    repo = tmp_path / "repo"
    _make_superproject(repo)
    before = (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s"))
    run = dp._run
    def interrupt_fetch(args, **kwargs):
        if "fetch" in args:
            raise KeyboardInterrupt
        return run(args, **kwargs)
    monkeypatch.setattr(dp, "_run", interrupt_fetch)
    with pytest.raises(KeyboardInterrupt):
        dp.add_one("mini", (tmp_path / "origin").as_uri(), "1.0.0", repo)
    assert (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s")) == before
    assert not (repo / "pipelines/mini").exists() and not (repo / ".gitmodules").exists()


def test_timed_out_discovery_git_command_stops_its_helper_children(tmp_path, monkeypatch):
    if not hasattr(os, "killpg"):
        pytest.skip("requires POSIX process groups")
    launcher = tmp_path / "git-helper"
    marker = tmp_path / "child.pid"
    launcher.write_text('#!/bin/sh\nsleep 60 &\necho $! >"$CHILD_PID_FILE"\nwait\n')
    launcher.chmod(0o755)
    monkeypatch.setenv("CHILD_PID_FILE", str(marker))
    communicate = subprocess.Popen.communicate
    def timeout_after_child_starts(self, input=None, timeout=None):
        if timeout == 60:
            deadline = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert marker.exists(), "fixture child never started"
            timeout = 0.03
        return communicate(self, input=input, timeout=timeout)
    monkeypatch.setattr(subprocess.Popen, "communicate", timeout_after_child_starts)
    child = None
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            dp._run([str(launcher)], timeout=60)
        child = int(marker.read_text())
        deadline = time.monotonic() + 2
        while _alive(child) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not _alive(child), "a timed-out Git command left its network helper running"
    finally:
        if child is not None and _alive(child):
            os.kill(child, signal.SIGKILL)


def test_sigterm_discovery_stops_helpers_and_restores_git_state(tmp_path, monkeypatch):
    if not hasattr(os, "killpg"):
        pytest.skip("requires POSIX process groups")
    _allow_file_submodules(monkeypatch)
    _make_origin(tmp_path / "origin")
    repo = tmp_path / "repo"
    _make_superproject(repo)
    before = (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s"))
    marker = tmp_path / "child.pid"
    launcher = tmp_path / "network-helper"
    launcher.write_text('#!/bin/sh\nsleep 60 &\necho $! >"$CHILD_PID_FILE"\nwait\n')
    launcher.chmod(0o755)
    script = '''import sys
from pathlib import Path
from librarian import discover_pipelines as dp
from runner import execution
original = dp._run
def stalled_fetch(args, **kwargs):
    if "fetch" in args:
        return original([sys.argv[3]])
    return original(args, **kwargs)
dp._run = stalled_fetch
try:
    dp.add_one("mini", Path(sys.argv[2]).as_uri(), "1.0.0", Path(sys.argv[1]))
except execution.Terminated as error:
    raise SystemExit(128 + error.signum)
'''
    env = {**os.environ, "CHILD_PID_FILE": str(marker),
           "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    proc = subprocess.Popen(
        [sys.executable, "-c", script, str(repo), str(tmp_path / "origin"), str(launcher)],
        env=env, cwd=tmp_path, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    child = None
    try:
        deadline = time.monotonic() + 15
        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists(), "discovery never entered its blocked fetch"
        child = int(marker.read_text())
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=10)
        assert proc.returncode == 128 + signal.SIGTERM, stdout + stderr
        assert not _alive(child), "terminated discovery left its network helper running"
        assert (_git(repo, "status", "--porcelain"), _git(repo, "ls-files", "-s")) == before
        assert not (repo / "pipelines/mini").exists() and not (repo / ".gitmodules").exists()
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=2)
        if child is not None and _alive(child):
            os.kill(child, signal.SIGKILL)
        proc.stdout.close()
        proc.stderr.close()
