"""Maintenance publishes through the permitted Git path, without creating a PR."""
import json
import hashlib
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/publish_validated_update.sh"
CANDIDATE = ROOT / "scripts/maintenance_candidate.py"


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
    upstream = repo / 'pipelines/mini/upstream'
    upstream.mkdir()
    git(upstream, 'init', '-q')
    git(upstream, '-c', 'user.name=test', '-c', 'user.email=test@example.com',
        'commit', '--allow-empty', '-qm', 'old release')
    (repo / '.gitmodules').write_text('[submodule "pipelines/mini/upstream"]\n'
        'path = pipelines/mini/upstream\nurl = https://github.com/nf-core/mini.git\n')
    (repo / 'sources.tsv').write_text('mini\thttps://github.com/nf-core/mini.git\tlatest-release\n')
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
    elif method == 'GET' and endpoint.endswith('/git/ref/heads/main'):
        current = git('rev-parse', 'refs/heads/main')
        if os.environ.get('MOVE_MAIN_AFTER_READ') and current == os.environ['BASE_SHA']:
            git('update-ref', 'refs/heads/main', os.environ['CANDIDATE_SHA'], current)
        print(current)
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
    # The main-ref update is real Git: this hook substitutes only remote rule evaluation.
    (remote / 'hooks/pre-receive').write_text(f"#!{sys.executable}\n" + r'''
import json, os, pathlib, sys
if 'CALLS' not in os.environ:
    sys.exit(0)
for line in sys.stdin:
    old, new, ref = line.split()
    if ref != 'refs/heads/main':
        continue
    with open(os.environ['CALLS'], 'a') as log:
        log.write(json.dumps(['git-push', ref, old, new]) + '\n')
    marker = pathlib.Path(os.environ['RUNNER_TEMP']) / 'main-push-attempted'
    fail = os.environ.get('PATCH_ERROR') == 'rule' or (
        os.environ.get('PATCH_ERROR') == 'transient' and not marker.exists())
    marker.touch()
    if fail:
        print('Repository rule evaluation has not accepted this update', file=sys.stderr)
        sys.exit(1)
''')
    (remote / 'hooks/pre-receive').chmod(0o755)
    (fake / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for path in fake.iterdir():
        path.chmod(0o755)

    def run(kind="update", *, workflow=None, native_artifact="valid",
            matrix_artifact="valid", reuse_candidate=False, **overrides):
        command = ["bash", str(SCRIPT)]
        if workflow:
            import yaml
            definition = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())
            job = definition["jobs"]["publish"]
            step = job["steps"][-1]
            kind = step["env"]["UPDATE_KIND"]
            assert step["env"]["BASE_SHA"] == "${{ needs.prepare.outputs.base }}"
            command = ["bash", str(ROOT / step["run"].split()[1])]
        if reuse_candidate:
            directory = run.last_directory
        else:
            directory = tmp_path / ('candidate-' + uuid.uuid4().hex)
            prepared = subprocess.run([sys.executable, str(CANDIDATE), 'prepare', '--directory',
                                       str(directory), '--base', base, '--kind', kind], cwd=repo,
                                      env={k: v for k, v in os.environ.items()
                                           if k != 'GITHUB_OUTPUT'},
                                      text=True, capture_output=True)
            if prepared.returncode:
                return prepared, [], {}
            run.last_directory = directory
        metadata = json.loads((directory / 'candidate.json').read_text())
        native = tmp_path / ('native-' + uuid.uuid4().hex)
        if native_artifact != 'missing':
            for name, pin in metadata['pipelines'].items():
                manifest = native / name / 'provenance/run_manifest.json'
                trace = native / name / 'pipeline_info/execution_trace.txt'
                manifest.parent.mkdir(parents=True)
                trace.parent.mkdir(parents=True)
                value = {'pipeline': name, 'commit': pin, 'outcome': 'success',
                    'nextflow': 'nextflow version 25.10.4 build 1',
                    'dependency_stability': {'status': 'unchanged'}}
                if native_artifact == 'stub':
                    value['stub_profiles'] = ['test']
                manifest.write_text(json.dumps(value))
                trace.write_text('task_id\tname\tstatus\texit\n1\tCOUNT\tCOMPLETED\t0\n')
                if native_artifact == 'failed_trace':
                    trace.write_text(trace.read_text().replace('COMPLETED', 'FAILED'))
                receipt = {'version': 1, 'candidate': metadata['sha'], 'base': base,
                    'pipeline': name, 'pin': pin, 'engine': value['nextflow'],
                    'tasks': [{'task_id': '1', 'name': 'COUNT',
                               'status': 'COMPLETED', 'exit': '0'}],
                    'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    'trace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest()}
                if native_artifact == 'changed_receipt':
                    receipt['candidate'] = 'f' * 40
                (native / name / 'native.json').write_text(json.dumps(receipt))
                if native_artifact == 'changed_trace':
                    trace.write_text(trace.read_text().replace('COUNT', 'OTHER'))
        matrix = tmp_path / ('matrix-' + uuid.uuid4().hex)
        if matrix_artifact != 'missing':
            xml = '<testsuites><testsuite>' + ''.join(
                f'<testcase classname="tests.test_example" name="test_{index}"/>'
                for index in range(3001)) + '</testsuite></testsuites>'
            for lane_os in ('ubuntu-latest', 'macos-latest'):
                for version in ('3.11', '3.12', '3.13', '3.14', '3.15'):
                    if (matrix_artifact == 'missing_lane'
                            and (lane_os, version) == ('macos-latest', '3.15')):
                        continue
                    lane = matrix / f'{lane_os}-{version}'
                    lane.mkdir(parents=True)
                    (lane / 'report.xml').write_text(xml)
                    record = {'version': 1, 'candidate': metadata['sha'], 'os': lane_os,
                        'python': version, 'passed': 3001, 'skipped': [],
                        'report_sha256': hashlib.sha256(xml.encode()).hexdigest()}
                    if matrix_artifact == 'wrong_candidate':
                        record['candidate'] = 'f' * 40
                    (lane / 'record.json').write_text(json.dumps(record))
        env = {**os.environ, "MATRIX_EVIDENCE_DIR": str(matrix), "CANDIDATE_DIR": str(directory),
               "NATIVE_EVIDENCE_DIR": str(native), 'CANDIDATE_SHA': metadata['sha'],
               'VALIDATION_RESULT': 'success', 'DRIFT_RESULT': 'success',
               'NATIVE_RESULT': 'success' if metadata['pipelines'] else 'skipped',
               "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}", "PYTHON": sys.executable,
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
    (repo / "sources.tsv").write_text("# updated inventory\n"
        "mini\thttps://github.com/nf-core/mini.git\tlatest-release\n")
    if workflow == "auto-update.yml":
        (repo / "sources.tsv").write_text("mini\thttps://github.com/nf-core/mini.git\tlatest-release\n")
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
        *(f"name=pytest ({os_name}, {version})" for os_name in ('ubuntu-latest', 'macos-latest')
          for version in ('3.11', '3.12', '3.13', '3.14', '3.15')),
        "name=website", "name=nextflow-integration", "name=drift"}
    assert all(f"head_sha={head}" in call and "conclusion=success" in call for call in checks)
    patch = next(call for call in calls if call[0] == "git-push")
    assert all(calls.index(check) < calls.index(patch) for check in checks)
    dispatches = [call for call in calls if call[:2] == ["workflow", "run"]]
    assert {call[2] for call in dispatches} == {
        "tests.yml", "smoke.yml", "codeql.yml", "deploy-pages.yml"}
    assert all(calls.index(patch) < calls.index(call) and call[-2:] == ["--ref", "main"]
               for call in dispatches)
    assert not git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/maintenance-*")
    if workflow == "discover-pipelines.yml":
        assert git(remote, "show", "main:sources.tsv") == ("# updated inventory\n"
            "mini\thttps://github.com/nf-core/mini.git\tlatest-release")



