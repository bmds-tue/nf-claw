import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from runner import chain, cli, orchestration, versions
from runner.errors import ErrorCode, NfclawError
from runner.outputs import OutputsReport
from runner.submodule import SubmoduleStatus


def _seed(tmp_path):
    for name in ("rnaseq", "sarek"):
        d = tmp_path / "pipelines" / name
        (d / "upstream").mkdir(parents=True)
        d.joinpath("skill.md").write_text(f"---\nname: {name}\nversion: 1.0.0\n---\n# {name}\n")
    return tmp_path


@pytest.fixture
def captured(tmp_path, monkeypatch):
    """`run_pipeline` replaced by a stub that records the keyword arguments the CLI passes it."""
    seen = {}
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: seen.update(k) or orchestration.RunResult(
                            "CMD", Path("/o"), True, None))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    return seen


def test_list_prints_pipelines(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "rnaseq" in out and "sarek" in out


def test_show_prints_skill(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["show", "sarek"]) == 0
    assert "# sarek" in capsys.readouterr().out


def test_run_hands_the_raw_input_to_the_pipeline_schema(tmp_path, captured):
    # What `--input` is — a samplesheet, a directory, an accession, `false` — depends on the
    # pipeline's schema, so the CLI must not pre-judge it as a local path (PXD009752
    # became <cwd>/PXD009752).
    for raw in ("PXD009752", "false", "rel/ss.csv", "https://example.test/ss.csv"):
        assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--input", raw]) == 0
        assert captured["input_path"] == raw
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 0
    assert captured["input_path"] is None


def test_unknown_options_are_rejected_outside_run(tmp_path, monkeypatch, capsys):
    # Only `run` forwards unknown flags (to the pipeline). Elsewhere a typo was silently ignored:
    # `show rnaseq --pipeline-versoin 3.0.0` printed the *latest* docs and exited 0.
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    for argv in (["show", "sarek", "--pipeline-versoin", "3.0.0"], ["list", "--bogus"],
                 ["versions", "sarek", "--bogus"], ["verify", "a", "--against", "b", "--x"]):
        with pytest.raises(SystemExit) as exc:
            cli.main(argv)
        assert exc.value.code == 2
        assert "unrecognized arguments" in capsys.readouterr().err


def test_run_has_no_wall_clock_limit_unless_asked(tmp_path, captured):
    # A real sarek WGS or a large rnaseq run routinely exceeds 12 h; an undocumented default that
    # killed the whole run at that point must not exist. --timeout stays available on request.
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 0
    assert captured["timeout_seconds"] is None
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--timeout", "3600"]) == 0
    assert captured["timeout_seconds"] == 3600


def test_collect_overrides_parses_flags():
    ov = cli._collect_overrides(["--tools", "strelka", "--wes"])
    assert ov == {"tools": "strelka", "wes": True}


def test_collect_overrides_handles_equals_form():
    # `--key=value` is a universal CLI convention agents will use.
    assert cli._collect_overrides(["--genome=GRCh38"]) == {"genome": "GRCh38"}
    ov = cli._collect_overrides(["--tools=strelka,mutect2", "--wes", "--step", "mapping"])
    assert ov == {"tools": "strelka,mutect2", "wes": True, "step": "mapping"}


def test_collect_overrides_rejects_stray_tokens():
    with pytest.raises(NfclawError) as exc:
        cli._collect_overrides(["orphan.csv"])
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "unexpected extra argument" in str(exc.value)


def test_run_prints_command_and_outputs_summary(tmp_path, monkeypatch, capsys):
    rep = OutputsReport(multiqc_report=Path("/o/multiqc_report.html"),
                        files=("a.txt", "b.txt"))
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: orchestration.RunResult("CMD", Path("/o"), False, rep))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert "CMD" in out and "2 files" in out and "multiqc" in out


def test_run_summary_names_the_run_log(tmp_path, monkeypatch, capsys):
    rep = OutputsReport(multiqc_report=None, files=("a.txt",))
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: orchestration.RunResult(
                            "CMD", Path("/o"), False, rep,
                            log_path=Path("/o/provenance/logs/run.log")))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 0
    assert "log: /o/provenance/logs/run.log" in capsys.readouterr().out


def test_check_exposes_checked_deferred_and_unsupported_validation(tmp_path, monkeypatch, capsys):
    result = orchestration.RunResult('CMD', tmp_path / 'out', True, None)
    result.validation_scope = {'version': 1, 'checks': [
        {'id': 'source_identity', 'status': 'checked', 'scope': 'selected source'},
        {'id': 'remote_inputs', 'status': 'deferred', 'scope': 'runtime staging'},
        {'id': 'scientific_completeness', 'status': 'unsupported',
         'scope': 'scientific contracts'}]}
    monkeypatch.setattr(orchestration, 'run_pipeline', lambda *a, **k: result)
    monkeypatch.setattr(cli, '_repo_root', lambda: tmp_path)
    assert cli.main(['run', 'x', '--outdir', str(tmp_path / 'out'), '--check']) == 0
    text = capsys.readouterr().out
    assert 'preflight checked: source_identity' in text
    assert 'preflight deferred: remote_inputs' in text
    assert 'preflight unsupported: scientific_completeness' in text


