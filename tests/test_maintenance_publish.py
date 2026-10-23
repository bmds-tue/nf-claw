"""Maintenance publishes through the permitted Git path, without creating a PR."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/publish_validated_update.sh"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def publication(tmp_path):
    repo, remote, fake = (tmp_path / name for name in ("repo", "origin.git", "bin"))
    repo.mkdir()
    fake.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.com")
    for name in ("catalog.json", "catalog.md", "sources.tsv", ".gitmodules", "README.md",
                 "pipelines/mini/skill.md"):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n" if name != ".gitmodules" else "")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    git(tmp_path, "clone", "-q", "--bare", str(repo), str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    calls, outputs, summary = (tmp_path / name for name in ("calls", "out", "summary"))
    # Only the external GitHub API is substituted. Commits, trees, gitlinks, pushes,
    # fast-forward checks and reference updates all use real Git repositories.
    (fake / "gh").write_text(f"#!{sys.executable}\n" + r'''
import json, os, subprocess, sys
args = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as log:
    log.write(json.dumps(args) + '\n')
def git(*values):
    return subprocess.check_output(['git', '--git-dir', os.environ['REMOTE'], *values],
                                   text=True).strip()
def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)
if args[:2] == ['workflow', 'run']:
    if args[2] == os.environ.get('FAIL_WORKFLOW'):
        fail('workflow dispatch failed')
elif args[0] == 'api':
    method = args[args.index('--method') + 1] if '--method' in args else 'GET'
    endpoint = next(arg for arg in args if arg.startswith('repos/'))
    if method == 'GET' and '/commits/' in endpoint:
        sha = git('rev-parse', 'refs/heads/' + endpoint.rsplit('/', 1)[1])
        parents = git('show', '-s', '--format=%P', sha).split()
        print('\t'.join([sha, parents[0], str(len(parents))]))
    elif method == 'POST' and endpoint.endswith('/check-runs'):
        if os.environ.get('FAIL_CHECK') in args:
            fail('could not report validation')
    elif method == 'PATCH' and endpoint.endswith('/git/refs/heads/main'):
        attempts = sum('PATCH' in json.loads(line) for line in open(os.environ['CALLS']))
        if os.environ.get('PATCH_ERROR') == 'rule' or (
                os.environ.get('PATCH_ERROR') == 'transient' and attempts == 1):
            fail('gh: Repository rule violations found (HTTP 422)')
        sha = next(arg[4:] for arg in args if arg.startswith('sha='))
        current = git('rev-parse', 'refs/heads/main')
        result = subprocess.run(['git', '--git-dir', os.environ['REMOTE'],
                                 'merge-base', '--is-ancestor', current, sha])
        if result.returncode:
            fail('gh: Update is not a fast forward (HTTP 422)')
        assert 'force=false' in args
        git('update-ref', 'refs/heads/main', sha, current)
    elif method == 'DELETE' and '/git/refs/heads/' in endpoint:
        git('update-ref', '-d', 'refs/heads/' + endpoint.split('/git/refs/heads/', 1)[1])
    else:
        fail('unexpected API request: ' + repr(args))
else:
    fail('unexpected GitHub command (PRs are forbidden): ' + repr(args))
''')
    (fake / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for path in fake.iterdir():
        path.chmod(0o755)

    def run(kind="update", *, workflow=None, **overrides):
        command = ["bash", str(SCRIPT)]
        if workflow:
            import yaml
            definition = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())
            job = next(iter(definition["jobs"].values()))
            step = job["steps"][-1]
            kind = step["env"]["UPDATE_KIND"]
            assert step["env"]["BASE_SHA"] == "${{ steps.base.outputs.sha }}"
            command = ["bash", str(ROOT / step["run"].split()[1])]
        env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
               "CALLS": str(calls), "REMOTE": str(remote), "BASE_SHA": base,
               "UPDATE_KIND": kind, "GITHUB_REPOSITORY": "owner/repo",
               "GITHUB_SHA": "e" * 40, "GITHUB_SERVER_URL": "https://github.com",
               "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
               "GITHUB_OUTPUT": str(outputs), "GITHUB_STEP_SUMMARY": str(summary),
               "RUNNER_TEMP": str(tmp_path), **overrides}
        result = subprocess.run(command, cwd=repo, env=env, text=True, capture_output=True)
        requests = [json.loads(line) for line in calls.read_text().splitlines()] \
            if calls.exists() else []
        values = dict(line.split("=", 1) for line in outputs.read_text().splitlines()) \
            if outputs.exists() else {}
        return result, requests, values

    return repo, remote, base, run


@pytest.mark.parametrize("workflow", ["auto-update.yml", "discover-pipelines.yml"])
def test_both_workflows_publish_generated_changes_and_start_push_workflows(publication, workflow):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    (repo / "unrelated-build-output").write_text("do not publish\n")
    (repo / "sources.tsv").write_text("updated inventory\n")
    if workflow == "auto-update.yml":
        (repo / "sources.tsv").write_text("original\n")
    result, calls, outputs = run(workflow=workflow)
    assert result.returncode == 0, result.stdout + result.stderr
    head = git(remote, "rev-parse", "main")
    assert head != base and git(remote, "rev-parse", "main^") == base
    assert git(remote, "show", "main:catalog.md") == "regenerated"
    assert "unrelated-build-output" not in git(remote, "ls-tree", "-r", "--name-only", "main")
    assert git(repo, "rev-parse", "HEAD") == base   # publication never rewrites the checkout
    assert outputs["published"] == "true"
    checks = [call for call in calls if "POST" in call]
    assert {next(arg for arg in call if arg.startswith("name=")) for call in checks} == {
        "name=pytest (ubuntu-latest, 3.11)", "name=website",
        "name=nextflow-integration", "name=drift"}
    assert all(f"head_sha={head}" in call and "conclusion=success" in call for call in checks)
    patch = next(call for call in calls if "PATCH" in call)
    assert all(calls.index(check) < calls.index(patch) for check in checks)
    dispatches = [call for call in calls if call[:2] == ["workflow", "run"]]
    assert {call[2] for call in dispatches} == {
        "tests.yml", "smoke.yml", "codeql.yml", "deploy-pages.yml"}
    assert all(calls.index(patch) < calls.index(call) and call[-2:] == ["--ref", "main"]
               for call in dispatches)
    assert not git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/maintenance-*")
    if workflow == "discover-pipelines.yml":
        assert git(remote, "show", "main:sources.tsv") == "updated inventory"


def test_no_changes_does_not_commit_or_call_github(publication):
    repo, remote, base, run = publication
    result, calls, outputs = run()
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") == base
    assert git(repo, "rev-parse", "HEAD") == base
    assert calls == [] and outputs["published"] == "false"


@pytest.mark.parametrize("failure", [{"FAIL_CHECK": "name=website"}, {"PATCH_ERROR": "rule"}])
def test_check_or_rule_failure_never_publishes_or_deploys(publication, failure):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, _ = run(**failure)
    assert result.returncode != 0
    assert git(remote, "rev-parse", "main") == base
    assert not any(call[:2] == ["workflow", "run"] for call in calls)
    if "FAIL_CHECK" in failure:
        assert not any("PATCH" in call for call in calls)


def test_a_concurrent_main_update_is_preserved_for_the_next_scheduled_run(publication):
    repo, remote, _, run = publication
    (repo / "README.md").write_text("human change\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "human commit")
    human = git(repo, "rev-parse", "HEAD")
    git(repo, "push", "-q", "origin", "main")
    git(repo, "reset", "--hard", "HEAD^")
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, outputs = run()
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") == human
    assert outputs["published"] == "false"
    assert len([call for call in calls if "PATCH" in call]) == 1
    assert not any(call[:2] == ["workflow", "run"] for call in calls)
    # The next run regenerates the update on the new main; no candidate branch is left behind.
    assert not git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/maintenance-*")


def test_a_short_check_evaluation_delay_is_retried(publication):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, outputs = run(PATCH_ERROR="transient")
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") != base
    assert len([call for call in calls if "PATCH" in call]) == 2
    assert outputs["published"] == "true"


def test_a_failed_dispatch_is_reported_after_a_successful_publication(publication):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, _ = run(FAIL_WORKFLOW="tests.yml")
    assert result.returncode != 0
    assert git(remote, "rev-parse", "main") != base
    # One failed dispatch must not prevent the other push workflows from starting.
    assert {call[2] for call in calls if call[:2] == ["workflow", "run"]} == {
        "tests.yml", "smoke.yml", "codeql.yml", "deploy-pages.yml"}


@pytest.mark.parametrize("overrides", [{"BASE_SHA": "f" * 40}, {"UPDATE_KIND": "other"},
                                     {"GITHUB_RUN_ID": "../bad"}])
def test_invalid_or_stale_validation_identity_never_reaches_github(publication, overrides):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, _ = run(**overrides)
    assert result.returncode != 0
    assert calls == [] and git(remote, "rev-parse", "main") == base


def test_discovery_keeps_new_gitlinks_docs_and_every_generated_manifest(publication, tmp_path):
    repo, remote, _, run = publication
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "-q")
    git(upstream, "-c", "user.name=test", "-c", "user.email=test@example.com",
        "commit", "-qm", "release", "--allow-empty")
    pinned = git(upstream, "rev-parse", "HEAD")
    git(repo, "-c", "protocol.file.allow=always", "submodule", "add", str(upstream),
        "pipelines/new/upstream")
    (repo / "pipelines/new/skill.md").write_text("generated skill\n")
    (repo / "sources.tsv").write_text("new pipeline\n")
    staged = git(repo, "diff", "--cached", "--raw")
    result, _, _ = run(kind="discover")
    assert result.returncode == 0, result.stderr
    gitlink = git(remote, "ls-tree", "main", "pipelines/new/upstream")
    assert gitlink.startswith(f"160000 commit {pinned}")
    assert git(remote, "show", "main:pipelines/new/skill.md") == "generated skill"
    assert git(remote, "show", "main:sources.tsv") == "new pipeline"
    assert "pipelines/new/upstream" in git(remote, "show", "main:.gitmodules")
    assert git(repo, "diff", "--cached", "--raw") == staged


def test_a_rerun_uses_a_new_candidate_branch_and_removes_the_superseded_attempt(publication):
    repo, remote, _, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    first, _, _ = run(PATCH_ERROR="rule")
    assert first.returncode != 0
    previous = git(remote, "rev-parse", "maintenance-update-123-1")   # kept for inspection
    git(remote, "branch", "maintenance-update-1234-1", previous)      # another run's candidate
    second, calls, outputs = run(GITHUB_RUN_ATTEMPT="3")              # attempt 2 never pushed
    assert second.returncode == 0, second.stderr
    assert outputs["published"] == "true"
    deleted = [next(arg for arg in call if arg.startswith("repos/")).rsplit("/", 1)[1]
               for call in calls if "DELETE" in call]
    assert deleted == ["maintenance-update-123-3", "maintenance-update-123-1",
                       "maintenance-update-123-2"]
    assert git(remote, "for-each-ref", "--format=%(refname:short)",
               "refs/heads/maintenance-*") == "maintenance-update-1234-1"


def test_unexpected_tracked_code_changes_cannot_authorize_generated_data(publication):
    repo, remote, base, run = publication
    (repo / "README.md").write_text("unexpected tracked change during validation\n")
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, _ = run()
    assert result.returncode != 0
    assert calls == [] and git(remote, "rev-parse", "main") == base