@pytest.mark.parametrize("failure", [{"FAIL_CHECK": "name=website"}, {"PATCH_ERROR": "rule"}])
def test_check_or_rule_failure_never_publishes_or_deploys(publication, failure):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, _ = run(**failure)
    assert result.returncode != 0
    assert git(remote, "rev-parse", "main") == base
    assert not any(call[:2] == ["workflow", "run"] for call in calls)
    if "FAIL_CHECK" in failure:
        assert not any(call[0] == "git-push" for call in calls)


def test_an_unsuitable_python_publishes_nothing(publication, tmp_path):
    # A python3 older than nfclaw's 3.11 (macOS ships 3.9) is named, not run into an ImportError.
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    old = tmp_path / "python3.9"
    old.write_text("#!/bin/sh\nexit 1\n")
    old.chmod(0o755)
    result, calls, _ = run(PYTHON=str(old))
    assert result.returncode == 1
    assert "needs Python 3.11+" in result.stdout and str(old) in result.stdout
    assert git(remote, "rev-parse", "main") == base and not calls


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
    assert not any(call[0] == "git-push" for call in calls)
    assert not any(call[:2] == ["workflow", "run"] for call in calls)
    # The next run regenerates the update on the new main; no candidate branch is left behind.
    assert not git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/maintenance-*")


