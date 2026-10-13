import json

import pytest

from runner import dependency_stability, replay_guard


def capture(tmp_path):
    data = tmp_path / "data"
    (data / "empty").mkdir(parents=True)
    (data / "reads.fastq").write_bytes(b"original reads")
    config = tmp_path / "extra.config"
    config.write_text("params.x = 1\n")
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    (pipeline / "main.nf").write_text("workflow {}\n")
    ih, inv = replay_guard.snapshot_inputs([data])
    ch, cinv = replay_guard.snapshot_inputs([config])
    return dict(inputs=[data], input_checksums=ih, input_inventory=inv,
                configs=(config,), config_checksums=ch, config_inventory=cinv,
                pipeline=pipeline, pipeline_checksums=replay_guard.hash_pipeline(pipeline),
                git_head=None)


def test_unchanged_dependencies_are_verified(tmp_path):
    result = dependency_stability.compare(**capture(tmp_path))
    assert result["status"] == "unchanged" and result["issues"] == []


@pytest.mark.parametrize("kind", ["bytes", "namespace", "config", "source", "missing"])
def test_detects_dependency_changes_without_replacing_launch_snapshots(tmp_path, kind):
    options = capture(tmp_path)
    original = dict(options["input_checksums"])
    if kind == "bytes":
        (options["inputs"][0] / "reads.fastq").write_bytes(b"modified reads")
    elif kind == "namespace":
        (options["inputs"][0] / "empty").rename(options["inputs"][0] / "renamed")
    elif kind == "config":
        options["configs"][0].write_text("params.x = 2\n")
    elif kind == "source":
        (options["pipeline"] / "main.nf").write_text("workflow { println 'changed' }\n")
    else:
        (options["inputs"][0] / "reads.fastq").unlink()
    result = dependency_stability.compare(**options)
    assert result["status"] == "changed" and result["issues"]
    assert options["input_checksums"] == original
    expected = {"bytes": "inputs", "namespace": "inputs", "missing": "inputs",
                "config": "configs", "source": "pipeline"}[kind]
    assert any(issue["kind"] == expected for issue in result["issues"])


def test_unreadable_snapshot_is_recorded_as_unverified_attribution(tmp_path, monkeypatch):
    options = capture(tmp_path)
    def denied(paths):
        raise PermissionError("input no longer readable")
    monkeypatch.setattr(dependency_stability, "snapshot_inputs", denied)
    result = dependency_stability.compare(**options)
    assert result["status"] == "changed"
    assert all(issue["change"] == "unreadable" for issue in result["issues"])


def test_git_revision_change_is_detected_even_when_tracked_bytes_match(tmp_path):
    import subprocess
    options = capture(tmp_path)
    repo = options["pipeline"]
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args]).strip().decode()
    git("init", "-q")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "add", "main.nf")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "original")
    options["git_head"] = git("rev-parse", "HEAD")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "changed revision")
    result = dependency_stability.compare(**options)
    assert result["status"] == "changed"
    assert [issue["change"] for issue in result["issues"]] == ["revision"]


def test_tainted_run_cannot_be_replayed_after_restoring_dependencies(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "run_manifest.json").write_text(json.dumps({"outcome": "failed",
        "dependency_stability": {"version": 1, "status": "changed", "issues": []}}))
    with pytest.raises(ValueError, match="original run"):
        replay_guard.verify_dependencies(bundle)


def test_tainted_log_forces_fresh_resume_even_without_local_inputs_or_provenance(tmp_path):
    from runner import orchestration, runlog
    log = runlog.RunLog.open(tmp_path / "provenance/logs", command=["nextflow"], launch_dir=tmp_path)
    log.fail(dependency_stability.FAILED_OUTCOME, "local source changed")
    log.finish()
    assert "previous execution" in orchestration._input_resume_warning(tmp_path, {}, {})