def test_versions_command_lists_tags_and_marks_pin(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(versions, "available",
                        lambda name, **k: [("2.0.0", True), ("1.2.0", False)])
    assert cli.main(["versions", "sarek"]) == 0
    out = capsys.readouterr().out
    assert "2.0.0" in out and "latest" in out and "1.2.0" in out


def test_run_threads_pipeline_version(tmp_path, captured):
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"),
                     "--pipeline-version", "1.2.0"]) == 0
    assert captured["pipeline_version"] == "1.2.0"


def test_show_pipeline_version_prints_generated_docs(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    cached = root / "pipelines" / "sarek" / ".versions" / "1.2.0" / "upstream"
    st = SubmoduleStatus("sarek", cached, True, True, "1.2.0", "abc", ())
    monkeypatch.setattr(versions, "ensure", lambda *a, **k: st)

    def fake_generate(status, *, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "skill.md").write_text("# sarek @ 1.2.0\n")
        return dest_dir / "skill.md", dest_dir / "reference.md"

    monkeypatch.setattr(versions, "generate_docs", fake_generate)
    assert cli.main(["show", "sarek", "--pipeline-version", "1.2.0"]) == 0
    assert "# sarek @ 1.2.0" in capsys.readouterr().out


def test_show_unknown_pipeline_with_version_errors_cleanly(tmp_path, monkeypatch, capsys):
    # An unknown pipeline must 404 cleanly (return 1), never attempt git work on a bad path.
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["show", "nope", "--pipeline-version", "1.0.0"]) == 1
    assert "pipeline_not_found" in capsys.readouterr().err


def test_show_unknown_pipeline_without_version_errors_cleanly(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["show", "nope"]) == 1
    captured = capsys.readouterr()
    assert "pipeline_not_found" in captured.err
    assert "Traceback" not in captured.err


def test_non_editable_install_reports_missing_repository_content(tmp_path, monkeypatch, capsys):
    # A wheel contains the Python packages but intentionally not the large pipeline library.
    # Never make `nfclaw list` silently look valid with zero pipelines in that situation.
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "site-packages" / "runner" / "cli.py"))
    assert cli.main(["list"]) == 1
    captured = capsys.readouterr()
    assert "environment" in captured.err
    assert "pip install -e ." in captured.err


def test_versions_empty_reports_none_found(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(versions, "available", lambda name, **k: [])
    assert cli.main(["versions", "sarek"]) == 0
    assert "no release" in capsys.readouterr().err.lower()


def test_run_threads_nxf_ver_and_env(tmp_path, captured):
    rc = cli.main(["run", "x", "--outdir", str(tmp_path / "out"),
                   "--nxf-ver", "25.10.2",
                   "--nxf-env", "NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true",
                   "--nxf-env", "NXF_OFFLINE=true"])
    assert rc == 0
    assert captured["nxf_ver"] == "25.10.2"
    assert captured["nxf_env"] == {"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true",
                                   "NXF_OFFLINE": "true"}


def test_run_prints_the_command_with_the_nxf_env_it_runs_under(tmp_path, monkeypatch, capsys):
    # `--check` promises the exact command that would run; under `--nxf-ver 25.10.4` that command
    # runs with NXF_VER=25.10.4, and a copy without it would run whatever engine the shell
    # defaults to.
    monkeypatch.setattr(orchestration, "run_pipeline", lambda *a, **k: orchestration.RunResult(
        "nextflow run /t -profile binac2", Path("/o"), True, None,
        env={"NXF_VER": "25.10.4", "NXF_JVM_ARGS": "-Da=b -Dc=d"}))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--check"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == (
        "NXF_JVM_ARGS='-Da=b -Dc=d' NXF_VER=25.10.4 nextflow run /t -profile binac2")


def test_run_rejects_non_nxf_env_var(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    rc = cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--nxf-env", "FOO=bar"])
    assert rc == 1
    assert "NXF_" in capsys.readouterr().err


def test_run_threads_config(tmp_path, captured):
    cfg = tmp_path / "host.config"
    cfg.write_text("docker { runOptions = '--network host' }\n")
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"),
                     "-c", str(cfg), "--config", str(cfg)]) == 0
    assert captured["configs"] == [str(cfg), str(cfg)]            # repeatable, threaded through
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), f"-c={cfg}"]) == 0
    assert captured["configs"] == [str(cfg)]


@pytest.mark.parametrize("token,hint", [
    ("-config", "Nextflow's `-config` is `--config PATH`"),
    ("-config=x.config", "Nextflow's `-config` is `--config PATH`"),
    ("-cpus", "single-dash options itself")])
def test_attached_short_config_values_are_named_not_split(tmp_path, monkeypatch, capsys, token,
                                                          hint):
    # argparse would read `-config x.config` as `-c onfig` and report the real path as a stray
    # extra argument; the Nextflow spelling is named instead, before anything runs.
    monkeypatch.setattr(orchestration, "run_pipeline", lambda *a, **k: pytest.fail("must not run"))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), token, "x.config"]) == 1
    err = capsys.readouterr().err
    assert hint in err and "onfig" not in err.replace("config", "")


