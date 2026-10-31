"""Guards on the automation: the workflows hold write tokens and run third-party pipeline code."""
import os
import re
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"


def _text(name: str) -> str:
    return (WF / name).read_text(encoding="utf-8")


def _job(text: str, name: str) -> str:
    """The body of one job (from `  <name>:` to the next 2-space-indented key)."""
    m = re.search(rf"^  {name}:\n(.*?)(?=^  \S|\Z)", text, re.M | re.S)
    assert m, f"job {name!r} not found"
    return m.group(1)


def test_no_workflow_expands_inputs_inside_a_shell_script():
    yaml = pytest.importorskip('yaml')

    def inspect(value):
        if isinstance(value, dict):
            if isinstance(value.get('run'), str):
                assert not re.search(r"\$\{\{\s*(inputs|github\.event\.inputs)\.", value['run'])
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    paths = [*WF.glob('*.yml'), *(ROOT / '.github/actions').glob('*/action.yml')]
    for path in paths:
        inspect(yaml.load(path.read_text(), Loader=yaml.BaseLoader))


def test_discovery_step_fails_when_discovery_fails():
    # `discover_pipelines | tee` without pipefail reported a crashed discovery (e.g. nf-co.re down)
    # as "No new pipelines to add." with a green check.
    step = _text("discover-pipelines.yml").split("id: disc", 1)[1].split("\n      - ", 1)[0]
    assert "pipefail" in step


def test_no_checkout_leaves_its_token_in_the_git_config():
    # A persisted token sits in .git/config for every later step, including the upstream pipeline
    # code these jobs parse or run, and in any artifact that uploads the workspace. No job here
    # pushes with it.
    for path in sorted(WF.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        assert text.count("uses: actions/checkout@") == text.count("persist-credentials: false"), \
            path.name


@pytest.mark.parametrize('name, kind', [('auto-update.yml', 'update'),
                                        ('discover-pipelines.yml', 'discover')])
def test_maintenance_hands_its_frozen_candidate_to_the_shared_gate(name, kind):
    yaml = pytest.importorskip('yaml')
    jobs = yaml.load(_text(name), Loader=yaml.BaseLoader)['jobs']
    assert set(jobs) == {'prepare', 'gate'}
    assert jobs['prepare'].get('permissions', {}).get('contents', 'read') == 'read'
    gate = jobs['gate']
    assert gate['uses'] == './.github/workflows/maintenance-gate.yml'
    assert gate['needs'] == 'prepare'
    # Candidate consumers use the immutable producer ID, including on failed-job reruns.
    assert gate['with'] == {'base_sha': '${{ needs.prepare.outputs.base }}',
                            'candidate_sha': '${{ needs.prepare.outputs.sha }}',
                            'candidate_artifact': '${{ needs.prepare.outputs.artifact }}',
                            'pipelines': '${{ needs.prepare.outputs.pipelines }}', 'kind': kind}


def test_the_shared_gate_wires_every_check_to_the_isolated_publisher():
    yaml = pytest.importorskip('yaml')
    jobs = yaml.load(_text('maintenance-gate.yml'), Loader=yaml.BaseLoader)['jobs']
    publisher = jobs['publish']
    assert set(publisher['needs']) == {'validate', 'native', 'drift'}
    assert jobs['validate']['uses'] == './.github/workflows/tests.yml'
    assert jobs['native']['uses'] == './.github/workflows/maintenance-native.yml'
    # The callers grant write for the publisher alone: every gate job drops back to read.
    for job in ('validate', 'native', 'drift'):
        assert jobs[job]['permissions'] == {'contents': 'read'}
    environment = publisher['steps'][-1]['env']
    for field, producer in [('VALIDATION_RESULT', 'validate'), ('DRIFT_RESULT', 'drift'),
                            ('NATIVE_RESULT', 'native')]:
        assert environment[field] == '${{ needs.' + producer + '.result }}'
    assert environment['UPDATE_KIND'] == '${{ inputs.kind }}'
    for job in ('validate', 'native'):
        assert jobs[job]['with']['candidate_artifact'] == '${{ inputs.candidate_artifact }}'


@pytest.mark.parametrize('parsing', ['..  [100%]\n',
    'ss  [100%]\nSKIPPED [1] tests/test_website_parsing.py:51: needs node\n'])
def test_reused_website_gate_refuses_skipped_parser_tests(tmp_path, parsing):
    yaml = pytest.importorskip('yaml')
    steps = yaml.load(_text('tests.yml'), Loader=yaml.BaseLoader)['jobs']['website']['steps']
    script = next(step['run'] for step in steps
                  if step.get('name') == 'Website parsing of the generated skills')
    fake = tmp_path / 'bin'
    fake.mkdir()
    (fake / 'pytest').write_text('#!/bin/sh\nprintf "%s" "$PARSING"\n')
    (fake / 'pip').write_text('#!/bin/sh\nexit 0\n')
    for path in fake.iterdir():
        path.chmod(0o755)
    env = {**os.environ, 'PATH': f"{fake}{os.pathsep}{os.environ['PATH']}",
           'RUNNER_TEMP': str(tmp_path), 'PARSING': parsing}
    result = subprocess.run(['bash', '-e', '-c', script], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert (result.returncode == 0) == ('SKIPPED' not in parsing), result.stdout


def test_pages_and_oidc_permissions_are_scoped_to_the_deploy_job():
    # The build job runs `npm ci` + `next build` (third-party code); only the deploy job needs to
    # publish to Pages or mint an OIDC token.
    text = _text("deploy-pages.yml")
    top = text.split("\njobs:", 1)[0]
    build, deploy = _job(text, "build"), _job(text, "deploy")
    for scope in ("pages: write", "id-token: write"):
        assert scope not in top and scope not in build
        assert scope in deploy


def test_acceptance_script_fails_when_it_finds_no_pipelines(tmp_path):
    # With no arguments it validates `nfclaw list`; an empty list must fail, not pass vacuously.
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "nfclaw").write_text("#!/bin/sh\nexit 0\n")
    (fake / "nfclaw").chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "PYTHON": sys.executable, "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", str(ROOT / "scripts" / "nextflow_accept.sh")], cwd=tmp_path,
                       env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "no pipelines" in (r.stdout + r.stderr).lower()


