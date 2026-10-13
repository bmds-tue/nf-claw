import os as _os
import socket as _socket
from pathlib import Path

import pytest

from runner import runlog

FIXTURES = Path(__file__).parent / "fixtures" / "nextflow_console"


@pytest.mark.parametrize("payload", [
    b"==> nfclaw run finished 2026-10-09T00:00:00+00:00: success\n",
    b"==> nfclaw replay started 2026-10-09T00:00:00+00:00\n    pid: 1\n",
] + [f"progress{separator}==> nfclaw run finished 2026-10-09T00:00:00+00:00: success\n".encode()
     for separator in ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")])
def test_child_console_cannot_forge_status_controls(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(runlog, "_is_process", lambda *_: True)
    log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    try:
        for byte in payload:  # chunk boundaries must not change the trust boundary
            log.write(bytes([byte]))
        state = runlog.read_state(log.path)
        assert state.state == "running"
        assert state.kind == "run"
        assert state.pid == _os.getpid()
        assert state.outcome is None
        assert payload.decode().strip() in state.console
    finally:
        log.outcome = "failed (exit status 7)"
        log.finish()
    state = runlog.read_state(log.path)
    assert state.state == "ended"
    assert state.outcome == "failed (exit status 7)"


def test_partial_child_line_cannot_hide_the_real_outcome(tmp_path):
    log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    log.write(b"output without a final newline")
    log.outcome = "success"
    log.finish()
    assert runlog.read_state(log.path).state == "success"


def test_multiline_failure_still_ends_with_one_physical_status_line(tmp_path):
    log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    log.fail("failed after Nextflow succeeded (error: first\r\nsecond)", "first\nsecond")
    log.finish()
    state = runlog.read_state(log.path)
    assert state.state == "ended"
    assert state.outcome == "failed after Nextflow succeeded (error: first\\r\\nsecond)"
    assert log.path.read_bytes().split(b"\n")[-2].startswith(b"==> nfclaw run finished")


def test_multiline_header_value_cannot_forge_a_new_attempt(tmp_path):
    log = runlog.RunLog.open(tmp_path, command=["nextflow", "--label",
        "sample\n==> nfclaw replay started 2026-10-09T00:00:00+00:00\n    pid: 1"], launch_dir=tmp_path)
    log.outcome = "success"
    log.finish()
    state = runlog.read_state(log.path)
    assert state.kind == "run"
    assert state.pid == _os.getpid()


def test_relaunch_after_an_unterminated_console_line_keeps_its_own_header(tmp_path):
    (tmp_path / "run.log").write_text("==> nfclaw run started old\n    pid: 123\n| unfinished")
    log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    log.outcome = "success"
    log.finish()
    state = runlog.read_state(log.path)
    assert state.pid == _os.getpid()
    assert state.state == "success"


def test_executed_engine_version_survives_split_colored_chunks_and_large_console_output(tmp_path):
    log = runlog.RunLog(tmp_path / "run.log")
    try:
        log.write(b"\x1b[32mN E X T F L O W  ~  version 25.1")
        assert log.nextflow_version is None
        log.write(b"0.4\x1b[0m\n")
        log.write(b"analysis output\n" * 30000)
        log.write(b"N E X T F L O W  ~  version 26.04.0\n")
        assert log.nextflow_version == "nextflow version 25.10.4"
    finally:
        log.finish()


def test_executed_engine_witness_handles_cold_launcher_carriage_return_redraw(tmp_path):
    log = runlog.RunLog(tmp_path / "run.log")
    try:
        log.write(b"Downloading nextflow dependencies. Please wait .. \r\x1b[")
        log.write(b"KN E X T F L O W  ~  version 26.04.0\n")
        assert log.nextflow_version == "nextflow version 26.04.0"
    finally:
        log.finish()


def _console(name: str) -> str:
    # Real console output captured from Nextflow 26.04.3 (stdout of `nextflow run`, not a TTY).
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- where Nextflow writes its own log ------------------------------------------------------------

def test_nextflow_log_defaults_to_the_launch_dir(monkeypatch):
    # nfclaw launches Nextflow from --outdir, and Nextflow writes `.nextflow.log` into its launch
    # directory — not into the caller's cwd, which is where its relative "Check '.nextflow.log'" hint
    # sends an agent looking.
    monkeypatch.delenv("NXF_LOG_FILE", raising=False)
    assert runlog.nextflow_log_path(Path("/runs/out")) == Path("/runs/out/.nextflow.log")


def test_nextflow_log_honours_a_relative_nxf_log_file_against_the_launch_dir(monkeypatch):
    monkeypatch.setenv("NXF_LOG_FILE", "logs/nf.log")
    assert runlog.nextflow_log_path(Path("/runs/out")) == Path("/runs/out/logs/nf.log")


def test_nextflow_log_overlay_wins_over_the_shell(monkeypatch):
    monkeypatch.setenv("NXF_LOG_FILE", "shell.log")
    got = runlog.nextflow_log_path(Path("/runs/out"), {"NXF_LOG_FILE": "/abs/overlay.log"})
    assert got == Path("/abs/overlay.log")


# --- quoting Nextflow's own error report ----------------------------------------------------------

def test_excerpt_of_a_task_failure_is_the_last_error_report_once():
    # Nextflow 26.04 prints the report twice when stdout is not a TTY; quote it once, in full.
    excerpt = "\n".join(runlog.error_excerpt(_console("task_failure.txt")))
    assert excerpt.count("ERROR ~ Error executing process > 'BOOM'") == 1
    assert "the real task error: samtools could not open input.bam" in excerpt
    assert "Work dir:" in excerpt
    assert "BOOM | 0 of 1" in excerpt                    # the progress line naming the failed step


def test_excerpt_of_an_nf_core_failure_quotes_each_distinct_report_once():
    # Real nf-core/demo 1.2.0 console (corrupt FASTQ): Nextflow renders the process report three
    # times, and the nf-core template then adds its generic "ERROR ~ Pipeline failed" report — which
    # is the *last* `ERROR ~` line but not the cause. Each distinct report is quoted once, in order.
    excerpt = runlog.error_excerpt(_console("nfcore_task_failure.txt"))
    text = "\n".join(excerpt)
    assert text.count("ERROR ~ Error executing process > 'NFCORE_DEMO:DEMO:FASTQC (BROKEN)'") == 1
    assert text.count("ERROR ~ Pipeline failed.") == 1
    assert text.index("Error executing process") < text.index("Pipeline failed.")
    assert "java.util.zip.ZipException: Not in GZIP format" in text      # the tool's own error
    assert "Work dir:" in text
    assert len(excerpt) <= 50
    assert runlog.failing_task_dir(excerpt) == Path(
        "/mnt/volume/drafts/draft-7/nf-claw/work/67/506aabdbd84ecedb67949041e7e5f2")


def test_excerpt_keeps_the_detail_nextflow_prints_before_its_error_line():
    # A config/script syntax error is described *above* `ERROR ~ Config parsing failed`.
    excerpt = "\n".join(runlog.error_excerpt(_console("config_parse_error.txt")))
    assert "Error bad.config:3:1: Unexpected input: '}'" in excerpt
    assert "ERROR ~ Config parsing failed" in excerpt
    assert "N E X T F L O W" not in excerpt              # the banner is not part of the error


def test_excerpt_without_an_error_marker_is_the_console_tail():
    # `error "..."` in a workflow body prints just the message — no `ERROR ~` prefix.
    excerpt = runlog.error_excerpt(_console("workflow_error.txt"))
    assert excerpt[-1] == "pipeline-level failure: missing --fasta"


def test_excerpt_strips_terminal_control_sequences():
    console = ("\x1b[0;35m[nf-core/demo]\x1b[0m starting\n"
               "progress 10%\rprogress 100%\r\n"
               "ERROR ~ \x1b[31mboom\x1b[0m\n")
    excerpt = runlog.error_excerpt(console)
    assert "ERROR ~ boom" in excerpt
    assert "progress 100%" in excerpt and not any("10%" in line for line in excerpt)
    assert not any("\x1b" in line or "\r" in line for line in excerpt)


def test_a_long_error_report_is_capped_but_keeps_its_head_and_tail():
    body = [f"  line {i}" for i in range(200)]
    console = "\n".join(["ERROR ~ Error executing process > 'BIG'", "Caused by:", *body,
                         "Work dir:", "  /w/ab/cdef"]) + "\n"
    excerpt = runlog.error_excerpt(console)
    assert len(excerpt) <= 50
    assert excerpt[0] == "ERROR ~ Error executing process > 'BIG'"
    assert excerpt[-2:] == ["Work dir:", "  /w/ab/cdef"]
    assert any("lines omitted" in line for line in excerpt)


def test_empty_console_gives_an_empty_excerpt():
    assert runlog.error_excerpt("") == []


# --- the failing task ----------------------------------------------------------------------------

def test_failing_task_dir_is_read_from_the_report():
    excerpt = runlog.error_excerpt(_console("task_failure.txt"))
    assert runlog.failing_task_dir(excerpt) == Path(
        "/mnt/volume/drafts/draft-7/probe/l1/work/ca/546a82c2be33e7d21e7983b988f1e9")


def test_no_failing_task_dir_when_the_report_names_none():
    assert runlog.failing_task_dir(runlog.error_excerpt(_console("config_parse_error.txt"))) is None


# --- the underlying cause, from Nextflow's own log -----------------------------------------------

def test_log_causes_quote_the_exception_chain_of_the_last_error():
    # Real .nextflow.log of a run whose host cannot reach GitHub: the console only says "Unable to
    # parse config file"; the reason exists nowhere but in the log's exception chain.
    causes = runlog.nextflow_log_causes(FIXTURES / "nextflow_log_config_unreachable.log")
    assert causes == [
        "Caused by: java.io.IOException: Cannot read config file include: "
        "https://raw.githubusercontent.com/nf-core/configs/master/nfcore_custom.config",
        "Caused by: java.net.SocketException: Network is unreachable",
    ]


def test_log_causes_are_empty_for_a_task_failure_report(tmp_path):
    # A failed task's entry repeats the console report; its bare "Caused by:" heading is not a cause.
    log = tmp_path / ".nextflow.log"
    log.write_text(
        "Oct-05 21:42:15.651 [TaskFinalizer-1] ERROR nextflow.processor.TaskProcessor - "
        "Error executing process > 'BOOM'\n\nCaused by:\n"
        "  Process `BOOM` terminated with an error exit status (3)\n\n"
        "Oct-05 21:42:15.663 [TaskFinalizer-1] DEBUG nextflow.Session - Session aborted\n")
    assert runlog.nextflow_log_causes(log) == []


def test_log_causes_ignore_exceptions_outside_the_last_error_entry(tmp_path):
    log = tmp_path / ".nextflow.log"
    log.write_text(
        "Oct-05 10:00:00.000 [main] WARN  nextflow.Foo - retrying\n"
        "Caused by: java.net.SocketTimeoutException: earlier, recovered\n"
        "Oct-05 10:00:01.000 [main] ERROR nextflow.cli.Launcher - boom\n"
        "Caused by: java.lang.IllegalStateException: the real one\n"
        "\tat x.y(Z.java:1)\n"
        "Oct-05 10:00:02.000 [main] DEBUG nextflow.Session - after\n"
        "Caused by: java.lang.RuntimeException: after the error entry\n")
    assert runlog.nextflow_log_causes(log) == [
        "Caused by: java.lang.IllegalStateException: the real one"]


def test_log_causes_of_a_missing_log_are_empty(tmp_path):
    assert runlog.nextflow_log_causes(tmp_path / "absent.log") == []


def test_log_causes_keep_a_multi_line_exception_message(tmp_path):
    # Real shape (Nextflow 26.04, a config syntax error): the message continues on the lines after
    # "startup failed:" and stops where the stack frames begin.
    log = tmp_path / ".nextflow.log"
    log.write_text(
        "Oct-05 22:03:47.926 [main] ERROR nextflow.cli.Launcher - Config parsing failed\n"
        "nextflow.exception.ConfigParseException: Config parsing failed\n"
        "\tat nextflow.config.ConfigBuilder.build(ConfigBuilder.groovy:821)\n"
        "Caused by: org.codehaus.groovy.control.MultipleCompilationErrorsException: startup failed:\n"
        "_nf_config_ffa03b8917b73ec2: 3: Unexpected input: '}' @ line 3, column 1.\n"
        "   }\n"
        "   ^\n"
        "\n"
        "1 error\n"
        "\n"
        "\tat org.codehaus.groovy.control.ErrorCollector.failIfErrors(ErrorCollector.java:292)\n"
        "\t... 9 common frames omitted\n")
    assert runlog.nextflow_log_causes(log) == [
        "Caused by: org.codehaus.groovy.control.MultipleCompilationErrorsException: startup failed:",
        "  _nf_config_ffa03b8917b73ec2: 3: Unexpected input: '}' @ line 3, column 1.",
        "     }",
        "     ^",
        "  1 error",
    ]


def test_log_causes_are_quoted_once(tmp_path):
    log = tmp_path / ".nextflow.log"
    log.write_text(
        "Oct-05 10:00:01.000 [main] ERROR nextflow.cli.Launcher - boom\n"
        "Caused by: java.net.SocketException: Network is unreachable\n"
        "\tat x.y(Z.java:1)\n"
        "Caused by: java.net.SocketException: Network is unreachable\n"
        "\tat x.y(Z.java:1)\n")
    assert runlog.nextflow_log_causes(log) == [
        "Caused by: java.net.SocketException: Network is unreachable"]


# --- stderr: where nf-schema puts its validation details -----------------------------------------

def test_nf_schema_details_are_quoted_from_stderr():
    # Real nf-core/demo 1.2.0 run with an invalid enum: stdout only says "Validation of pipeline
    # parameters failed!"; *which* value is invalid is written to stderr.
    excerpt = runlog.stderr_excerpt(_console("nfschema_validation.stderr.txt"))
    text = "\n".join(excerpt)
    assert "* --publish_dir_mode (bogus): Expected any of" in text
    assert "is available - Please consider updating" not in text      # launcher chatter dropped


def test_stderr_with_only_the_update_notice_has_nothing_to_quote():
    assert runlog.stderr_excerpt(
        "Nextflow 26.04.6 is available - Please consider updating your version to it\n") == []


def test_context_above_an_error_is_only_the_paragraph_directly_above_it():
    # nf-core prints its citation block before a validation error; only the paragraph adjacent to
    # the error line is quoted, never the run's banner or parameter summary.
    excerpt = runlog.error_excerpt(_console("nfschema_validation.stdout.txt"))
    assert excerpt[-3:] == ["ERROR ~ Validation of pipeline parameters failed!", "",
                            " -- Check '.nextflow.log' file for details"]
    assert len(excerpt) <= 6
    assert not any("zenodo" in line or "userName" in line for line in excerpt)


def test_without_a_report_the_console_tail_is_optional():
    console = _console("workflow_error.txt")
    assert runlog.error_excerpt(console, tail_if_no_report=False) == []
    assert runlog.error_excerpt(console)[-1] == "pipeline-level failure: missing --fasta"


def test_without_a_report_the_quote_is_the_last_paragraph_not_the_parameter_summary():
    # Real nf-core/sarek 3.10.0: the pipeline's own `error(...)` prints its message — no `ERROR ~`
    # prefix — right after nf-core's parameter summary and citations, which are not the error.
    excerpt = runlog.error_excerpt(_console("sarek_workflow_error.stdout.txt"))
    assert excerpt == [
        "Base quality score recalibration requires at least one resource file. Please provide at "
        "least one of `--dbsnp` or `--known_indels`",
        "You can skip this step in the workflow by adding `--skip_tools baserecalibrator` to the "
        "command.",
    ]


def test_last_paragraph_fallback_reaches_above_a_trailing_check_line():
    console = (" N E X T F L O W   ~  version 26.04.3\n\nparams summary\n\n"
               "* --genome (GRCh99): not a known genome\n\n"
               " -- Check script 'main.nf' at line: 68 or see '.nextflow.log' file for more details\n")
    excerpt = runlog.error_excerpt(console)
    assert excerpt[0] == "* --genome (GRCh99): not a known genome"
    assert excerpt[-1].startswith(" -- Check script 'main.nf'")


# --- the state of a run, read from its log alone (`nfclaw status`) -------------------------------

def _block(*, pid, host=None, body="", end=None, kind="run", nextflow_pid=None):
    if host is None:
        host = _socket.gethostname()
    lines = [f"==> nfclaw {kind} started 2026-10-06T10:00:00+00:00", "    command: nextflow run x",
             f"    host: {host}", f"    pid: {pid}"]
    if nextflow_pid is not None:
        lines.append(f"    nextflow pid: {nextflow_pid}")
    lines.append(body)
    if end is not None:
        lines.append(f"==> nfclaw {kind} finished 2026-10-06T10:05:00+00:00: {end}")
    return "\n".join(lines) + "\n"


def _log(tmp_path, text):
    path = tmp_path / "run.log"
    path.write_text(text)
    return path


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_state_of_a_successful_run(tmp_path, newline):
    text = _block(pid=1, body="N E X T F L O W", end="success").replace("\n", newline)
    st = runlog.read_state(_log(tmp_path, text))
    assert st.state == "success" and st.outcome == "success"
    assert st.finished == "2026-10-06T10:05:00+00:00"


def test_state_of_a_failed_run_carries_the_recorded_error(tmp_path):
    body = "ERROR ~ boom\n==> nfclaw error:\n[execution_failed] Nextflow failed.\n  run_log: /x"
    st = runlog.read_state(_log(tmp_path, _block(pid=1, body=body, end="failed (exit status 1)")))
    assert st.state == "ended" and st.outcome == "failed (exit status 1)"
    assert st.error == ["[execution_failed] Nextflow failed.", "  run_log: /x"]


def test_state_is_that_of_the_last_launch(tmp_path):
    text = _block(pid=1, end="failed (exit status 1)") + _block(pid=2, end="success")
    assert runlog.read_state(_log(tmp_path, text)).state == "success"


def test_a_run_whose_nfclaw_is_alive_is_running(tmp_path, named_process):
    proc = named_process("nfclaw")
    try:
        body = "executor >  local (3)\n[ab/cdef12] NFCORE_DEMO:DEMO:FASTQC (S1) | 1 of 2"
        st = runlog.read_state(_log(tmp_path, _block(pid=proc.pid, body=body)))
    finally:
        proc.kill()
        proc.wait()
    assert st.state == "running" and st.pid == proc.pid
    assert st.last_output[-1] == "[ab/cdef12] NFCORE_DEMO:DEMO:FASTQC (S1) | 1 of 2"


def test_a_run_whose_nfclaw_is_gone_stopped_without_an_outcome(tmp_path, named_process):
    # kill -9, out of memory, a restart: nfclaw never wrote the last line and is not running.
    proc = named_process("nfclaw")
    proc.kill()
    proc.wait()
    st = runlog.read_state(_log(tmp_path, _block(pid=proc.pid, body="ERROR ~ half a report")))
    assert st.state == "dead"


def test_a_reused_pid_is_not_mistaken_for_the_run(tmp_path):
    # After a restart the recorded pid can belong to an unrelated process: that is not the run.
    st = runlog.read_state(_log(tmp_path, _block(pid=_os.getpid())))
    assert st.state == "dead"


def test_a_dead_run_reports_a_nextflow_still_running(tmp_path, named_process):
    gone = named_process("nfclaw")
    gone.kill()
    gone.wait()
    nextflow = named_process("nextflow")
    try:
        st = runlog.read_state(_log(tmp_path, _block(pid=gone.pid, nextflow_pid=nextflow.pid)))
        assert st.state == "dead" and st.nextflow_pid == nextflow.pid and st.nextflow_alive
    finally:
        nextflow.kill()
        nextflow.wait()


def test_dead_replay_reports_its_supervisor_without_claiming_its_pid_is_nextflow(
        tmp_path, named_process):
    from runner import cli
    gone = named_process("commands.sh")
    gone.kill()
    gone.wait()
    supervisor = named_process("replay_guard.py")
    try:
        text = _block(pid=gone.pid, kind="replay").replace(
            f"    pid: {gone.pid}\n", f"    pid: {gone.pid}\n    replay supervisor pid: {supervisor.pid}\n")
        state = runlog.read_state(_log(tmp_path, text))
        assert state.state == "dead" and state.supervisor_alive
        assert state.supervisor_pid == supervisor.pid
        assert state.nextflow_pid is None and not state.nextflow_alive
        message = cli._status_report(state)
        assert f"Replay supervisor (pid {supervisor.pid})" in message
        assert f"kill {supervisor.pid}" in message
        assert f"Nextflow (pid {supervisor.pid})" not in message
    finally:
        supervisor.kill()
        supervisor.wait()


def test_an_unfinished_run_on_another_host_is_not_judged_here(tmp_path):
    st = runlog.read_state(_log(tmp_path, _block(pid=1, host="some-other-node")))
    assert st.state == "elsewhere" and st.host == "some-other-node"


def test_matching_host_identity_survives_a_hostname_change(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "host_identity", lambda: "a" * 64, raising=False)
    monkeypatch.setattr(runlog.socket, "gethostname", lambda: "new-hostname")
    monkeypatch.setattr(runlog, "_is_process", lambda pid, names: pid == 123)
    text = _block(pid=123, host="old-hostname").replace(
        "    host: old-hostname\n", "    host: old-hostname\n    host id: " + "a" * 64 + "\n")
    assert runlog.read_state(_log(tmp_path, text)).state == "running"


def test_matching_hostname_does_not_override_a_different_host_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "host_identity", lambda: "a" * 64, raising=False)
    monkeypatch.setattr(runlog, "_is_process", lambda pid, names: True)
    text = _block(pid=123).replace("    pid: 123\n", "    host id: " + "b" * 64 + "\n    pid: 123\n")
    assert runlog.read_state(_log(tmp_path, text)).state == "elsewhere"


def test_foreign_host_pids_are_not_probed_in_the_local_namespace(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "host_identity", lambda: "a" * 64)
    calls = []
    monkeypatch.setattr(runlog, "_is_process", lambda pid, names: calls.append(pid) or True)
    text = _block(pid=123, nextflow_pid=456).replace(
        "    pid: 123\n", "    host id: " + "b" * 64 + "\n    pid: 123\n")
    state = runlog.read_state(_log(tmp_path, text))
    assert calls == []
    assert state.state == "elsewhere" and state.nextflow_alive is False


def test_a_finished_run_is_final_on_any_host(tmp_path):
    st = runlog.read_state(_log(tmp_path, _block(pid=1, host="some-other-node", end="success")))
    assert st.state == "success"


def test_a_replay_log_is_read_the_same_way(tmp_path, named_process):
    proc = named_process("commands.sh")
    try:
        st = runlog.read_state(_log(tmp_path, _block(pid=proc.pid, kind="replay")))
    finally:
        proc.kill()
        proc.wait()
    assert st.kind == "replay" and st.state == "running"


def test_state_without_a_run_log(tmp_path):
    st = runlog.read_state(tmp_path / "provenance" / "logs" / "run.log")
    assert st.state == "missing"


def test_causes_are_read_from_a_log_in_any_jvm_locale(tmp_path):
    # A real `.nextflow.log` from Nextflow 25.10.4 under a Spanish JVM locale: its entries start
    # `oct-12 …`, not `Oct-12 …`. The English-only pattern found no entry, so the `Caused by:` chain
    # — here the only place the reason is written — was silently dropped from the error.
    log = Path(__file__).parent / "fixtures" / "nextflow_logs" / "config-include-refused.es.log"
    assert runlog.nextflow_log_causes(log) == ["Caused by: java.net.ConnectException: Connection refused"]
    german = tmp_path / "de.log"
    german.write_text(log.read_text(encoding="utf-8").replace("oct-12 ", "Okt.-12 "), encoding="utf-8")
    assert runlog.nextflow_log_causes(german) == ["Caused by: java.net.ConnectException: Connection refused"]


# What nf-core/rnaseq 3.27.0 printed at the end of a real run that dropped a sample (with colours).
_RNASEQ_SKIPPED = (
    "\x1b[0;35m[nf-core/rnaseq]\x1b[0m done\n"
    "-\x1b[0;35m[nf-core/rnaseq]\x1b[0;33m Pipeline completed successfully with skipped sampl(es)"
    "\x1b[0m-\n"
    "-\x1b[0;35m[nf-core/rnaseq]\x1b[0;31m Please check MultiQC report: 1/3 samples skipped since "
    "they failed 10000 trimmed read threshold.\x1b[0m-\n"
    "-\x1b[0;35m[nf-core/rnaseq]\x1b[0;31m Please check MultiQC report: 2/2 samples failed "
    "strandedness check.\x1b[0m-\n")


def test_completion_caveats_quote_what_a_successful_pipeline_left_out(tmp_path):
    assert runlog.completion_caveats(_RNASEQ_SKIPPED) == [
        "[nf-core/rnaseq] Pipeline completed successfully with skipped sampl(es)",
        "[nf-core/rnaseq] Please check MultiQC report: 1/3 samples skipped since they failed "
        "10000 trimmed read threshold.",
        "[nf-core/rnaseq] Please check MultiQC report: 2/2 samples failed strandedness check."]
    # The nf-core template's own qualifier: failed tasks whose errors were ignored.
    template = "-[nf-core/demo] Pipeline completed successfully, but with errored process(es) -\n"
    assert runlog.completion_caveats(template) == [
        "[nf-core/demo] Pipeline completed successfully, but with errored process(es)"]
    # A plain success carries no caveat, and console text cannot pose as a summary line of
    # another pipeline after it.
    plain = "-[nf-core/demo] Pipeline completed successfully-\n-[other] Please check this-\n"
    assert runlog.completion_caveats(plain) == []


def test_completion_caveats_count_ignored_task_failures_from_the_nextflow_log(tmp_path):
    log = tmp_path / ".nextflow.log"
    stats = ("Oct-13 12:15:14.586 [main] DEBUG n.trace.WorkflowStatsObserver - Workflow completed > "
             "WorkflowStats[succeededCount=85; failedCount={f}; ignoredCount={i}; cachedCount=0]\n")
    log.write_text(stats.format(f=0, i=0))
    assert runlog.completion_caveats("", log) == []
    log.write_text(stats.format(f=2, i=2))
    assert runlog.completion_caveats("", log) == [
        "Nextflow ignored 2 failed task(s) (errorStrategy 'ignore'); their results are missing"]
    assert runlog.completion_caveats("", tmp_path / "absent.log") == []
