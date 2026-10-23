"""Guards on the automation: the workflows hold write tokens and run third-party pipeline code."""
import os
import re
import shlex
import subprocess
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
    # `${{ inputs.* }}` inside `run:` is substituted before bash parses the script, so a crafted
    # value becomes shell code. Inputs may only reach a script through an `env:` mapping.
    for wf in sorted(WF.glob("*.yml")):
        for line in wf.read_text(encoding="utf-8").splitlines():
            if re.search(r"\$\{\{\s*(inputs|github\.event\.inputs)\.", line):
                assert re.match(r"^\s+[A-Z][A-Z0-9_]*:\s", line), f"{wf.name}: {line.strip()}"


def test_discovery_step_fails_when_discovery_fails():
    # `discover_pipelines | tee` without pipefail reported a crashed discovery (e.g. nf-co.re down)
    # as "No new pipelines to add." with a green check.
    step = _text("discover-pipelines.yml").split("id: disc", 1)[1].split("\n      - ", 1)[0]
    assert "pipefail" in step


def test_jobs_that_run_upstream_code_do_not_keep_a_write_token():
    # Both jobs evaluate upstream pipeline code (`nextflow run -preview` parses each release's Groovy
    # config) while holding contents: write; the checkout must not leave that token in .git/config.
    for name in ("auto-update.yml", "discover-pipelines.yml"):
        text = _text(name)
        assert text.count("uses: actions/checkout@") == text.count("persist-credentials: false"), name


@pytest.mark.parametrize("name", ["auto-update.yml", "discover-pipelines.yml"])
def test_write_capable_test_gates_install_yaml_before_running_the_suite(name):
    text = _text(name)
    # PyYAML is optional for the CLI, but required by the full automation gate. The scheduled
    # update failed on valid merge overrides and recursive-alias controls without this extra.
    install = re.search(r"- run: (pip install .*)", text)
    assert install and install.start() < text.index("pytest -q"), name
    args = shlex.split(install.group(1))
    editable = args[args.index("-e") + 1]
    assert editable.startswith(".[") and editable.endswith("]"), name
    assert {"dev", "yaml"} <= set(editable[2:-1].split(",")), name


@pytest.mark.parametrize("name, gate", [("auto-update.yml", "Unit tests + final drift gate"),
                                        ("discover-pipelines.yml", "Unit tests + drift gate")])
@pytest.mark.parametrize("parsing", ["..  [100%]\n",
                                     "ss  [100%]\nSKIPPED [1] tests/test_website_parsing.py:51: needs node\n"])
def test_write_capable_gates_run_the_website_parsing_tests(tmp_path, name, gate, parsing):
    # These jobs merge PRs that trigger no tests.yml run, and the site's parser tests skip without
    # node: a silent skip would merge and deploy skill.md files the site was never checked to read.
    text = _text(name)
    step = text.index(f"- name: {gate}")
    install = re.search(r"working-directory: website\n\s+run: (npm ci .*)", text)
    assert install and install.start() < step, name
    assert "--ignore-scripts" in install.group(1).split(), name
    raw = text[step:].split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
    script = "\n".join(line[10:] for line in raw.splitlines())
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "pytest").write_text(
        '#!/bin/sh\ncase "$*" in *test_website_parsing*) printf "%s" "$PARSING" ;; esac\n')
    (fake / "python").write_text("#!/bin/sh\nexit 0\n")
    (fake / "ruff").write_text("#!/bin/sh\nexit 0\n")
    (fake / "npm").write_text("#!/bin/sh\nexit 0\n")
    for path in fake.iterdir():
        path.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "RUNNER_TEMP": str(tmp_path), "PARSING": parsing}
    # GitHub runs a step without an explicit shell as `bash -e {0}`, without pipefail.
    result = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert (result.returncode == 0) == ("SKIPPED" not in parsing), result.stdout


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
           "RUNNER_TEMP": str(tmp_path)}
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
           "RUNNER_TEMP": str(tmp_path)}
    result = subprocess.run(["bash", str(ROOT / "scripts/nextflow_accept.sh")], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "could not list" in result.stdout


def test_parallel_acceptance_checks_every_pipeline_exactly_once(tmp_path):
    text = _text("nextflow-validate.yml")
    count = int(re.search(r'SHARD_COUNT: "(\d+)"', text).group(1))
    shards = [int(n) for n in re.search(r"shard: \[([^]]+)\]", text).group(1).split(",")]
    assert shards == list(range(count))
    raw = text.split("- name: Preview every pipeline", 1)[1].split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
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
    # workflow's token. Local composite actions (./.github/actions/...) are reviewed in this repository.
    for path in sorted([*WF.glob("*.yml"), *(ROOT / ".github" / "actions").glob("*/action.yml")]):
        for line in path.read_text(encoding="utf-8").splitlines():
            if m := re.match(r"^\s*-?\s*uses:\s*(\S+)", line):
                ref = m.group(1)
                assert ref.startswith("./") or re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", ref), f"{path.name}: {ref}"


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
    assert {lang.strip() for lang in languages.split(",")} == {"actions", "javascript-typescript", "python"}
    assert "security-events: write" in _job(text, "analyze")
    assert text.count("uses: actions/checkout@") == text.count("persist-credentials: false")
