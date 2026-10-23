import os
import subprocess
import threading

import pytest

from runner import submodule
from runner.errors import ErrorCode, NfclawError


def test_uninitialized_when_empty(tmp_path):
    (tmp_path / "sarek" / "upstream").mkdir(parents=True)
    st = submodule.resolve("sarek", tmp_path)
    assert st.initialized is False
    assert st.complete is False


def test_complete_when_required_files_present(tmp_path):
    up = tmp_path / "sarek" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config", "nextflow_schema.json"):
        (up / f).write_text("x")
    st = submodule.resolve("sarek", tmp_path)
    assert st.initialized is True
    assert st.complete is True
    assert st.missing_files == ()


def test_ensure_initialized_serializes_parallel_init(tmp_path, monkeypatch):
    # Several processes/threads initialising the same submodule at once must not race on
    # .git/config: the lock + re-check means `git submodule update` runs exactly once.
    up = tmp_path / "pipelines" / "mini" / "upstream"
    up.mkdir(parents=True)                                        # exists but empty → not initialised
    calls = []

    def fake_capture(args, **kw):
        if "submodule" in args:                                  # the init call (not the _git reads)
            calls.append(args)
            for f in submodule.REQUIRED_FILES:
                (up / f).write_text("x")                         # simulate a successful init
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(submodule, "capture", fake_capture)
    errors = []

    def worker():
        try:
            submodule.ensure_initialized("mini", tmp_path / "pipelines", tmp_path)
        except Exception as exc:                                 # noqa: BLE001 — record any failure
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(calls) == 1                                       # ran once under the lock + re-check


def test_resolve_at_uses_explicit_path(tmp_path):
    # resolve_at points at an arbitrary tree (e.g. a version worktree), not pipelines/<name>/upstream.
    tree = tmp_path / ".versions" / "1.2.0" / "upstream"
    tree.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config", "nextflow_schema.json"):
        (tree / f).write_text("x")
    st = submodule.resolve_at("sarek", tree)
    assert st.path == tree
    assert st.complete is True


def test_resolve_uses_committed_skill_version_when_shallow_tags_are_absent(tmp_path, monkeypatch):
    # A shallow submodule may not have release tags locally, making `git describe --tags --always`
    # return a short hash. If the committed skill.md matches the exact commit, the pinned release
    # version in that file is the offline source of truth.
    up = tmp_path / "sarek" / "upstream"
    up.mkdir(parents=True)
    for f in submodule.REQUIRED_FILES:
        (up / f).write_text("x")
    (tmp_path / "sarek" / "skill.md").write_text(
        "---\nversion: 2.1.0\ncommit: abcdef1234567890\n---\n")

    def fake_git(path, *args):
        if args == ("rev-parse", "--show-toplevel", "HEAD"):
            return f"{path}\nabcdef1234567890"                    # the tree is its own repo
        if args == ("describe", "--tags", "--always"):
            return "abcdef1"
        return ""

    monkeypatch.setattr(submodule, "_git", fake_git)
    st = submodule.resolve("sarek", tmp_path)
    assert st.version == "2.1.0"


def test_resolve_keeps_git_tag_when_available_even_if_skill_is_stale(tmp_path, monkeypatch):
    up = tmp_path / "sarek" / "upstream"
    up.mkdir(parents=True)
    for f in submodule.REQUIRED_FILES:
        (up / f).write_text("x")
    (tmp_path / "sarek" / "skill.md").write_text(
        "---\nversion: abcdef1\ncommit: abcdef1234567890\n---\n")

    def fake_git(path, *args):
        if args == ("rev-parse", "--show-toplevel", "HEAD"):
            return f"{path}\nabcdef1234567890"                    # the tree is its own repo
        if args == ("describe", "--tags", "--always"):
            return "2.1.0"
        return ""

    monkeypatch.setattr(submodule, "_git", fake_git)
    assert submodule.resolve("sarek", tmp_path).version == "2.1.0"


def test_incomplete_when_files_missing(tmp_path):
    up = tmp_path / "sarek" / "upstream"
    up.mkdir(parents=True)
    (up / "main.nf").write_text("x")  # missing nextflow.config + schema
    st = submodule.resolve("sarek", tmp_path)
    assert st.initialized is True
    assert st.complete is False
    assert "nextflow.config" in st.missing_files


def test_init_failure_is_reported_as_structured_nfclaw_error(tmp_path, monkeypatch):
    up = tmp_path / "pipelines" / "mini" / "upstream"
    up.mkdir(parents=True)

    real_capture = submodule.capture

    def fail_init(args, **kwargs):
        if args[:3] == ["git", "submodule", "update"]:
            raise subprocess.CalledProcessError(1, args, stderr="network unavailable")
        return real_capture(args, **kwargs)

    monkeypatch.setattr(submodule, "capture", fail_init)
    with pytest.raises(NfclawError) as exc:
        submodule.ensure_initialized("mini", tmp_path / "pipelines", tmp_path)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "network unavailable" in str(exc.value)


def _git_repo(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_init_lock_lives_in_the_repositorys_git_dir(tmp_path):
    # The lock used to live in the shared temp dir (/tmp on Linux), where a file left by another user
    # sharing the clone made every first-time `nfclaw run` crash with a raw PermissionError.
    repo = _git_repo(tmp_path / "repo")
    with submodule._init_lock(repo):
        assert (repo / ".git" / "nfclaw-submodule.lock").is_file()


def test_unusable_lock_file_is_a_clean_error_not_a_traceback(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / ".git" / "nfclaw-submodule.lock").mkdir()           # cannot be opened as a lock file
    with pytest.raises(NfclawError) as exc:
        with submodule._init_lock(repo):
            pass
    assert exc.value.code == ErrorCode.ENVIRONMENT
    assert "nfclaw-submodule.lock" in str(exc.value)


def test_lock_never_follows_a_planted_symlink(tmp_path):
    # Opening the lock with "w" followed a symlink and truncated whatever it pointed at.
    repo = _git_repo(tmp_path / "repo")
    victim = tmp_path / "victim.txt"
    victim.write_text("precious")
    os.symlink(victim, repo / ".git" / "nfclaw-submodule.lock")
    with pytest.raises(NfclawError):
        with submodule._init_lock(repo):
            pass
    assert victim.read_text() == "precious"


def _committed_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    for args in (["init", "-q"], ["-c", "user.email=t@t", "-c", "user.name=t",
                                  "commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_a_tree_inside_another_repo_never_reports_that_repos_commit(tmp_path):
    # An uninitialised (or hand-filled) submodule directory sits inside the nf-claw checkout, and git
    # run there answers for nf-claw: provenance recorded nf-claw's HEAD as the pipeline's commit.
    outer_head = _committed_repo(tmp_path)
    up = tmp_path / "pipelines" / "sarek" / "upstream"
    up.mkdir(parents=True)
    for f in submodule.REQUIRED_FILES:
        (up / f).write_text("x")
    st = submodule.resolve("sarek", tmp_path / "pipelines")
    assert st.complete is True                       # the files are there and can still be run...
    assert st.commit == "" and st.version == ""      # ...but no commit is borrowed from nf-claw
    assert outer_head and not submodule.is_git_tree(up)
    assert not submodule.is_git_tree(tmp_path / "pipelines" / "missing" / "upstream")


def test_a_tree_that_is_its_own_repo_reports_its_commit(tmp_path):
    _committed_repo(tmp_path)
    up = tmp_path / "pipelines" / "sarek" / "upstream"
    head = _committed_repo(up)
    assert submodule.is_git_tree(up)
    assert submodule.resolve("sarek", tmp_path / "pipelines").commit == head
