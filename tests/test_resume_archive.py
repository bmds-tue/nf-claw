"""Fresh cache sessions preserve old evidence and cannot retain stale publications."""
import subprocess
from pathlib import Path

import pytest

from runner import outputs, provenance, resume_safety
from runner.errors import NfclawError
from runner.submodule import SubmoduleStatus


@pytest.mark.parametrize("aliased_outdir", [False, True])
def test_archive_preserves_results_links_bundle_and_log_history(tmp_path, monkeypatch, aliased_outdir):
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "test engine")
    physical = tmp_path / "analysis"
    physical.mkdir()
    out = physical
    if aliased_outdir:
        out = tmp_path / "alias"
        out.symlink_to(physical, target_is_directory=True)
    source = tmp_path / "data"
    source.mkdir()
    (source / "empty_sample").mkdir()
    work = physical / "work/task"
    work.mkdir(parents=True)
    (work / "reads.txt").write_bytes(b"recorded reads")
    results = physical / "result"
    results.mkdir()
    (results / "absolute.txt").symlink_to(work / "reads.txt")
    (results / "relative.txt").symlink_to("../work/task/reads.txt")
    (physical / "provenance/logs").mkdir(parents=True)
    (physical / "provenance/logs/run.log").write_text("recorded log\n")
    (physical / "provenance/params.json").write_text('{"scientific_parameter": 42}\n')
    provenance.write(outdir=out, pipeline="fixture", command_str="echo REPLAY_RAN",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[source])
    before = provenance.output_checksums(out)
    _, inventory = provenance.snapshot_inputs([source])
    archive = resume_safety.archive_previous_run(out, inventory, [])
    assert provenance.output_checksums(archive) == before
    recorded = outputs.read_inventory(archive / "provenance/outputs.inventory.json", before)
    assert outputs.snapshot(archive)[1] == recorded
    assert not (out / "result").exists()
    assert (out / "provenance/logs/run.log").read_text() == "recorded log\n"
    assert (archive / "provenance/logs/run.log").read_text() == "recorded log\n"
    assert (archive / "result/absolute.txt").resolve() == archive / "work/task/reads.txt"
    assert (archive / "result/relative.txt").resolve() == archive / "work/task/reads.txt"
    replay = subprocess.run([str(archive / "provenance/commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert "REPLAY_RAN" in replay.stdout


@pytest.mark.parametrize("dependency", ["inside_input", "ancestor_input", "inside_config", "inside_pipeline"])
def test_archiving_cannot_move_or_modify_dependencies_of_the_new_launch(tmp_path, dependency):
    out = tmp_path / "analysis"
    out.mkdir()
    data = out / "reads.txt"
    data.write_bytes(b"scientific data")
    inventory = {}
    configurations = []
    if dependency == "inside_input":
        _, inventory = provenance.snapshot_inputs([data])
    elif dependency == "ancestor_input":
        _, inventory = provenance.snapshot_inputs([tmp_path])
    elif dependency == "inside_config":
        config = out / "extra.config"
        config.write_text("process.cpus=1\n")
        configurations = [config]
    else:
        pipeline = out / "pipeline"
        pipeline.mkdir()
        configurations = [pipeline]
    before = provenance.snapshot_inputs([out])
    with pytest.raises(NfclawError, match="Cannot preserve the previous run"):
        resume_safety.archive_previous_run(out, inventory, configurations)
    assert provenance.snapshot_inputs([out]) == before
    assert not list(tmp_path.glob("analysis.previous-*"))


def test_archive_cannot_bypass_an_active_nextflow_database_lock(tmp_path):
    import select
    import sys
    out = tmp_path / "analysis"
    lock = out / ".nextflow/cache/session/db/LOCK"
    lock.parent.mkdir(parents=True)
    lock.write_bytes(b"")
    before = provenance.snapshot_inputs([out])
    holder = subprocess.Popen([sys.executable, "-u", "-c", """
import fcntl, sys
with open(sys.argv[1], 'r+b') as handle:
    fcntl.lockf(handle, fcntl.LOCK_EX)
    print('LOCKED', flush=True)
    sys.stdin.readline()
""", str(lock)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        ready, _, _ = select.select([holder.stdout], [], [], 5)
        assert ready and holder.stdout.readline().strip() == "LOCKED"
        with pytest.raises(NfclawError, match="session is active or locked"):
            resume_safety.archive_previous_run(out, {}, [])
        assert provenance.snapshot_inputs([out]) == before
        assert not list(tmp_path.glob("analysis.previous-*"))
    finally:
        holder.communicate("release\n", timeout=5)


def test_archive_filename_respects_filesystem_byte_limits_for_unicode_names(tmp_path):
    out = tmp_path / ("é" * 115)
    out.mkdir()
    (out / "scientific.txt").write_bytes(b"retained scientific output")
    archive = resume_safety.archive_previous_run(out, {}, [])
    assert (archive / "scientific.txt").read_bytes() == b"retained scientific output"
    assert out.is_dir() and not list(out.iterdir())


@pytest.mark.parametrize("target_kind", ["absolute_alias", "relative_alias", "relative_original"])
def test_archive_keeps_publications_addressed_through_old_directory_names(tmp_path, target_kind):
    out = tmp_path / "analysis"
    work = out / "work/task"
    work.mkdir(parents=True)
    data = work / "reads.txt"
    data.write_bytes(b"OLD\n")
    alias = tmp_path / "alias"
    alias.symlink_to(out, target_is_directory=True)
    target = {"absolute_alias": str(alias / "work/task/reads.txt"),
              "relative_alias": "../alias/work/task/reads.txt",
              "relative_original": "../analysis/work/task/reads.txt"}[target_kind]
    (out / "published.txt").symlink_to(target)
    before = provenance.output_checksums(out)
    archive = resume_safety.archive_previous_run(alias, {}, [])
    assert provenance.output_checksums(archive) == before
    replacement = out / "work/task/reads.txt"
    replacement.parent.mkdir(parents=True)
    replacement.write_bytes(b"NEW\n")
    assert (archive / "published.txt").read_bytes() == b"OLD\n"


@pytest.mark.parametrize("error", [OSError, KeyboardInterrupt])
def test_failed_archive_replacement_restores_the_complete_original_tree(tmp_path, monkeypatch, error):
    import os
    out = tmp_path / "analysis"
    out.mkdir()
    data = out / "reads.txt"
    data.write_bytes(b"retained scientific reads")
    for name in ("first.txt", "second.txt"):
        (out / name).symlink_to(data)
    before = provenance.snapshot_inputs([out])
    original_replace = os.replace
    calls = 0

    def fail_second_replace(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise error("injected second publication replacement failure")
        return original_replace(*args, **kwargs)

    monkeypatch.setattr(os, "replace", fail_second_replace)
    with pytest.raises(NfclawError if error is OSError else KeyboardInterrupt):
        resume_safety.archive_previous_run(out, {}, [])
    assert provenance.snapshot_inputs([out]) == before
    assert not list(tmp_path.glob("analysis.previous-*"))


@pytest.mark.parametrize("where", ["original", "fresh"])
def test_cancellation_after_completed_rename_restores_original(tmp_path, monkeypatch, where):
    out = tmp_path / "analysis"
    out.mkdir()
    data = out / "reads.txt"
    data.write_bytes(b"recorded reads")
    (out / "published.txt").symlink_to(data)
    before = provenance.snapshot_inputs([out])
    rename = Path.rename
    injected = False

    def interrupted_rename(path, target):
        nonlocal injected
        result = rename(path, target)
        selected = path == out if where == "original" else path.name.startswith(".nfclaw-resume-")
        if selected and not injected:
            injected = True
            raise KeyboardInterrupt("cancellation after successful rename")
        return result

    monkeypatch.setattr(Path, "rename", interrupted_rename)
    with pytest.raises(KeyboardInterrupt):
        resume_safety.archive_previous_run(out, {}, [])
    assert provenance.snapshot_inputs([out]) == before
    assert not list(tmp_path.glob("analysis.previous-*"))
    assert not list(tmp_path.glob(".nfclaw-resume-*"))


@pytest.mark.parametrize("aliased", [False, True])
@pytest.mark.parametrize("directory", [False, True])
def test_archiving_preserves_links_through_internal_external_publications(
        tmp_path, aliased, directory):
    out = tmp_path / "analysis"
    out.mkdir()
    external = tmp_path / "work"
    external.mkdir()
    (external / "reads.txt").write_bytes(b"external scientific reads")
    alias = tmp_path / "alias"
    alias.symlink_to(out, target_is_directory=True)
    root = alias if aliased else out
    if directory:
        (out / "published").symlink_to(external, target_is_directory=True)
        (out / "indirect.txt").symlink_to(root / "published/reads.txt")
    else:
        (out / "published.txt").symlink_to(external / "reads.txt")
        (out / "indirect.txt").symlink_to(root / "published.txt")
    before = provenance.output_checksums(out)
    archive = resume_safety.archive_previous_run(out, {}, [])
    assert provenance.output_checksums(archive) == before
    assert (archive / "indirect.txt").read_bytes() == b"external scientific reads"


@pytest.mark.skipif(__import__("os").geteuid() == 0, reason="requires non-root permissions")
def test_unwritable_publication_directory_leaves_original_results_readable(tmp_path):
    out = tmp_path / "analysis"
    out.mkdir()
    data = out / "reads.txt"
    data.write_bytes(b"retained scientific reads")
    published = out / "published"
    published.mkdir()
    (published / "reads.txt").symlink_to(data)
    before = provenance.output_checksums(out)
    published.chmod(0o555)
    try:
        with pytest.raises(NfclawError, match="Could not preserve the previous run"):
            resume_safety.archive_previous_run(out, {}, [])
        assert provenance.output_checksums(out) == before
        assert not list(tmp_path.glob("analysis.previous-*"))
    finally:
        published.chmod(0o755)


@pytest.mark.parametrize("stop_signal", ["SIGTERM", "SIGHUP"])
def test_real_stop_signal_restores_the_original_archive_tree(tmp_path, stop_signal):
    import sys

    result = subprocess.run([sys.executable, "-c", r'''
import os, signal, sys
from pathlib import Path
from runner import execution, provenance, resume_safety
out = Path(sys.argv[1]) / "analysis"
out.mkdir()
data = out / "reads.txt"
data.write_bytes(b"retained reads")
for name in ("first.txt", "second.txt"):
    (out / name).symlink_to(data)
before = provenance.snapshot_inputs([out])
stop = getattr(signal, sys.argv[2])
signal.signal(stop, signal.SIG_DFL)
replace = os.replace
calls = 0
def interrupted_replace(*args, **kwargs):
    global calls
    calls += 1
    if calls == 2:
        os.kill(os.getpid(), stop)
    return replace(*args, **kwargs)
os.replace = interrupted_replace
try:
    resume_safety.archive_previous_run(out, {}, [])
except execution.Terminated as stopped:
    assert stopped.signum == stop
else:
    raise AssertionError("stop signal was ignored")
assert provenance.snapshot_inputs([out]) == before
assert not list(out.parent.glob("analysis.previous-*"))
assert not list(out.parent.glob(".nfclaw-resume-*"))
''', str(tmp_path), stop_signal], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