def test_a_short_check_evaluation_delay_is_retried(publication):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, outputs = run(PATCH_ERROR="transient")
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") != base
    assert len([call for call in calls if call[0] == "git-push"]) == 2
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
    modules = repo / '.gitmodules'
    modules.write_text(modules.read_text().replace(str(upstream),
                                                   'https://github.com/nf-core/new.git'))
    (repo / "sources.tsv").write_text("mini\thttps://github.com/nf-core/mini.git\tlatest-release\n"
        "new\thttps://github.com/nf-core/new.git\tlatest-release\n")
    staged = git(repo, "diff", "--cached", "--raw")
    result, _, _ = run(kind="discover")
    assert result.returncode == 0, result.stderr
    gitlink = git(remote, "ls-tree", "main", "pipelines/new/upstream")
    assert gitlink.startswith(f"160000 commit {pinned}")
    assert git(remote, "show", "main:pipelines/new/skill.md") == "generated skill"
    assert git(remote, "show", "main:sources.tsv") == ("mini\thttps://github.com/nf-core/mini.git\tlatest-release\n"
        "new\thttps://github.com/nf-core/new.git\tlatest-release")
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


@pytest.mark.parametrize("gate,result", [
    ("VALIDATION_RESULT", "failure"), ("VALIDATION_RESULT", "skipped"),
    ("VALIDATION_RESULT", "cancelled"), ("DRIFT_RESULT", "failure"),
    ("DRIFT_RESULT", "skipped"), ("NATIVE_RESULT", "success"),
    ("NATIVE_RESULT", "failure"), ("CANDIDATE_SHA", "f" * 40),
])
def test_unproven_candidate_or_required_gate_never_reaches_github(publication, gate, result):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    process, calls, _ = run(**{gate: result})
    assert process.returncode != 0
    assert calls == [] and git(remote, "rev-parse", "main") == base


def test_changed_pipeline_cannot_publish_with_skipped_real_tasks(publication):
    repo, remote, base, run = publication
    upstream = repo / 'pipelines/mini/upstream'
    git(upstream, '-c', 'user.name=test', '-c', 'user.email=test@example.com',
        'commit', '--allow-empty', '-qm', 'new release')
    git(repo, 'add', 'pipelines/mini/upstream')
    process, calls, _ = run(NATIVE_RESULT='skipped')
    assert process.returncode != 0
    assert calls == [] and git(remote, "rev-parse", "main") == base


def test_main_movement_after_observation_cannot_be_misreported_as_publication(publication):
    repo, remote, base, run = publication
    (repo / "catalog.md").write_text("regenerated\n")
    result, calls, outputs = run(MOVE_MAIN_AFTER_READ='candidate')
    assert result.returncode == 0, result.stderr
    assert git(remote, 'rev-parse', 'main') != base  # simulated concurrent actor moved it
    assert outputs['published'] == 'false'
    assert not any(call[0] == 'git-push' for call in calls)  # lease refused before remote receive
    assert {call[2] for call in calls if call[:2] == ['workflow', 'run']} == {
        'tests.yml', 'smoke.yml', 'codeql.yml', 'deploy-pages.yml'}


@pytest.mark.parametrize('native_artifact', ['missing', 'stub', 'failed_trace',
                                            'changed_trace', 'changed_receipt'])
def test_successful_native_job_cannot_bypass_fresh_raw_evidence_validation(publication,
                                                                         native_artifact):
    repo, remote, base, run = publication
    upstream = repo / 'pipelines/mini/upstream'
    git(upstream, '-c', 'user.name=test', '-c', 'user.email=test@example.com',
        'commit', '--allow-empty', '-qm', 'new release')
    git(repo, 'add', 'pipelines/mini/upstream')
    result, calls, _ = run(native_artifact=native_artifact)
    assert result.returncode != 0
    assert calls == [] and git(remote, 'rev-parse', 'main') == base


@pytest.mark.parametrize('matrix_artifact', ['missing', 'missing_lane', 'wrong_candidate'])
def test_successful_matrix_job_cannot_bypass_missing_or_substituted_raw_reports(publication,
                                                                             matrix_artifact):
    repo, remote, base, run = publication
    (repo / 'catalog.md').write_text('regenerated\n')
    result, calls, _ = run(matrix_artifact=matrix_artifact)
    assert result.returncode != 0
    assert calls == [] and git(remote, 'rev-parse', 'main') == base


def test_failed_dispatch_can_recover_on_the_same_candidate_without_republishing(publication):
    repo, remote, base, run = publication
    (repo / 'catalog.md').write_text('regenerated\n')
    first, _, _ = run(FAIL_WORKFLOW='deploy-pages.yml')
    assert first.returncode != 0
    published = git(remote, 'rev-parse', 'main')
    assert published != base
    second, calls, outputs = run(reuse_candidate=True, GITHUB_RUN_ATTEMPT='2')
    assert second.returncode == 0, second.stderr
    assert git(remote, 'rev-parse', 'main') == published
    assert outputs['published'] == 'false' and outputs['followup_retried'] == 'true'
    assert len([call for call in calls if call[0] == 'git-push']) == 1
    for workflow in ('tests.yml', 'smoke.yml', 'codeql.yml', 'deploy-pages.yml'):
        assert len([call for call in calls if call[:3] == ['workflow', 'run', workflow]]) == 2