def test_run_passes_through_pipeline_flag_that_prefixes_a_reserved_flag(tmp_path, captured):
    # A pipeline parameter whose name is a prefix of a reserved nfclaw flag (e.g. `--res` vs
    # `--resume`, `--time` vs `--timeout`) must reach the pipeline as an override, not be silently
    # swallowed by argparse abbreviation. Guards the passthrough contract (allow_abbrev=False).
    rc = cli.main(["run", "x", "--outdir", str(tmp_path / "out"),
                   "--res", "5", "--time", "30"])
    assert rc == 0
    assert captured["cli_overrides"] == {"res": "5", "time": "30"}   # forwarded, not misparsed
    assert captured["resume"] is False                               # reserved --resume untouched
    assert captured["timeout_seconds"] is None                       # reserved --timeout untouched


def test_run_threads_allow_spaces(tmp_path, captured):
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--allow-spaces"]) == 0
    assert captured["allow_spaces"] is True
    captured.clear()
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 0
    assert captured["allow_spaces"] is False                  # default off


def test_run_rejects_malformed_nxf_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    rc = cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--nxf-env", "NXF_VER"])
    assert rc == 1
    assert "KEY=VALUE" in capsys.readouterr().err


def test_nxf_env_rejects_invalid_environment_name(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    rc = cli.main(
        ["run", "x", "--outdir", str(tmp_path / "out"), "--nxf-env", "NXF_BAD-NAME=value"])
    assert rc == 1
    assert "invalid environment variable name" in capsys.readouterr().err


def test_timeout_and_engine_version_are_validated(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    for args in (["--timeout", "0"], ["--timeout", "-1"], ["--nxf-ver", "latest"]):
        with pytest.raises(SystemExit) as exc:
            cli.main(["run", "x", "--outdir", str(tmp_path / "out"), *args])
        assert exc.value.code == 2


def test_run_surfaces_advisories_on_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: orchestration.RunResult(
                            "CMD", Path("/o"), True, None, warnings=["inert release warning"]))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 0
    cap = capsys.readouterr()
    assert "CMD" in cap.out                                    # command still on stdout
    assert "warning: inert release warning" in cap.err         # advisory on stderr


# --- dev: the unreleased development branch ---------------------------------------------------

def test_versions_lists_dev_after_every_release(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(versions, "available",
                        lambda name, **k: [("2.0.0", True), ("1.2.0", False)])
    monkeypatch.setattr(versions, "dev_head", lambda name, **k: ("f754e0a247b0" + "0" * 28, True))
    assert cli.main(["versions", "sarek"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("2.0.0\tlatest")  # the first line is still the newest release
    assert lines[-1].startswith("dev\t") and "unreleased" in lines[-1]
    assert "f754e0a247b0" in lines[-1] and "last fetched" not in lines[-1]


def test_versions_marks_an_offline_dev_head_as_last_fetched(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(versions, "available", lambda name, **k: [])
    monkeypatch.setattr(versions, "dev_head", lambda name, **k: ("a" * 40, False))
    assert cli.main(["versions", "sarek"]) == 0
    captured = capsys.readouterr()
    assert "no release" in captured.err.lower()
    assert captured.out.startswith("dev\t") and "last fetched" in captured.out


def test_versions_omits_dev_when_the_pipeline_has_none(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(versions, "available", lambda name, **k: [("2.0.0", True)])
    monkeypatch.setattr(versions, "dev_head", lambda name, **k: (None, True))
    assert cli.main(["versions", "sarek"]) == 0
    assert "dev" not in capsys.readouterr().out


def test_show_dev_prints_generated_docs_and_the_advisory(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    cached = root / "pipelines" / "sarek" / ".versions" / "dev-f754e0a247b0" / "upstream"
    st = SubmoduleStatus("sarek", cached, True, True, "dev", "f754e0a247b0" + "0" * 28, (),
                         notes=("nf-core/sarek@dev is unreleased development code",))
    seen = {}

    def fake_ensure(name, version, **k):
        seen["version"] = version
        return st

    monkeypatch.setattr(versions, "ensure", fake_ensure)

    def fake_generate(status, *, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "skill.md").write_text("# sarek @ dev\n")
        return dest_dir / "skill.md", dest_dir / "reference.md"

    monkeypatch.setattr(versions, "generate_docs", fake_generate)
    assert cli.main(["show", "sarek", "--pipeline-version", "dev"]) == 0
    captured = capsys.readouterr()
    assert seen["version"] == "dev"
    assert "# sarek @ dev" in captured.out
    assert "warning: nf-core/sarek@dev is unreleased" in captured.err


def test_run_threads_dev_with_the_users_exact_flags(tmp_path, monkeypatch, capsys):
    # The command from the feature request: dev + an institutional profile + a pinned engine.
    captured = {}

    def fake_run(*a, **k):
        captured.update(k)
        return orchestration.RunResult("CMD", Path("/o"), True, None,
                                       warnings=["nf-core/fetchngs@dev is unreleased"])

    monkeypatch.setattr(orchestration, "run_pipeline", fake_run)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "fetchngs", "--pipeline-version", "dev", "--input", "ids.csv",
                     "--outdir", str(tmp_path / "fetchngs_all12"), "-profile", "binac2",
                     "--nxf-ver", "25.10.4"]) == 0
    assert captured["pipeline_version"] == "dev"
    assert captured["profile"] == "binac2" and captured["nxf_ver"] == "25.10.4"
    assert captured["cli_overrides"] == {}                     # nothing leaked to the pipeline
    assert "warning: nf-core/fetchngs@dev is unreleased" in capsys.readouterr().err


def test_run_says_warnings_before_launch_and_only_once(tmp_path, monkeypatch, capsys):
    # A dev run can take hours, and a failed one never returns: the advisory must be printed as
    # soon as it is known (before Nextflow starts), not with the result — and not twice.
    def fake_run(*a, on_warning, **k):
        on_warning("nf-core/fetchngs@dev is unreleased")
        raise NfclawError(ErrorCode.EXECUTION_FAILED, "Nextflow execution failed.")

    monkeypatch.setattr(orchestration, "run_pipeline", fake_run)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "fetchngs", "--pipeline-version", "dev",
                     "--outdir", str(tmp_path / "out")]) == 1
    err = capsys.readouterr().err
    assert err.index("warning: nf-core/fetchngs@dev") < err.index("Nextflow execution failed")

    def fake_ok(*a, on_warning, **k):
        on_warning("said early")
        return orchestration.RunResult("CMD", Path("/o"), True, None,
                                       warnings=["said early", "only in result"])

    monkeypatch.setattr(orchestration, "run_pipeline", fake_ok)
    assert cli.main(["run", "fetchngs", "--outdir", str(tmp_path / "out")]) == 0
    err = capsys.readouterr().err
    assert err.count("warning: said early") == 1 and "warning: only in result" in err


def test_output_into_a_closed_pipe_ends_quietly():
    # `nfclaw versions X | head -1` (or `list | grep -m1`) closes the pipe early; the next write
    # used to end the command with a BrokenPipeError traceback on stderr.
    script = (
        "import sys\n"
        "from runner import cli\n"
        "def big(argv):\n"
        "    for i in range(200000):\n"
        "        print(f'line {i}')\n"
        "    return 0\n"
        "cli._main = big\n"
        "sys.exit(cli.main([]))\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=Path(__file__).resolve().parent.parent)
    assert proc.stdout.readline() == b"line 0\n"
    proc.stdout.close()                                    # the reader goes away, like `head -1`
    stderr = proc.stderr.read().decode()
    assert proc.wait(timeout=60) == cli._EXIT_BROKEN_PIPE
    assert "Traceback" not in stderr and "BrokenPipeError" not in stderr, stderr


def test_run_stopped_by_sigterm_exits_cleanly(tmp_path, monkeypatch, capsys):
    # A background run is stopped with `kill`: nfclaw shuts Nextflow down (execution) and exits with
    # the conventional 128+15, naming the run log — not a traceback, and not left running.
    def stopped(*a, **k):
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(5)                                   # the handler interrupts this
        raise AssertionError("SIGTERM was not handled")

    before = signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(orchestration, "run_pipeline", stopped)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 128 + signal.SIGTERM
    err = capsys.readouterr().err
    assert "nfclaw: stopped by SIGTERM" in err and "Traceback" not in err
    assert signal.getsignal(signal.SIGTERM) is before          # handler restored


def test_run_interrupted_by_ctrl_c_exits_cleanly(tmp_path, monkeypatch, capsys):
    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(orchestration, "run_pipeline", interrupted)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 130
    assert "nfclaw: interrupted" in capsys.readouterr().err


# --- nfclaw chain ---------------------------------------------------------------------------

def _chain_spec(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"stages": [{"pipeline": "fetchngs", "input": "/x/ids.csv"},
                                           {"pipeline": "rnaseq"}]}))
    return spec


def test_chain_run_threads_its_flags(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake(spec, **kw):
        seen.update(kw, spec=spec)
        return chain.ChainResult(outdir=kw["outdir"], outcome="success",
                                 stages=[{"index": 1, "id": "fetchngs", "status": "success",
                                          "outdir": str(kw["outdir"] / "01-fetchngs")}],
                                 log_path=tmp_path / "chain.log")

    monkeypatch.setattr(cli.chain, "run_chain", fake)
    assert cli.main(["chain", "run", str(_chain_spec(tmp_path)), "--outdir",
                     str(tmp_path / "o"), "--timeout", "60", "--check", "--resume"]) == 0
    assert seen["timeout_seconds"] == 60 and seen["outdir"] == (tmp_path / "o").resolve()
    assert seen["check_only"] and seen["resume"]
    assert [s.pipeline for s in seen["spec"].stages] == ["fetchngs", "rnaseq"]
    out = capsys.readouterr().out
    assert "chain: success" in out and "01-fetchngs\tsuccess" in out and "log: " in out


def test_chain_check_prints_each_stages_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.chain, "run_chain", lambda spec, **kw: chain.ChainResult(
        outdir=kw["outdir"], outcome="checked", stages=[],
        commands=[("01-fetchngs", "nextflow run a"), ("02-rnaseq", "nextflow run b")]))
    assert cli.main(["chain", "run", str(_chain_spec(tmp_path)), "--outdir",
                     str(tmp_path / "o"), "--check"]) == 0
    out = capsys.readouterr().out
    assert "# 01-fetchngs\nnextflow run a\n# 02-rnaseq\nnextflow run b" in out


def test_chain_resume_may_omit_the_spec(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(cli.chain, "run_chain", lambda spec, **kw: seen.update(spec=spec, **kw)
                        or chain.ChainResult(outdir=kw["outdir"], outcome="success", stages=[]))
    assert cli.main(["chain", "run", "--outdir", str(tmp_path / "o"), "--resume"]) == 0
    assert seen["spec"] is None and seen["resume"]


def test_chain_run_needs_a_spec_unless_resuming(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["chain", "run", "--outdir", str(tmp_path / "o")])


def test_chain_run_rejects_pipeline_flags(tmp_path):
    # Stage parameters belong in the spec; a stray flag must not be silently dropped.
    with pytest.raises(SystemExit):
        cli.main(["chain", "run", str(_chain_spec(tmp_path)), "--outdir", str(tmp_path),
                  "--genome", "GRCh38"])


def test_chain_errors_are_reported_cleanly(tmp_path, capsys):
    bad = tmp_path / "spec.json"
    bad.write_text("{nope")
    assert cli.main(["chain", "run", str(bad), "--outdir", str(tmp_path / "o")]) == 1
    assert "chain spec is not valid JSON" in capsys.readouterr().err


def test_chain_stop_signal_exit_code(tmp_path, monkeypatch, capsys):
    def stopped(*a, **k):
        raise cli.execution.Terminated(signal.SIGTERM)

    monkeypatch.setattr(cli.chain, "run_chain", stopped)
    assert cli.main(["chain", "run", str(_chain_spec(tmp_path)), "--outdir",
                     str(tmp_path / "o")]) == 128 + signal.SIGTERM
    assert "stopped by SIGTERM" in capsys.readouterr().err


def test_chain_edges_lists_the_registry(monkeypatch, capsys, library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): {
        "description": "mini_up writes a mini sheet",
        "params": {"input": {"samplesheet": "s.csv", "provides": ["sample", "fastq_1"]}}}})
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["chain", "edges"]) == 0
    assert capsys.readouterr().out == "mini_up\tmini\tmini_up writes a mini sheet\n"
    assert cli.main(["chain", "edges", "other"]) == 0
    assert capsys.readouterr().out == ""


