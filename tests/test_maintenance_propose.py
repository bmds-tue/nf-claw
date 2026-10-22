"""A maintenance update the organization will not let Actions propose is reported, not lost."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
BASE = "b" * 40
REFUSED = ("pull request create failed: GraphQL: GitHub Actions is not permitted to create or "
           "approve pull requests (createPullRequest)\n")


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def run_propose(tmp_path, *, tip=None, parent=BASE, parents=1, create="refused"):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
         "-m", "update")
    _git(repo, "branch", "-f", "auto-update-pipelines")
    local = _git(repo, "rev-parse", "auto-update-pipelines")
    commands, output, summary = (tmp_path / name for name in ("calls.jsonl", "out", "summary"))
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "gh").write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['COMMANDS'], 'a') as log:\n"
        "    log.write(json.dumps(args) + '\\n')\n"
        "if args[0] == 'api':\n"
        "    print('\\t'.join([os.environ['TIP'], os.environ['PARENT'], os.environ['PARENTS']]))\n"
        "elif args[:2] == ['pr', 'create']:\n"
        "    if os.environ['CREATE'] == 'opened':\n"
        "        print('https://github.com/owner/repo/pull/77')\n"
        "    else:\n"
        "        sys.stderr.write(os.environ['CREATE_ERR'])\n"
        "        sys.exit(1)\n"
    )
    (fake / "gh").chmod(0o755)
    env = {
        **os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
        "COMMANDS": str(commands), "TIP": tip or local, "PARENT": parent,
        "PARENTS": str(parents), "CREATE": create,
        "CREATE_ERR": REFUSED if create == "refused" else "HTTP 502: Bad Gateway\n",
        "BRANCH": "auto-update-pipelines", "TITLE": "chore: update", "BODY": "Automated.",
        "GITHUB_REPOSITORY": "owner/repo", "GITHUB_SHA": BASE,
        "GITHUB_SERVER_URL": "https://github.com", "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary), "RUNNER_TEMP": str(tmp_path),
    }
    result = subprocess.run(["bash", str(ROOT / "scripts/propose_validated_update.sh")],
                            cwd=repo, env=env, text=True, capture_output=True)
    calls = [json.loads(line) for line in commands.read_text().splitlines()] if commands.exists() else []
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
    return result, calls, outputs, summary.read_text() if summary.exists() else "", local


def test_an_organization_refusal_reports_the_validated_branch_without_failing(tmp_path):
    result, calls, outputs, summary, local = run_propose(tmp_path)
    assert result.returncode == 0, result.stderr
    assert any(call[:2] == ["pr", "create"] for call in calls)
    assert outputs == {}                                  # nothing for the merge step to merge
    assert "::warning title=Validated update awaits a pull request::" in result.stdout
    assert local in summary
    assert "https://github.com/owner/repo/compare/main...auto-update-pipelines?expand=1" in summary


def test_a_pull_request_opened_on_retry_is_handed_to_the_merge_step(tmp_path):
    result, _, outputs, summary, local = run_propose(tmp_path, create="opened")
    assert result.returncode == 0, result.stderr
    assert outputs == {"number": "77", "head_sha": local}
    assert summary == ""


def test_any_other_pull_request_failure_fails_the_job(tmp_path):
    result, _, outputs, _, _ = run_propose(tmp_path, create="error")
    assert result.returncode != 0
    assert "Bad Gateway" in result.stderr
    assert outputs == {}


@pytest.mark.parametrize("branch", [{"tip": "c" * 40},                # not what this job pushed
                                    {"parent": "d" * 40},             # not on the validated commit
                                    {"parents": 2}])                  # a merge, not one update commit
def test_a_branch_without_this_runs_update_is_never_proposed(tmp_path, branch):
    result, calls, outputs, summary, _ = run_propose(tmp_path, **branch)
    assert result.returncode != 0
    assert "does not hold this run's validated update" in result.stdout
    assert not any(call[:2] == ["pr", "create"] for call in calls)
    assert outputs == {} and summary == ""


@pytest.mark.parametrize("name, branch", [("auto-update.yml", "auto-update-pipelines"),
                                          ("discover-pipelines.yml", "auto-discover-pipelines")])
def test_bots_propose_a_refused_branch_and_merge_only_an_opened_pull_request(name, branch):
    text = (WF / name).read_text(encoding="utf-8")
    cpr = text.split("peter-evans/create-pull-request@", 1)[1].split("\n      - ", 1)[0]
    assert "continue-on-error: true" in cpr
    assert re.search(rf"^\s+branch: {branch}$", cpr, re.M)
    propose = text.split("- name: Propose the validated branch\n", 1)[1].split("\n      - ", 1)[0]
    assert "steps.cpr.outcome == 'failure'" in propose
    assert f"BRANCH: {branch}\n" in propose
    assert "run: bash scripts/propose_validated_update.sh" in propose
    merge = text.split("- name: Auto-merge and redeploy\n", 1)[1]
    assert "steps.cpr.outputs.pull-request-number || steps.propose.outputs.number" in merge
    assert ("steps.cpr.outputs.pull-request-head-sha || steps.propose.outputs.head_sha"
            in merge)
