"""Exercise the release gate against controlled external Nextflow outcomes."""
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _executable(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _accept(tmp_path, log, exit_code, *, timeout_available=True, exceptions="",
            engine_log="engine cause\n", second=None, third=None):
    """Run the gate on one fake pipeline whose preview prints `log` and exits `exit_code`.
    `second` and `third` are (log, exit_code) for relaunches; `second` also serves later ones."""
    up = tmp_path / "pipelines" / "mini" / "upstream"
    up.mkdir(parents=True)
    (up / "nextflow.config").write_text("manifest { nextflowVersion = '!>=25.10.4' }\n")
    fake = tmp_path / "bin"
    fake.mkdir()
    _executable(fake / "git", '#!/bin/sh\ncase "$*" in\n  submodule*) exit 0 ;;\n'
                f'  "-C pipelines/mini/upstream rev-parse HEAD") echo {COMMIT} ;;\n'
                '  *) exit 2 ;;\nesac\n')
    _executable(fake / "timeout", '#!/bin/sh\n[ "$1" = --kill-after=10s ] || exit 2\n'
                'printf "%s\\n" "$2" >> "$FAKE_TIMEOUTS"\nshift\nshift\nexec "$@"\n')
    _executable(fake / "nextflow", '#!/bin/sh\nprintf "%s\\n" "$@" > "$FAKE_NXF_ARGS"\n'
                'n=$(cat "$FAKE_NXF_COUNT" 2>/dev/null || echo 0); n=$((n + 1))\n'
                'echo "$n" > "$FAKE_NXF_COUNT"\n'
                '[ "$1" = -log ] && cat "$FAKE_ENGINE_LOG" > "$2"\n'
                'if [ "$n" -gt 2 ] && [ -f "$FAKE_NXF_LOG3" ]; then\n'
                '  cat "$FAKE_NXF_LOG3"; exit "$FAKE_NXF_EXIT3"\nfi\n'
                'if [ "$n" -gt 1 ] && [ -f "$FAKE_NXF_LOG2" ]; then\n'
                '  cat "$FAKE_NXF_LOG2"; exit "$FAKE_NXF_EXIT2"\nfi\n'
                'cat "$FAKE_NXF_LOG"\nexit "$FAKE_NXF_EXIT"\n')
    source_log = tmp_path / "nextflow-output.txt"
    source_log.write_text(log)
    (tmp_path / "engine-output.txt").write_text(engine_log)
    registry = tmp_path / "exceptions.tsv"
    registry.write_text(exceptions)
    result = tmp_path / "verdict.tsv"
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "RUNNER_TEMP": str(tmp_path), "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
           "NFCLAW_RESULT_FILE": str(result), "NFCLAW_KEEP_SUBMODULES": "1",
           "NFCLAW_LOG_DIR": str(tmp_path / "retained-logs"),
           "NFCLAW_ACCEPT_EXCEPTIONS": str(registry), "NFCLAW_ACCEPT_RETRY_DELAY": "0",
           "FAKE_NXF_LOG": str(source_log), "FAKE_NXF_EXIT": str(exit_code),
           "FAKE_NXF_LOG2": str(tmp_path / "second-output.txt"),
           "FAKE_NXF_EXIT2": str(second[1] if second else 0),
           "FAKE_NXF_LOG3": str(tmp_path / "third-output.txt"),
           "FAKE_NXF_EXIT3": str(third[1] if third else 0),
           "FAKE_ENGINE_LOG": str(tmp_path / "engine-output.txt"),
           "FAKE_NXF_COUNT": str(tmp_path / "launches.txt"),
           "FAKE_TIMEOUTS": str(tmp_path / "timeouts.txt"),
           "FAKE_NXF_ARGS": str(tmp_path / "nextflow-args.txt")}
    if second:
        (tmp_path / "second-output.txt").write_text(second[0])
    if third:
        (tmp_path / "third-output.txt").write_text(third[0])
    if not timeout_available:
        startup = tmp_path / "bash-startup"
        startup.write_text('command() {\ncase "$*" in\n'
                           '"-v timeout"|"-v gtimeout") return 1 ;;\n'
                           '*) builtin command "$@" ;;\nesac\n}\n')
        env["BASH_ENV"] = str(startup)
    process = subprocess.run(["bash", str(ROOT / "scripts" / "nextflow_accept.sh"), "mini"],
                             cwd=tmp_path, env=env, capture_output=True, text=True)
    return process, result.read_text()