def test_chain_status_exit_code_reflects_the_lineage(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.chain, "status", lambda p: ({"chain_id": "c", "outcome": "success",
                                                          "stages": []}, ["a broken link"]))
    assert cli.main(["chain", "status", str(tmp_path)]) == 1
    assert "lineage: BROKEN" in capsys.readouterr().out
    monkeypatch.setattr(cli.chain, "status", lambda p: ({"stages": [], "outcome": "success"}, []))
    assert cli.main(["chain", "status", str(tmp_path)]) == 0
    monkeypatch.setattr(cli.chain, "status", lambda p: ({"stages": [], "outcome": "failed at x"},
                                                        []))
    assert cli.main(["chain", "status", str(tmp_path)]) == 1          # as `nfclaw status`


# --- `nfclaw status`: the state of a run, without reading its log ---------------------------------

def _write_run_log(outdir, text):
    log = outdir / "provenance" / "logs" / "run.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text)
    return log


def _finished_block(outcome, body=""):
    return ("==> nfclaw run started 2026-10-06T10:00:00+00:00\n    command: nextflow run x\n"
            f"    host: {socket.gethostname()}\n    pid: 1\n{body}"
            f"==> nfclaw run finished 2026-10-06T10:05:00+00:00: {outcome}\n")


def test_status_of_a_successful_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    log = _write_run_log(tmp_path / "out", _finished_block("success"))
    assert cli.main(["status", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert "status: success" in out and f"log: {log}" in out


def test_status_of_a_failed_run_prints_the_recorded_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    body = ("ERROR ~ x\n==> nfclaw error:\n[execution_failed] Nextflow execution failed "
            "(exit status 1).\n")
    _write_run_log(tmp_path / "out", _finished_block("failed (exit status 1)", body))
    assert cli.main(["status", str(tmp_path / "out")]) == 1
    out = capsys.readouterr().out
    assert "status: failed (exit status 1)" in out
    assert "[execution_failed] Nextflow execution failed (exit status 1)." in out


def test_status_of_a_running_run_exits_3(tmp_path, monkeypatch, capsys, named_process):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    proc = named_process("nfclaw")
    try:
        _write_run_log(tmp_path / "out", "==> nfclaw run started 2026-10-06T10:00:00+00:00\n"
                       f"    host: {socket.gethostname()}\n    pid: {proc.pid}\n"
                       "[ab/cdef12] NFCORE_DEMO:DEMO:FASTQC (S1) | 1 of 2\n")
        assert cli.main(["status", str(tmp_path / "out")]) == 3
    finally:
        proc.kill()
        proc.wait()
    out = capsys.readouterr().out
    assert f"status: running (nfclaw pid {proc.pid}" in out and "FASTQC (S1) | 1 of 2" in out


def test_status_of_a_run_killed_outright(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    proc = subprocess.Popen([sys.executable, "-c", "pass", "nfclaw"])
    proc.wait()
    _write_run_log(tmp_path / "out", "==> nfclaw run started 2026-10-06T10:00:00+00:00\n"
                   f"    host: {socket.gethostname()}\n    pid: {proc.pid}\nlast words\n")
    assert cli.main(["status", str(tmp_path / "out")]) == 1
    out = capsys.readouterr().out
    assert "status: stopped without an outcome" in out and "last words" in out


def test_status_without_a_run_log_says_why(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["status", str(tmp_path / "never")]) == 1
    out = capsys.readouterr().out
    assert "status: no run log" in out and "in the foreground" in out


def test_status_json_is_the_parsed_state_with_the_same_exit_code(tmp_path, monkeypatch, capsys):
    # Agents branch on the outcome without parsing prose: one JSON object on stdout.
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    body = ("ERROR ~ x\n==> nfclaw error:\n[execution_failed] Nextflow execution failed "
            "(exit status 1).\n")
    log = _write_run_log(tmp_path / "out", _finished_block("failed (exit status 1)", body))
    assert cli.main(["status", str(tmp_path / "out"), "--json"]) == 1
    record = json.loads(capsys.readouterr().out)
    assert record["version"] == 1 and record["exit_code"] == 1
    assert (record["state"], record["kind"], record["outcome"]) == (
        "ended", "run", "failed (exit status 1)")
    assert record["started"] == "2026-10-06T10:00:00+00:00"
    assert record["finished"] == "2026-10-06T10:05:00+00:00"
    assert record["log"] == str(log) and record["pid"] == 1
    assert record["error"] == ["[execution_failed] Nextflow execution failed (exit status 1)."]
    assert record["report"].startswith("status: failed (exit status 1)\n")

    _write_run_log(tmp_path / "ok", _finished_block("success"))
    assert cli.main(["status", str(tmp_path / "ok"), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert (record["state"], record["outcome"], record["caveats"]) == ("success", "success", [])

    assert cli.main(["status", str(tmp_path / "never"), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "missing"


def test_chain_status_json_carries_state_problems_and_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.chain, "status", lambda p: ({"chain_id": "c", "outcome": "success",
                                                          "stages": []}, ["a broken link"]))
    assert cli.main(["chain", "status", str(tmp_path), "--json"]) == 1
    record = json.loads(capsys.readouterr().out)
    assert record["exit_code"] == 1 and record["problems"] == ["a broken link"]
    assert record["chain"]["chain_id"] == "c" and "lineage: BROKEN" in record["report"]

    monkeypatch.undo()
    assert cli.main(["chain", "status", str(tmp_path / "none"), "--json"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["error"].startswith("no chain recorded")
    assert "no chain recorded" in captured.err


# --- a refused relaunch must not leave the previous attempt's outcome as the last line -----------

def test_refused_relaunch_is_recorded_in_the_existing_run_log(tmp_path, monkeypatch):
    log = _write_run_log(tmp_path / "out", _finished_block("failed (exit status 1)"))

    def refused(*a, **k):
        raise NfclawError(ErrorCode.ENVIRONMENT, "Preflight checks failed.",
                          details={"issues": ["--outdir is not empty"]})

    monkeypatch.setattr(orchestration, "run_pipeline", refused)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 1
    text = log.read_text()
    assert text.count("==> nfclaw run started") == 2
    assert "--outdir is not empty" in text
    assert text.rstrip().splitlines()[-1].endswith(": refused before launch")


def test_refusal_into_a_fresh_outdir_leaves_it_untouched(tmp_path, monkeypatch):
    def refused(*a, **k):
        raise NfclawError(ErrorCode.PARAMS_INVALID, "Parameters failed validation.")

    monkeypatch.setattr(orchestration, "run_pipeline", refused)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists()


def test_check_never_writes_into_the_run_log(tmp_path, monkeypatch):
    log = _write_run_log(tmp_path / "out", _finished_block("success"))
    before = log.read_text()

    def refused(*a, **k):
        raise NfclawError(ErrorCode.PARAMS_INVALID, "Parameters failed validation.")

    monkeypatch.setattr(orchestration, "run_pipeline", refused)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--check"]) == 1
    assert log.read_text() == before


def test_a_launched_run_is_not_recorded_twice(tmp_path, monkeypatch):
    # The run log already records a failure that happened after launch; cli adds nothing.
    log = _write_run_log(tmp_path / "out", _finished_block("success"))

    def launched_then_failed(*a, **k):
        with log.open("a") as fh:
            fh.write(_finished_block("failed (exit status 1)"))
        raise NfclawError(ErrorCode.EXECUTION_FAILED, "Nextflow execution failed.")

    monkeypatch.setattr(orchestration, "run_pipeline", launched_then_failed)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 1
    assert log.read_text().count("==> nfclaw run started") == 2


def test_status_of_a_chain_outdir_points_at_chain_status(tmp_path, capsys, library):
    log = tmp_path / "c" / "chain" / "logs" / "chain.log"
    log.parent.mkdir(parents=True)
    log.write_text("==> nfclaw chain started 2026-01-01T00:00:00+00:00\n"
                   "    launch dir: /x\n    host: h\n    pid: 1\n"
                   "==> nfclaw chain finished 2026-01-01T01:00:00+00:00: success\n")
    assert cli.main(["status", str(tmp_path / "c")]) == 0
    out = capsys.readouterr().out
    assert "status: success" in out and "nfclaw chain status" in out


@pytest.mark.parametrize("token,hint", [
    ("-resume", "`--resume`"), ("-params-file", "`--params-file`"),
    ("-r", "`--pipeline-version`"), ("-with-tower", "single-dash options itself")])
def test_nextflow_style_single_dash_options_name_the_nfclaw_flag(token, hint):
    with pytest.raises(NfclawError) as exc:
        cli._collect_overrides([token])
    assert hint in exc.value.fix


def test_run_takes_data_files_and_sheet_columns(tmp_path, monkeypatch, capsys):
    # A shell glob expands into several --input values; --sheet-set columns are nfclaw's own,
    # never forwarded to the pipeline as parameters.
    captured = {}
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: captured.update(k) or orchestration.RunResult(
                            "CMD", Path("/o"), True, None,
                            generated_samplesheet=Path("/stage/samplesheet.csv")))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--input", "a_R1.fq.gz",
                     "--input", "a_R2.fq.gz", "--sheet-set", "strandedness=auto", "--sheet-set",
                     "seq_center=", "--genome", "GRCh38", "--check"]) == 0
    assert captured["input_path"] == ["a_R1.fq.gz", "a_R2.fq.gz"]
    assert captured["sheet_set"] == {"strandedness": "auto", "seq_center": ""}
    assert captured["cli_overrides"] == {"genome": "GRCh38"}
    assert "samplesheet: /stage/samplesheet.csv (generated from --input)" in capsys.readouterr().out
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--input", "dir"]) == 0
    assert captured["input_path"] == "dir" and captured["sheet_set"] == {}


def test_a_malformed_sheet_column_is_refused_before_anything_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: pytest.fail("must not run"))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--input", "d",
                     "--sheet-set", "strandedness"]) == 1
    assert "--sheet-set expects COLUMN=VALUE" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_input_before_the_pipeline_name_still_parses(tmp_path, monkeypatch, capsys):
    # Options may precede the pipeline name; an --input value must not swallow it.
    captured = {}
    monkeypatch.setattr(orchestration, "run_pipeline",
                        lambda *a, **k: captured.update(name=a[0], **k) or orchestration.RunResult(
                            "CMD", Path("/o"), True, None))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "--input", "sheet.csv", "rnaseq", "--outdir", str(tmp_path / "o")]) == 0
    assert captured["name"] == "rnaseq" and captured["input_path"] == "sheet.csv"
    # Several data files: --input once per file (or a quoted glob, or their directory).
    assert cli.main(["run", "rnaseq", "--input", "a.fq.gz", "--input", "b.fq.gz",
                     "--outdir", str(tmp_path / "o")]) == 0
    assert captured["input_path"] == ["a.fq.gz", "b.fq.gz"]
    # What an unquoted shell glob expands to is explained, not taken for a pipeline parameter.
    (tmp_path / "b.fq.gz").write_text("x")
    assert cli.main(["run", "rnaseq", "--input", "a.fq.gz", str(tmp_path / "b.fq.gz"),
                     "--outdir", str(tmp_path / "o")]) == 1
    assert "quote the glob" in capsys.readouterr().err


