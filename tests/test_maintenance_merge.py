"""Maintenance must satisfy CI on its validated commit before merging or deploying."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


def run_merge(tmp_path, **overrides):
    commands = tmp_path / "commands.jsonl"
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "gh").write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['COMMANDS'], 'a') as log:\n"
        "    log.write(json.dumps(args) + '\\n')\n"
        "if args[0] == 'api' and os.environ.get('FAIL_CHECK') in args:\n"
        "    sys.exit(1)\n"
        "if args[:2] == ['pr', 'merge'] and os.environ.get('FAIL_MERGE'):\n"
        "    calls = [json.loads(line) for line in open(os.environ['COMMANDS'])]\n"
        "    attempts = sum(call[:2] == ['pr', 'merge'] for call in calls)\n"
        "    if os.environ['FAIL_MERGE'] != 'transient' or attempts < 2:\n"
        "        sys.exit(1)\n"
    )
    (fake / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for path in fake.iterdir():
        path.chmod(0o755)
    env = {
        **os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
        "COMMANDS": str(commands), "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123",
        "PR_NUMBER": "42", "PR_HEAD_SHA": SHA, **overrides,
    }
    result = subprocess.run(["bash", str(ROOT / "scripts/merge_validated_update.sh")],
                            env=env, text=True, capture_output=True)
    calls = [json.loads(line) for line in commands.read_text().splitlines()] if commands.exists() else []
    return result, calls


def test_reports_checks_for_validated_commit_and_deploys_only_after_merge(tmp_path):
    result, calls = run_merge(tmp_path)
    assert result.returncode == 0, result.stderr
    checks = [call for call in calls if call[0] == "api"]
    assert len(checks) == 4
    assert all(f"head_sha={SHA}" in call and "conclusion=success" in call for call in checks)
    merge = next(call for call in calls if call[:2] == ["pr", "merge"])
    assert merge[merge.index("--match-head-commit") + 1] == SHA
    assert "--admin" not in merge
    assert "--auto" not in merge
    deploy = next(call for call in calls if call[:2] == ["workflow", "run"])
    assert calls.index(merge) < calls.index(deploy)


@pytest.mark.parametrize("failure", [{"FAIL_CHECK": "name=website"}, {"FAIL_MERGE": "1"}])
def test_publication_or_merge_failure_prevents_deployment(tmp_path, failure):
    result, calls = run_merge(tmp_path, **failure)
    assert calls, result.stderr
    assert result.returncode != 0
    assert not any(call[:2] == ["workflow", "run"] for call in calls)
    if "FAIL_CHECK" in failure:
        assert not any(call[:2] == ["pr", "merge"] for call in calls)


def test_retries_a_short_check_evaluation_delay_without_queuing_a_late_merge(tmp_path):
    result, calls = run_merge(tmp_path, FAIL_MERGE="transient")
    assert result.returncode == 0, result.stderr
    merges = [call for call in calls if call[:2] == ["pr", "merge"]]
    assert len(merges) == 2
    assert all("--auto" not in call for call in merges)
    assert calls[-1][:2] == ["workflow", "run"]