def test_acceptance_script_rejects_a_failed_partial_pipeline_inventory(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "nfclaw").write_text("#!/bin/sh\necho mini\nexit 1\n")
    (fake / "nfclaw").chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "PYTHON": sys.executable, "RUNNER_TEMP": str(tmp_path)}
    result = subprocess.run(["bash", str(ROOT / "scripts/nextflow_accept.sh")], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "could not list" in result.stdout


def test_parallel_acceptance_checks_every_pipeline_exactly_once(tmp_path):
    text = _text("nextflow-validate.yml")
    count = int(re.search(r'SHARD_COUNT: "(\d+)"', text).group(1))
    shards = [int(n) for n in re.search(r"shard: \[([^]]+)\]", text).group(1).split(",")]
    assert shards == list(range(count))
    raw = text.split("- name: Preview every pipeline", 1)[1].split("        run: |\n", 1)[1]
    raw = raw.split("\n      - name:", 1)[0]
    script = "\n".join(line[10:] for line in raw.splitlines())
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "nfclaw").write_text('#!/bin/sh\ncat "$INVENTORY"\nexit "${LIST_EXIT:-0}"\n')
    (fake / "bash").write_text('#!/bin/sh\nshift\nprintf "%s\\n" "$@" >> "$CHECKED"\n')
    for path in fake.iterdir():
        path.chmod(0o755)
    inventory, checked = tmp_path / "inventory", tmp_path / "checked"
    names = [f"pipeline-{n}" for n in range(91)]
    inventory.write_text("".join(f"{name}\tmetadata\n" for name in names))
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "INVENTORY": str(inventory), "CHECKED": str(checked), "SHARD_COUNT": str(count)}
    for shard in shards:
        result = subprocess.run(["/bin/bash", "-c", script], cwd=tmp_path,
                                env={**env, "SHARD_INDEX": str(shard)}, capture_output=True)
        assert result.returncode == 0, result.stderr
    assert sorted(checked.read_text().splitlines()) == sorted(names)
    checked.unlink()
    result = subprocess.run(["/bin/bash", "-c", script], cwd=tmp_path,
                            env={**env, "SHARD_INDEX": "0", "LIST_EXIT": "1"},
                            capture_output=True)
    assert result.returncode != 0 and not checked.exists()