@pytest.mark.parametrize("banner", ["* PREVIEW *", "Only displaying parameters that differ",
                                    "Core Nextflow options", "If you use nf-core"])
def test_banner_does_not_accept_workflow_failure(tmp_path, banner):
    process, verdict = _accept(tmp_path, f"{banner}\nERROR ~ Invalid sample metadata\n", 1)
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"


@pytest.mark.parametrize("exit_code", [124, 137, 143])
def test_timeout_or_signal_after_banner_is_rejected(tmp_path, exit_code):
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", exit_code)
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"


def test_remote_input_staging_failure_is_unverified_and_fails_gate(tmp_path):
    process, verdict = _accept(tmp_path, "* PREVIEW *\nERROR ~ No such file or directory: "
                              "https://example.invalid/reads.fastq.gz\n", 1)
    assert process.returncode != 0
    assert verdict == "mini\tstaging-unverified\n"


def test_successful_preview_is_accepted(tmp_path):
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", 0)
    assert process.returncode == 0
    assert verdict == "mini\taccepted\n"
    # The gate invokes preview mode, which Nextflow defines as skipping every process.
    args = (tmp_path / "nextflow-args.txt").read_text().splitlines()
    assert "-preview" in args and "-stub-run" not in args


def test_unavailable_timeout_cannot_launch_an_unbounded_preview(tmp_path):
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", 0, timeout_available=False)
    assert process.returncode != 0, "a bounded acceptance gate must not silently run unbounded"
    assert verdict == "mini\trejected\n"
    assert not (tmp_path / "nextflow-args.txt").exists()
    assert "timeout" in process.stdout.lower()


def test_failed_preview_retains_console_and_engine_evidence_after_cleanup(tmp_path):
    console = "ERROR ~ Invalid sample metadata\n"
    process, verdict = _accept(tmp_path, console, 1)
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"
    logs = tmp_path / "retained-logs"
    assert (logs / "mini.console.log").read_text() == console
    assert (logs / "mini.nextflow.log").read_text() == "engine cause\n"
    assert not list(tmp_path.glob("nfclaw-accept.*"))


def test_acceptance_uses_private_scratch_and_preserves_unrelated_temp_files(tmp_path):
    config = tmp_path / "no-reports.config"
    config.write_text("unrelated user config\n")
    result = tmp_path / "prev-mini"
    result.mkdir()
    (result / "precious.txt").write_text("previous scientific result\n")
    process, _ = _accept(tmp_path, "* PREVIEW *\n", 0)
    assert process.returncode == 0, process.stderr
    assert config.read_text() == "unrelated user config\n"
    assert (result / "precious.txt").read_text() == "previous scientific result\n"
    assert not list(tmp_path.glob("nfclaw-accept.*"))



HANG = "barrier arrives \\(monitor: local\\)"


def _row(outcome, evidence, commit=COMMIT):
    return f"# comment line\nmini\t{commit}\t{outcome}\t{evidence}\tdocumented upstream defect\n"


def test_documented_preview_hang_of_the_exact_commit_is_known_not_accepted(tmp_path):
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", 124, exceptions=_row("timeout", HANG),
                               engine_log="DEBUG <<< barrier arrives (monitor: local)\n")
    assert process.returncode == 0, process.stdout
    assert verdict == "mini\tknown-timeout\n"
    # A documented hang is bounded more tightly: its evidence is written within seconds.
    assert (tmp_path / "timeouts.txt").read_text() == "300\n"


def test_exception_for_another_commit_does_not_apply(tmp_path):
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", 124,
                               exceptions=_row("timeout", HANG, commit="f" * 40),
                               engine_log="DEBUG <<< barrier arrives (monitor: local)\n")
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"
    assert (tmp_path / "timeouts.txt").read_text() == "900\n"


