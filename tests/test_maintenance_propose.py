"""A maintenance update the organization will not let Actions propose is published, not lost."""
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
FFWD_ERRORS = {"not-ff": "gh: Update is not a fast forward (HTTP 422)\n",
               "rule": "gh: Repository rule violations found\n\nChanges must be made through a "
                       "pull request. (HTTP 422)\n"}


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def run_propose(tmp_path, *, tip=None, parent=BASE, parents=1, create="refused", ffwd="ok",
                **env_overrides):
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
        "if args[0] == 'api' and '--method' not in args:\n"
        "    print('\\t'.join([os.environ['TIP'], os.environ['PARENT'], os.environ['PARENTS']]))\n"
        "elif args[0] == 'api' and 'PATCH' in args and os.environ['FFWD'] != 'ok':\n"
        "    sys.stderr.write(os.environ['FFWD_ERR'])\n"
        "    sys.exit(1)\n"
        "elif args[:2] == ['pr', 'create']:\n"
        "    if os.environ['CREATE'] == 'opened':\n"
        "        print('https://github.com/owner/repo/pull/77')\n"
        "    else:\n"
        "        sys.stderr.write(os.environ['CREATE_ERR'])\n"
        "        sys.exit(1)\n"
    )
    (fake / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for path in fake.iterdir():
        path.chmod(0o755)
    env = {
        **os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
        "COMMANDS": str(commands), "TIP": tip or local, "PARENT": parent,
        "PARENTS": str(parents), "CREATE": create, "FFWD": ffwd,
        "FFWD_ERR": FFWD_ERRORS.get(ffwd, ""),
        "CREATE_ERR": REFUSED if create == "refused" else "HTTP 502: Bad Gateway\n",
        "BRANCH": "auto-update-pipelines", "TITLE": "chore: update", "BODY": "Automated.",
        "GITHUB_REPOSITORY": "owner/repo", "GITHUB_SHA": BASE, "GITHUB_RUN_ID": "123",
        "GITHUB_SERVER_URL": "https://github.com", "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary), "RUNNER_TEMP": str(tmp_path), **env_overrides,
    }
    if "BASE_SHA" not in env_overrides:                 # the script falls back to GITHUB_SHA
        env.pop("BASE_SHA", None)
    result = subprocess.run(["bash", str(ROOT / "scripts/propose_validated_update.sh")],
                            cwd=repo, env=env, text=True, capture_output=True)
    calls = [json.loads(line) for line in commands.read_text().splitlines()] if commands.exists() else []
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
    return result, calls, outputs, summary.read_text() if summary.exists() else "", local


def _patches(calls):
    return [call for call in calls if call[0] == "api" and "PATCH" in call]


def test_an_organization_refusal_publishes_the_validated_commit_to_main(tmp_path):
    result, calls, outputs, summary, local = run_propose(tmp_path)
    assert result.returncode == 0, result.stderr
    assert any(call[:2] == ["pr", "create"] for call in calls)
    assert outputs == {}                                  # nothing for the merge step to merge
    checks = [call for call in calls if call[0] == "api" and "POST" in call]
    assert len(checks) == 4
    assert all(f"head_sha={local}" in call and "conclusion=success" in call for call in checks)
    patch, = _patches(calls)
    assert "repos/owner/repo/git/refs/heads/main" in patch
    assert f"sha={local}" in patch and "force=false" in patch      # a fast-forward, never forced
    assert max(calls.index(c) for c in checks) < calls.index(patch)  # checks reported first
    deletion = next(call for call in calls if call[0] == "api" and "DELETE" in call)
    assert "repos/owner/repo/git/refs/heads/auto-update-pipelines" in deletion
    dispatched = [call[2] for call in calls if call[:2] == ["workflow", "run"]]
    assert dispatched == ["deploy-pages.yml", "tests.yml"]
    assert calls.index(patch) < min(i for i, c in enumerate(calls) if c[:2] == ["workflow", "run"])
    assert "::notice title=Validated update published::" in result.stdout
    assert local in summary and "fast-forwarded" in summary


@pytest.mark.parametrize("ffwd, attempts", [("not-ff", 1),     # main moved on: no retry helps
                                            ("rule", 5)])      # e.g. checks not yet evaluated
def test_a_main_that_refuses_the_fast_forward_leaves_the_branch_for_a_maintainer(
        tmp_path, ffwd, attempts):
    result, calls, outputs, summary, local = run_propose(tmp_path, ffwd=ffwd)
    assert result.returncode == 0, result.stderr
    assert len(_patches(calls)) == attempts
    assert not any(call[0] == "api" and "DELETE" in call for call in calls)
    assert not any(call[:2] == ["workflow", "run"] for call in calls)
    assert outputs == {}
    assert "::warning title=Validated update awaits a pull request::" in result.stdout
    assert local in summary
    assert "https://github.com/owner/repo/compare/main...auto-update-pipelines?expand=1" in summary


def test_a_pull_request_opened_on_retry_is_handed_to_the_merge_step(tmp_path):
    result, calls, outputs, summary, local = run_propose(tmp_path, create="opened")
    assert result.returncode == 0, result.stderr
    assert outputs == {"number": "77", "head_sha": local}
    assert not _patches(calls)
    assert summary == ""


def test_any_other_pull_request_failure_fails_the_job(tmp_path):
    result, calls, outputs, _, _ = run_propose(tmp_path, create="error")
    assert result.returncode != 0
    assert "Bad Gateway" in result.stderr
    assert outputs == {}
    assert not _patches(calls)


def test_the_validated_base_is_the_commit_the_job_checked_out(tmp_path):
    # A queued run checks out main as it is when it starts, not its stale event commit.
    result, calls, _, _, _ = run_propose(tmp_path, parent="e" * 40, BASE_SHA="e" * 40)
    assert result.returncode == 0, result.stderr
    assert _patches(calls)


@pytest.mark.parametrize("branch", [{"tip": "c" * 40},                # not what this job pushed
                                    {"parent": "d" * 40},             # not on the validated commit
                                    {"parents": 2},                   # a merge, not one update commit
                                    {"BASE_SHA": "e" * 40}])          # validated another base
def test_a_branch_without_this_runs_update_is_never_proposed(tmp_path, branch):
    result, calls, outputs, summary, _ = run_propose(tmp_path, **branch)
    assert result.returncode != 0
    assert "does not hold this run's validated update" in result.stdout
    assert not any(call[:2] == ["pr", "create"] for call in calls)
    assert not _patches(calls)
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
    assert "BASE_SHA: ${{ steps.base.outputs.sha }}" in propose
    assert "run: bash scripts/propose_validated_update.sh" in propose
    merge = text.split("- name: Auto-merge and redeploy\n", 1)[1]
    assert "steps.cpr.outputs.pull-request-number || steps.propose.outputs.number" in merge
    assert ("steps.cpr.outputs.pull-request-head-sha || steps.propose.outputs.head_sha"
            in merge)


@pytest.mark.parametrize("name", ["auto-update.yml", "discover-pipelines.yml"])
def test_bots_publish_one_at_a_time_from_main_as_it_is_when_they_start(name):
    text = (WF / name).read_text(encoding="utf-8")
    assert re.search(r"^concurrency:\n  group: nfclaw-maintenance\n  cancel-in-progress: false$",
                     text, re.M)
    checkout = text.split("uses: actions/checkout@", 1)[1].split("\n      - ", 1)[0]
    assert re.search(r"^\s+ref: main$", checkout, re.M)
    base = text.split("- name: Record the validated base\n", 1)[1].split("\n      - ", 1)[0]
    assert "id: base" in base and "git rev-parse HEAD" in base
    assert text.index("Record the validated base") < text.index("Fetch submodule tags")