@pytest.mark.parametrize("step", ["Build + preflight the demo command for every pipeline",
                                   "Check every registry chain"])
def test_smoke_rejects_failed_partial_inventories_before_checking_subset(tmp_path, step):
    raw = _text("smoke.yml").split(f"- name: {step}", 1)[1].split("        run: |\n", 1)[1]
    raw = raw.split("\n      - ", 1)[0]
    script = "\n".join(line[10:] for line in raw.splitlines())
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "nfclaw").write_text(
        '#!/bin/sh\ncase "$1 $2" in\n'
        '"list ") printf "mini\\tmetadata\\n"; exit 1 ;;\n'
        '"chain edges") printf "mini\\tmini2\\tpartial edge\\n"; exit 1 ;;\n'
        '*) echo "$*" >> "$CHECKED"; exit 0 ;;\nesac\n')
    (fake / "git").write_text('#!/bin/sh\nexit 0\n')
    for path in fake.iterdir():
        path.chmod(0o755)
    checked = tmp_path / "checked"
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "CHECKED": str(checked), "RUNNER_TEMP": str(tmp_path),
           "GITHUB_STEP_SUMMARY": str(tmp_path / "summary")}
    result = subprocess.run(["/bin/bash", "-c", script], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert result.returncode != 0, "a partial subset is not a completed smoke check"
    assert not checked.exists(), "do not validate a subset from a failed inventory command"


@pytest.mark.parametrize("listing_exit", [0, 1])
def test_execution_evidence_packaging_fails_on_a_partial_task_listing(tmp_path, listing_exit):
    raw = _text("pipeline-execution.yml").split("- name: Package execution evidence", 1)[1]
    raw = raw.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
    script = "\n".join(line[10:] for line in raw.splitlines())
    task = tmp_path / "work" / "ab" / "cdef"
    task.mkdir(parents=True)
    (task / ".command.sh").write_text("echo task\n")
    fake = tmp_path / "bin"
    fake.mkdir()
    # A listing that stops partway (e.g. an unreadable task directory) still prints what it found.
    (fake / "find").write_text(f'#!/bin/sh\n/usr/bin/find "$@"\nexit {listing_exit}\n')
    (fake / "find").chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "RUNNER_TEMP": str(tmp_path / "runner")}
    # GitHub runs a step without an explicit shell as `bash -e {0}`, without pipefail.
    result = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert (result.returncode == 0) == (listing_exit == 0), result.stderr
    with tarfile.open(tmp_path / "runner" / "evidence" / "task-commands.tar.gz") as archive:
        assert "work/ab/cdef/.command.sh" in archive.getnames()  # retained even when incomplete


def test_every_action_is_pinned_to_a_full_commit():
    # A tag can be moved to different code after review; only a commit SHA fixes what runs with the
    # workflow's token. Local composite actions (./.github/actions/...) are reviewed in
    # this repository.
    for path in sorted([*WF.glob("*.yml"), *(ROOT / ".github" / "actions").glob("*/action.yml")]):
        for line in path.read_text(encoding="utf-8").splitlines():
            if m := re.match(r"^\s*-?\s*uses:\s*(\S+)", line):
                ref = m.group(1)
                pinned = ref.startswith("./") or re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", ref)
                assert pinned, f"{path.name}: {ref}"


