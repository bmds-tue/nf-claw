import json
import os
from datetime import UTC, datetime
from types import SimpleNamespace

from runner import job_retention, jobs


def _job(tmp_path, monkeypatch, number=1, *, outdir=None):
    monkeypatch.setenv("NFCLAW_STATE_DIR", str(tmp_path / "state"))
    jid = f"20260101T00000{number}-demo-abcdef"
    directory = jobs.jobs_dir() / jid
    directory.mkdir(parents=True)
    job = jobs.Job(id=jid, kind="run", argv=[], command=[], cwd=str(tmp_path),
                   outdir=str(outdir or tmp_path / f"results-{number}"),
                   created_at="2026-01-01T00:00:00+00:00", dir=directory)
    (directory / jobs.JOB_FILE).write_text(json.dumps(job.spec()))
    (directory / jobs.SUPERVISOR_FILE).write_text(json.dumps(
        {"exit_code": 0, "finished_at": "2026-01-01T00:10:00+00:00"}))
    (directory / jobs.OUTPUT_LOG).write_text("old console output\n")
    (directory / jobs.LOCK_FILE).touch()
    return job


def _prune(**kwargs):
    return job_retention.prune(older_than_days=30, keep=0,
                              now=datetime(2026, 10, 25, tzinfo=UTC), **kwargs)


def test_pruning_previews_then_removes_only_known_metadata(tmp_path, monkeypatch):
    job = _job(tmp_path, monkeypatch)
    result = job.dir / "scientific-result.txt"
    result.write_text("retain me\n")
    spec = job.dir / "spec.json"
    spec.write_text("retain replay specification\n")
    assert _prune()["candidates"][0]["job_id"] == job.id
    assert (job.dir / jobs.JOB_FILE).exists()
    report = _prune(apply=True)
    assert report["removed"] == [job.id]
    assert not (job.dir / jobs.JOB_FILE).exists()
    assert result.read_text() == "retain me\n"
    assert spec.read_text() == "retain replay specification\n"


def test_active_supervisor_is_protected_by_the_real_job_lock(tmp_path, monkeypatch):
    job = _job(tmp_path, monkeypatch)
    fd = os.open(job.dir / jobs.LOCK_FILE, os.O_RDWR)
    try:
        jobs.fcntl.flock(fd, jobs.fcntl.LOCK_EX | jobs.fcntl.LOCK_NB)
        assert _prune(apply=True)["removed"] == []
        assert (job.dir / jobs.JOB_FILE).exists()
    finally:
        os.close(fd)


def test_job_metadata_used_as_another_runs_input_is_protected(tmp_path, monkeypatch):
    producer = _job(tmp_path, monkeypatch)
    consumer = _job(tmp_path, monkeypatch, 2)
    prov = tmp_path / "results-2/provenance"
    prov.mkdir(parents=True)
    (prov / "inputs.inventory.json").write_text(json.dumps(
        {str(producer.dir / jobs.OUTPUT_LOG): {"type": "file"}}))
    report = _prune(apply=True)
    assert producer.id not in report["removed"]
    assert (producer.dir / jobs.OUTPUT_LOG).is_file()
    assert consumer.id in report["removed"]


def test_scientific_outputs_inside_metadata_directory_are_protected(tmp_path, monkeypatch):
    job = _job(tmp_path, monkeypatch)
    spec = job.spec()
    spec["outdir"] = str(job.dir / "scientific-results")
    (job.dir / jobs.JOB_FILE).write_text(json.dumps(spec))
    assert _prune(apply=True)["removed"] == []


def test_listing_loads_only_one_page_and_cursor_continues_without_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_STATE_DIR", str(tmp_path / "state"))
    jobs.jobs_dir().mkdir(parents=True)
    names = [f"20260101T000000-demo-{n:06x}" for n in range(100)]
    for name in names:
        (jobs.jobs_dir() / name).mkdir()
    calls = []

    def load(name):
        calls.append(name)
        return SimpleNamespace(id=name)

    monkeypatch.setattr(jobs, "load", load)
    first = jobs.list_jobs(limit=3)
    assert len(calls) == 3
    second = jobs.list_jobs(limit=3, before=first[-1].id)
    assert len(calls) == 6
    assert [j.id for j in first + second] == sorted(names, reverse=True)[:6]


def test_malformed_job_records_are_not_listed_or_pruned(tmp_path, monkeypatch):
    job = _job(tmp_path, monkeypatch)
    (job.dir / jobs.JOB_FILE).write_text('{"outdir": null}')
    assert jobs.list_jobs(limit=5) == []
    assert _prune(apply=True)["removed"] == []
    assert (job.dir / jobs.JOB_FILE).is_file()