def test_exception_whose_evidence_no_longer_matches_is_rejected(tmp_path):
    # Same exit status, but not the documented point of failure (the DAG was never built).
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", 124, exceptions=_row("timeout", HANG),
                               engine_log="DEBUG still staging inputs\n")
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"
    assert "without its documented evidence" in process.stdout


def test_exception_with_a_different_failure_is_rejected(tmp_path):
    process, verdict = _accept(tmp_path, "ERROR ~ Invalid sample metadata\n", 1,
                               exceptions=_row("timeout", HANG),
                               engine_log="DEBUG <<< barrier arrives (monitor: local)\n")
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"
    assert "no longer fails as documented (timeout): observed rejected" in process.stdout


def test_documented_rejection_requires_its_evidence(tmp_path):
    row = _row("rejected", "Unable to read script: .*GRCm39\\.fa")
    process, verdict = _accept(tmp_path, "ERROR ~ Unable to read script: 'x.nf' -- cause: "
                               "/o/references/mm10/GRCm39.fa\n", 1, exceptions=row)
    assert process.returncode == 0
    assert verdict == "mini\tknown-rejected\n"


def test_exception_with_empty_evidence_never_applies(tmp_path):
    row = f"mini\t{COMMIT}\trejected\t\treason\n"
    process, verdict = _accept(tmp_path, "ERROR ~ anything\n", 1, exceptions=row)
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"


def test_documented_pipeline_that_now_passes_is_a_stale_exception(tmp_path):
    process, verdict = _accept(tmp_path, "* PREVIEW *\n", 0, exceptions=_row("timeout", HANG))
    assert process.returncode != 0
    assert verdict == "mini\tstale-exception\n"


def test_unreachable_remote_file_is_retried_once(tmp_path):
    flaky = ("* --checkm_download_url (https://zenodo.org/x.tar.gz): the file or directory "
             "'https://zenodo.org/x.tar.gz' does not exist\n")
    process, verdict = _accept(tmp_path, flaky, 1, second=("* PREVIEW *\n", 0))
    assert process.returncode == 0, process.stdout
    assert verdict == "mini\taccepted\n"
    assert (tmp_path / "launches.txt").read_text().strip() == "2"


def test_persistently_unreachable_remote_file_is_staging_unverified(tmp_path):
    flaky = "ERROR ~ No such file or directory: https://example.invalid/reads.fastq.gz\n"
    process, verdict = _accept(tmp_path, flaky, 1, second=(flaky, 1))
    assert process.returncode != 0
    assert verdict == "mini\tstaging-unverified\n"
    assert (tmp_path / "launches.txt").read_text().strip() == "3"


def test_remote_outage_outlasting_the_first_retry_is_retried_again(tmp_path):
    # GitHub answered 503 for sopa's test-data page across a 30-second retry and a rerun.
    flaky = ("* --input: Error for field 'data_path' (https://github.com/x/blob/dev/s.csv): the file "
             "or directory 'https://github.com/x/blob/dev/s.csv' does not exist\n")
    process, verdict = _accept(tmp_path, flaky, 1, second=(flaky, 1), third=("* PREVIEW *\n", 0))
    assert process.returncode == 0, process.stdout
    assert verdict == "mini\taccepted\n"
    assert (tmp_path / "launches.txt").read_text().strip() == "3"
    assert "retrying the preview in 0s (attempt 3 of 3)" in process.stdout


PLUGIN_DOWNLOAD = ("* PREVIEW * null [x] DSL2 - revision: b77a479c29\n"
                   "Downloading plugin nf-prov@1.2.2\n"
                   "ERROR ~ Error during download of plugin nf-prov\n")


def test_failed_plugin_download_is_retried_once(tmp_path):
    # Observed on a GitHub runner: the plugin's release host answered HTTP 500 once.
    process, verdict = _accept(tmp_path, PLUGIN_DOWNLOAD, 1, second=("* PREVIEW *\n", 0))
    assert process.returncode == 0, process.stdout
    assert verdict == "mini\taccepted\n"
    assert (tmp_path / "launches.txt").read_text().strip() == "2"
    assert "a plugin download failed (exit 1); retrying the preview in 0s (attempt 2 of 3)" in process.stdout