def test_dependabot_keeps_every_pinned_action_and_the_website_dependencies_current():
    # Commit-pinned actions never move by themselves: every directory that pins one, and the
    # website's npm manifest, must be under a version-update entry that names a real directory.
    yaml = pytest.importorskip('yaml')
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert config["version"] == 2
    covered = {}
    for entry in config["updates"]:
        assert entry["schedule"]["interval"] in ("daily", "weekly", "monthly")
        # A just-published release is where a hijacked or broken package lands; wait it out.
        assert entry["cooldown"]["default-days"] >= 3, entry["package-ecosystem"]
        patterns = entry.get("directories") or [entry["directory"]]
        directories = {path for pattern in patterns
                       for path in ([ROOT] if not pattern.strip("/")
                                    else ROOT.glob(pattern.strip("/")))
                       if path.is_dir()}
        assert directories, f"{entry['package-ecosystem']}: {patterns} names no directory"
        covered.setdefault(entry["package-ecosystem"], set()).update(directories)
    pinning = {ROOT} | {path.parent for path in (ROOT / ".github" / "actions").glob("*/action.yml")
                        if "uses:" in path.read_text(encoding="utf-8")}
    assert pinning <= covered["github-actions"]
    assert (ROOT / "website") in covered["npm"] and (ROOT / "website" / "package.json").is_file()


def test_nextflow_launcher_download_has_connect_and_total_limits():
    action = (ROOT / ".github" / "actions" / "setup-nextflow" / "action.yml").read_text()
    command = action.split("curl ", 1)[1].split("\n        echo ", 1)[0].replace("\\\n", " ")
    args = shlex.split(command)
    for option in ("--connect-timeout", "--max-time"):
        assert option in args
        assert float(args[args.index(option) + 1]) > 0


def test_code_scanning_covers_every_language_in_the_repository():
    text = _text("codeql.yml")
    languages = re.search(r"language: \[([^]]+)\]", text).group(1)
    assert {lang.strip() for lang in languages.split(",")} == {"actions",
                                                               "javascript-typescript", "python"}
    assert "security-events: write" in _job(text, "analyze")
    assert text.count("uses: actions/checkout@") == text.count("persist-credentials: false")


def test_every_pytest_lane_runs_the_whole_suite_on_every_core():
    # Each of the ten lanes ran the full suite one test at a time on a multi-core runner (16 to
    # 34 minutes a lane). The lanes split it over the cores and still report every case, unfiltered.
    yaml = pytest.importorskip('yaml')
    steps = yaml.load(_text('tests.yml'), Loader=yaml.BaseLoader)['jobs']['pytest']['steps']
    script = next(step['run'] for step in steps
                  if step.get('name') == 'Execute the complete Python suite')
    [command] = [line.strip() for line in script.splitlines() if line.strip().startswith('pytest')]
    words = shlex.split(command)
    assert words[:6] == ['pytest', '-q', '-n', 'auto', '--dist', 'worksteal']
    assert not {'-k', '-m', '-x', '--lf', '--ff'} & set(words)
    dev = re.search(r'^dev = \[(.*)\]$', (ROOT / 'pyproject.toml').read_text(encoding='utf-8'),
                    re.M).group(1)
    assert '"pytest-xdist' in dev


def test_a_new_pull_request_push_cancels_only_that_pull_request_s_previous_run():
    # Superseded pull request runs stayed queued for hours behind the five-at-a-time macOS
    # runners. A push to a pull request now cancels its own previous run; a push to main, a
    # schedule, a dispatch and a maintenance gate (`workflow_call`) each keep a group of their own.
    yaml = pytest.importorskip('yaml')
    superseded = ("${{ github.workflow }}-${{ github.event_name == 'pull_request' && "
                  "github.event.pull_request.number || github.run_id }}")
    for path in sorted(WF.glob('*.yml')):
        doc = yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
        concurrency = doc.get('concurrency')
        if 'pull_request' in doc['on']:
            assert concurrency == {
                'group': superseded,
                'cancel-in-progress': "${{ github.event_name == 'pull_request' }}"}, path.name
        else:
            assert concurrency is None or concurrency['cancel-in-progress'] == 'false', path.name
