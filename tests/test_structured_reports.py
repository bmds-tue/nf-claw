import json

from runner import cli, reports


def test_trace_progress_counts_observations_without_inventing_an_eventual_total(tmp_path):
    info = tmp_path / "pipeline_info"
    info.mkdir()
    (info / "execution_trace.txt").write_text(
        "task_id\tstatus\tname\n1\tCOMPLETED\tA\n2\tCACHED\tB\n")
    progress = reports.task_progress(tmp_path)
    assert progress["observed_tasks"] == 2
    assert progress["counts"] == {"COMPLETED": 1, "CACHED": 1}
    assert progress["expected_tasks"] is None
    assert reports.task_progress(tmp_path / "absent")["observed_tasks"] is None


def test_verification_json_preserves_historical_strict_compatibility(tmp_path, capsys):
    original, replay = tmp_path / "original", tmp_path / "replay"
    for path in (original, replay):
        path.mkdir()
        (path / "result.txt").write_text("identical\n")
    code = cli.main(["verify", str(replay), "--against", str(original), "--strict", "--json"])
    report = json.loads(capsys.readouterr().out)
    assert code == 0 and report["schema_version"] == 1
    assert report["passed"] is True and report["comparison"]["environment"] is None
    (replay / "result.txt").write_text("changed\n")
    assert cli.main(["verify", str(replay), "--against", str(original), "--strict", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["comparison"]["changed"] == ["result.txt"]