def test_an_odd_extra_token_is_a_clear_error_not_a_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(orchestration, "run_pipeline", lambda *a, **k: pytest.fail("must not run"))
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    for token in ("~nosuchuser_nfclaw/x", "x" * 300):
        assert cli.main(["run", "rnaseq", "--outdir", str(tmp_path / "o"), token]) == 1
        assert "unexpected extra argument" in capsys.readouterr().err


def test_status_of_a_success_names_the_caveats_the_pipeline_reported(tmp_path, monkeypatch, capsys):
    # rnaseq exits 0 after dropping a sample below its trimmed-read threshold; `status: success`
    # alone told an agent every sample had been analysed.
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    body = ("    console format: prefixed\n"
            "| -[nf-core/rnaseq] Pipeline completed successfully with skipped sampl(es)-\n"
            "| -[nf-core/rnaseq] Please check MultiQC report: 1/3 samples skipped since they "
            "failed 10000 trimmed read threshold.-\n")
    _write_run_log(tmp_path / "out", _finished_block("success", body))
    assert cli.main(["status", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("status: success — with caveats the pipeline reported")
    assert "  [nf-core/rnaseq] Please check MultiQC report: 1/3 samples skipped" in out


# --- what the command line says about itself ------------------------------------------------------

def test_version_names_the_package_and_its_checkout_commit(capsys, monkeypatch):
    from runner import version
    monkeypatch.setattr(version, "commit", lambda: "0123456789abcdef" * 2 + "01234567")
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out == f"nfclaw {version.package_version()} (commit 0123456789ab)\n"


def test_version_outside_a_checkout_names_the_package_alone(capsys, monkeypatch):
    from runner import version
    monkeypatch.setattr(version, "commit", lambda: None)
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert capsys.readouterr().out == f"nfclaw {version.package_version()}\n"


def test_a_pipeline_flag_named_version_still_reaches_the_pipeline(captured, tmp_path):
    # `--version` belongs to nfclaw only before a command; after `run` it is a pipeline parameter.
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out"), "--version", "2"]) == 0
    assert captured["cli_overrides"] == {"version": "2"}


def test_every_command_and_run_option_explains_itself():
    parser = cli.build_parser()
    commands = next(a for a in parser._actions if isinstance(a, cli.argparse._SubParsersAction))
    described = {choice.dest for choice in commands._choices_actions}
    assert described == set(commands.choices)
    chain_commands = next(a for a in commands.choices["chain"]._actions
                          if isinstance(a, cli.argparse._SubParsersAction))
    assert {c.dest for c in chain_commands._choices_actions} == set(chain_commands.choices)
    undocumented = [action.dest for action in commands.choices["run"]._actions
                    if not action.help]
    assert undocumented == []


def test_list_searches_the_library_by_keyword(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    (root / "catalog.json").write_text(json.dumps([
        {"name": "rnaseq", "version": "3.0.0", "description": "RNA sequencing analysis",
         "tools": ["STAR", "Salmon"], "input": "FastQ", "summary": ""},
        {"name": "sarek", "version": "3.5.0", "description": "Variant calling",
         "tools": ["GATK"], "input": "FastQ", "summary": "germline and somatic"}]))
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["list", "variant", "calling"]) == 0
    assert capsys.readouterr().out == "sarek\t3.5.0\tVariant calling\n"
    assert cli.main(["list", "salmon"]) == 0
    assert capsys.readouterr().out.startswith("rnaseq\t3.0.0\t")
    assert cli.main(["list", "metagenome"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "No pipeline matches 'metagenome'" in captured.err


def test_list_search_reads_skill_frontmatter_without_a_catalog(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    assert cli.main(["list", "SAREK"]) == 0
    assert capsys.readouterr().out == "sarek\t1.0.0\t\n"


def test_status_and_run_survive_a_log_that_cannot_be_inspected(tmp_path, monkeypatch, capsys,
                                                               captured):
    # Before Python 3.14 `Path.is_file` raises PermissionError under a directory that cannot be
    # searched: `nfclaw status` and `nfclaw run` must report it, not end in a traceback.
    out = tmp_path / "out"
    log = out / "provenance" / "logs" / "run.log"
    original_stat = Path.stat

    def refused(self, *args, **kwargs):
        if self == log:
            raise PermissionError(13, "Permission denied", str(self))
        return original_stat(self, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", refused)
    assert cli.main(["status", str(out)]) == 1
    assert "cannot be read: Permission denied" in capsys.readouterr().out
    assert cli.main(["run", "x", "--outdir", str(out)]) == 0


def test_a_path_nfclaw_cannot_reach_is_a_refusal_not_a_traceback(tmp_path, monkeypatch, capsys):
    # Before Python 3.14 `Path.exists` raises PermissionError under a directory that cannot be
    # searched: `--input /root/x.csv` or `--outdir /root/out` ended in a traceback.
    log = _write_run_log(tmp_path / "out", _finished_block("failed (exit status 1)"))

    def unreachable(*a, **k):
        raise PermissionError(13, "Permission denied", "/root/data/sheet.csv")
    monkeypatch.setattr(orchestration, "run_pipeline", unreachable)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 1
    err = capsys.readouterr().err
    assert "[environment] cannot access /root/data/sheet.csv: Permission denied" in err
    assert "Traceback" not in err
    assert log.read_text().rstrip().splitlines()[-1].endswith(": refused before launch")


def test_any_command_reports_an_unreachable_path_cleanly(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    skill = root / "pipelines" / "sarek" / "skill.md"
    original = Path.read_text

    def refused(self, *args, **kwargs):
        if self == skill:
            raise PermissionError(13, "Permission denied", str(self))
        return original(self, *args, **kwargs)
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(Path, "read_text", refused)
    assert cli.main(["show", "sarek"]) == 1
    err = capsys.readouterr().err
    assert err.startswith(f"[environment] cannot access {skill}: Permission denied")


def test_an_os_error_without_a_path_is_named_as_such(tmp_path, monkeypatch, capsys):
    def full(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(orchestration, "run_pipeline", full)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["run", "x", "--outdir", str(tmp_path / "out")]) == 1
    assert "[environment] operating-system error: No space left on device" in \
        capsys.readouterr().err