def test_persistently_failing_plugin_download_is_rejected(tmp_path):
    process, verdict = _accept(tmp_path, PLUGIN_DOWNLOAD, 1, second=(PLUGIN_DOWNLOAD, 1))
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"
    assert (tmp_path / "launches.txt").read_text().strip() == "3"


def test_ordinary_failure_is_not_retried(tmp_path):
    process, verdict = _accept(tmp_path, "ERROR ~ Invalid sample metadata\n", 1,
                               second=("* PREVIEW *\n", 0))
    assert process.returncode != 0
    assert verdict == "mini\trejected\n"
    assert (tmp_path / "launches.txt").read_text().strip() == "1"


def test_committed_exceptions_are_well_formed_and_documented():
    registry = ROOT / "scripts" / "nextflow_accept_exceptions.tsv"
    sources = {line.split("\t")[0] for line in
               (ROOT / "sources.tsv").read_text().splitlines()[1:] if line.strip()}
    known_issues = (ROOT / "docs" / "known-issues.md").read_text()
    rows = [line for line in registry.read_text().splitlines()
            if line.strip() and not line.startswith("#")]
    assert rows
    for line in rows:
        fields = line.split("\t")
        assert len(fields) == 5 and all(fields), line
        name, commit, outcome, evidence, _ = fields
        assert name in sources
        assert re.fullmatch(r"[0-9a-f]{40}", commit)
        assert outcome in {"rejected", "staging-unverified", "timeout"}
        re.compile(evidence)
        assert f"`{name}`" in known_issues, f"{name} needs its investigation in known-issues.md"

def _discovery_step(tmp_path, verdict):
    raw = (ROOT / ".github" / "workflows" / "discover-pipelines.yml").read_text()
    step = raw.split("id: disc", 1)[1].split("\n      - name: Unit tests", 1)[0]
    script = re.search(r"^        run: \|\n(.*)", step, re.M | re.S).group(1)
    script = "\n".join(line[10:] for line in script.splitlines())
    fake = tmp_path / "bin"
    fake.mkdir()
    _executable(fake / "python", '#!/bin/sh\ncase "$*" in\n'
                '  *"--rollback "*) printf "%s\\n" "$*" >> "$ROLLBACK_LOG" ;;\n'
                '  *"librarian.discover_pipelines"*) echo "mini: added at 1.0.0" ;;\n'
                '  *"librarian.write_catalog"*) exit 0 ;;\n'
                '  *) exit 2 ;;\nesac\n')
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    _executable(scripts / "nextflow_accept.sh", '#!/bin/sh\nprintf "%s" "$FAKE_VERDICT" '
                '> "$NFCLAW_RESULT_FILE"\nexit 1\n')
    output = tmp_path / "github-output"
    rollback = tmp_path / "rollback.txt"
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}", "LIMIT": "12",
           "RUNNER_TEMP": str(tmp_path), "GITHUB_OUTPUT": str(output),
           "FAKE_VERDICT": verdict, "ROLLBACK_LOG": str(rollback)}
    process = subprocess.run(["bash", "-c", script], cwd=tmp_path, env=env,
                             capture_output=True, text=True)
    return process, output.read_text() if output.exists() else "", rollback


@pytest.mark.parametrize("verdict", ["rejected", "staging-unverified"])
def test_discovery_drops_every_pipeline_without_completed_acceptance(tmp_path, verdict):
    process, output, rollback = _discovery_step(tmp_path, f"mini\t{verdict}\n")
    assert process.returncode == 0
    assert output == "kept=0\n"
    assert "--rollback mini" in rollback.read_text()


@pytest.mark.parametrize("verdict", ["", "mini\tunknown\n", "other\taccepted\n",
                                    "mini\taccepted\nmini\taccepted\n"])
def test_discovery_cannot_keep_a_pipeline_with_missing_or_unknown_verdict(tmp_path, verdict):
    process, output, _ = _discovery_step(tmp_path, verdict)
    assert process.returncode != 0
    assert "kept=" not in output


def test_discovery_keeps_a_completed_acceptance(tmp_path):
    process, output, rollback = _discovery_step(tmp_path, "mini\taccepted\n")
    assert process.returncode == 0
    assert output == "kept=1\n"
    assert not rollback.exists()
