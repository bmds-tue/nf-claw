from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path

from runner import (chain, discovery, execution, handoff, nextflow_command, orchestration,
                    resources, runlog, sheetgen, verify, versions)
from runner.errors import ErrorCode, NfclawError


def _repo_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    if not (root / "pipelines").is_dir():
        raise NfclawError(
            ErrorCode.ENVIRONMENT,
            "nf-claw repository content was not found next to the installed package.",
            fix="Run from a cloned nf-claw repository and install it with `pip install -e .`.",
        )
    return root


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _nxf_version(raw: str) -> str:
    try:
        return resources.check_nxf_version(raw)
    except NfclawError as exc:
        raise argparse.ArgumentTypeError(exc.message) from None


def _collect_overrides(extras: list[str]) -> dict:
    out: dict = {}
    i = 0
    while i < len(extras):
        tok = extras[i]
        if tok.startswith("--"):
            body = tok[2:]
            if "=" in body:                                   # --key=value (one token)
                key, _, val = body.partition("=")
                out[key.replace("-", "_")] = val
                i += 1
                continue
            key = body.replace("-", "_")
            if i + 1 < len(extras) and not extras[i + 1].startswith("--"):
                out[key] = extras[i + 1]                       # --key value (two tokens)
                i += 2
            else:
                out[key] = True                               # --flag (boolean)
                i += 1
        else:
            # Nextflow's own single-dash options (-resume, -params-file, -work-dir, …) are set by
            # nfclaw; say which nfclaw flag covers them instead of a bare "unexpected argument".
            nextflow = {"-resume": "--resume", "-params-file": "--params-file",
                        "-config": "--config", "-r": "--pipeline-version",
                        "-revision": "--pipeline-version",
                        "-work-dir": "--nxf-env NXF_WORK=<dir>", "-w": "--nxf-env NXF_WORK=<dir>"}
            name = tok.split("=", 1)[0]
            hint = (f" Nextflow's `{name}` is `{nextflow[name]}` for nfclaw." if name in nextflow
                    else " nfclaw sets Nextflow's own single-dash options itself."
                    if tok.startswith("-") and not tok.startswith("--")
                    # What an unquoted glob expands to: several data files after one --input.
                    else " For several --input data files, quote the glob (--input "
                         "'/data/*.fastq.gz'), pass their directory, or repeat --input."
                    if _existing_path(tok) else "")
            raise NfclawError(
                ErrorCode.PARAMS_INVALID,
                f"unexpected extra argument: {tok!r}",
                fix="Pipeline parameters must be passed as --param value or --param=value." + hint,
            )
    return out


def _existing_path(token: str) -> bool:
    """Whether a stray token names an existing file (what an unquoted glob expands to)."""
    try:
        return Path(token).expanduser().exists()
    except (OSError, RuntimeError, ValueError):            # ~unknownuser, an over-long name
        return False


def _stop_words(exc: BaseException) -> str:
    return f"stopped by {exc.name}" if isinstance(exc, execution.Terminated) else "interrupted"


def _stopped(exc: BaseException, log: Path) -> int:
    """Say that a stop signal (or Ctrl-C) ended the run, and return the shell's exit status for it."""
    print(f"nfclaw: {_stop_words(exc)}; any Nextflow run it had started was shut down."
          + (f" Log: {log}" if log.is_file() else ""), file=sys.stderr)
    return 128 + exc.signum if isinstance(exc, execution.Terminated) else 130


def _chain(args: argparse.Namespace, parser: argparse.ArgumentParser, root: Path, warn) -> int:
    if args.chain_cmd == "edges":
        try:
            rules = handoff.load_registry(root)
        except NfclawError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        for (up, down), rule in sorted(rules.items()):
            if args.name in (None, up, down):
                print(f"{up}\t{down}\t{rule.description}")
        return 0
    if args.chain_cmd == "status":
        try:
            state, problems = (chain.status(Path(args.outdir), quick=True) if args.quick
                               else chain.status(Path(args.outdir)))
        except NfclawError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(chain.format_status(state, problems), end="")
        return chain.status_exit_code(state, problems)
    if args.spec is None and not args.resume:
        parser.error("chain run needs a spec file (or --resume an existing chain)")
    outdir = Path(args.outdir).expanduser().resolve()
    try:
        spec = chain.load_spec(Path(args.spec).expanduser()) if args.spec else None
        # As for `run`: `kill` or a closing terminal stop the running stage the way Ctrl-C does.
        with execution.stop_on_signals():
            res = chain.run_chain(spec, repo_root=root, outdir=outdir, check_only=args.check,
                                  resume=args.resume, timeout_seconds=args.timeout,
                                  on_warning=warn)
    except NfclawError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (execution.Terminated, KeyboardInterrupt) as exc:
        return _stopped(exc, outdir / chain.RECORD_DIRNAME / "logs" / chain.LOG_NAME)
    for dirname, command in res.commands:                     # --check
        print(f"# {dirname}\n{command}")
    print(f"chain: {res.outcome} — {outdir}")
    for s in res.stages:
        print(f"  {s['index']:02d}-{s['id']}\t{s['status']}\t{s['outdir']}")
    if res.log_path is not None:
        print(f"log: {res.log_path}")
    return 0


# What a shell reports for a command killed by SIGPIPE (128 + 13).
_EXIT_BROKEN_PIPE = 141


def _run_log_path(outdir: str) -> Path:
    return Path(outdir).expanduser().resolve() / "provenance" / "logs" / runlog.RUN_LOG_NAME


def _status_report(st: runlog.RunState) -> str:
    """`nfclaw status` output: the state first, then where to look and what the run last said."""
    who = "the replay (commands.sh)" if st.kind == "replay" else "nfclaw"
    lines: list[str] = []
    if st.state == "missing":
        return (f"status: no run log — {st.log} does not exist.\n"
                "nfclaw has not launched a run into this --outdir. A run it refuses before launching "
                "(invalid parameters or samplesheet, a failed preflight check) leaves a fresh "
                "--outdir untouched: run the same command in the foreground to see why.\n")
    if st.state == "success":
        lines.append("status: success" + (" — with caveats the pipeline reported about its results"
                                          if st.caveats else ""))
        if st.caveats:
            lines += ["caveats (as reported; results may be incomplete):",
                      *(f"  {caveat}" for caveat in st.caveats)]
    elif st.state == "ended":
        lines.append(f"status: {st.outcome}")
    elif st.state == "running":
        lines.append(f"status: running ({who} pid {st.pid} on {st.host}, started {st.started})")
    elif st.state == "elsewhere":
        lines.append(f"status: unknown here — launched on {st.host} and not finished; "
                     "run `nfclaw status` there")
    else:
        lines.append(f"status: stopped without an outcome — {who} (pid {st.pid}) is no longer "
                     "running and never recorded how the run ended: it was killed with SIGKILL, "
                     "ran out of memory, its disk filled up, or the machine restarted")
    times = f"started: {st.started}" + (f" · finished: {st.finished}" if st.finished else "")
    lines += [times, f"log: {st.log}"]
    if st.nextflow_log:
        lines.append(f"nextflow log: {st.nextflow_log}")
    if st.state in ("dead", "elsewhere") and st.nextflow_alive:
        lines.append(f"Nextflow (pid {st.nextflow_pid}) is still running — stop it with: "
                     f"kill {st.nextflow_pid}")
    if st.state == "dead" and st.supervisor_alive:
        lines.append(f"Replay supervisor (pid {st.supervisor_pid}) is still running — "
                     f"stop its command and tasks with: kill {st.supervisor_pid}")
    if st.state == "running":
        lines += ["last output:", *(f"  {line}" for line in st.last_output)]
    elif st.state != "success":
        if st.error:
            lines += ["error (as recorded):", *(f"  {line}" for line in st.error)]
        else:
            quoted = runlog.error_excerpt(st.console)
            lines += ["last output:", *(f"  {line}" if line else "" for line in quoted)]
        if st.state == "dead":
            lines.append("Re-run the same command with --resume to continue where it stopped.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run one nfclaw command. Output piped into a reader that stops early (`nfclaw versions X |
    head -1`, `nfclaw list | grep -m1 rna`) ends the command quietly, as it would a Unix tool, rather
    than with a BrokenPipeError traceback. SIGPIPE itself stays ignored (Python's default): a run
    whose terminal goes away must keep tearing down Nextflow and writing its provenance, not die."""
    try:
        code = _main(argv)
        sys.stdout.flush()                    # surface a closed pipe here, not at interpreter exit
        return code
    except BrokenPipeError:
        # Point stdout at /dev/null so the interpreter's own final flush cannot raise again.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)
        return _EXIT_BROKEN_PIPE


def build_parser() -> argparse.ArgumentParser:
    """The `nfclaw` command line. One definition, shared by the CLI and the MCP server — which reads
    `run`'s own option names from it, so a pipeline parameter can never shadow one."""
    parser = argparse.ArgumentParser(prog="nfclaw")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_show = sub.add_parser("show")
    p_show.add_argument("name")
    p_show.add_argument("--pipeline-version", dest="pipeline_version")
    p_versions = sub.add_parser("versions")
    p_versions.add_argument("name")
    # The state of a run from its log alone — running, finished and how, or stopped without an
    # outcome (nfclaw killed outright) — so nobody has to read or interpret the log to know.
    p_status = sub.add_parser("status")
    p_status.add_argument("outdir", help="--outdir of the run (or replay target) to report on")
    # Compare a replay against the run it reproduces. Keyed on path, because comparing the raw
    # `outputs.sha256` lines counts one changed file as both a missing and an extra one.
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("replay", help="--outdir of the replayed run")
    p_verify.add_argument("--against", dest="against", required=True,
                          help="--outdir of the original run it should reproduce")
    p_verify.add_argument("--strict", action="store_true",
                          help="also fail when any output bytes or recorded link identities "
                               "differ, or when the runs' recorded execution environments (container "
                               "images, plugins, staged remote inputs) do not match; inspect "
                               "timestamped reports separately from analytical results")
    # Several pipelines in sequence, each started only after the previous one succeeded, with its
    # inputs prepared from that one's outputs (runner.chain; rules in handoffs/).
    p_chain = sub.add_parser("chain")
    chain_sub = p_chain.add_subparsers(dest="chain_cmd", required=True)
    pc_run = chain_sub.add_parser("run", allow_abbrev=False)
    pc_run.add_argument("spec", nargs="?",
                        help="chain spec (JSON, or YAML with pyyaml); optional with --resume, "
                             "which then re-reads the recorded one")
    pc_run.add_argument("--outdir", required=True,
                        help="the chain's directory: one NN-<stage>/ per stage, plus chain/")
    pc_run.add_argument("--check", action="store_true",
                        help="validate every stage and handoff, print the commands, run nothing")
    pc_run.add_argument("--resume", action="store_true",
                        help="continue the chain recorded in --outdir")
    pc_run.add_argument("--timeout", type=_positive_int, default=None, metavar="SECONDS",
                        help="stop the whole chain after SECONDS (default: no limit)")
    pc_status = chain_sub.add_parser("status")
    pc_status.add_argument("outdir", help="a chain's --outdir, or the outdir of one of its stages")
    pc_status.add_argument("--quick", action="store_true",
                           help="report execution state without hashing data; lineage is not checked")
    pc_edges = chain_sub.add_parser("edges")
    pc_edges.add_argument("name", nargs="?", help="only the handoffs from or to this pipeline")
    # allow_abbrev=False: `run` forwards every unknown flag to the pipeline (via parse_known_args
    # → _collect_overrides). With abbreviation on, a pipeline flag that is a prefix of a reserved
    # nfclaw flag (e.g. `--res`, `--time`) would be silently swallowed as `--resume`/`--timeout`
    # instead of passed through. Turning it off keeps reserved flags exact and lets everything else
    # reach Nextflow. Full flag names and single-dash `-profile` are unaffected.
    p_run = sub.add_parser("run", allow_abbrev=False)
    p_run.add_argument("name")
    # One value as before (a samplesheet, a directory, an accession, `false`), or — repeated — the
    # data files nfclaw generates the samplesheet from. Repeated rather than multi-valued: a value
    # list would swallow a pipeline name written after it (`run --input s.csv rnaseq`).
    p_run.add_argument("--input", action="append",
                       help="a samplesheet; or the data files themselves — a directory, a quoted "
                            "glob, or a file (repeat --input for several) — to generate the "
                            "samplesheet from")
    p_run.add_argument("--sheet-set", dest="sheet_set", action="append", default=[],
                       metavar="COLUMN=VALUE",
                       help="a column of the samplesheet nfclaw generates from --input data files "
                            "(repeatable): a constant, or a template using {sample}/{lane}; an "
                            "empty VALUE leaves the column empty")
    p_run.add_argument("--outdir", required=True)
    p_run.add_argument("-profile", "--profile", dest="profile", default="docker")
    p_run.add_argument("--params-file", dest="params_file")
    p_run.add_argument("--pipeline-version", dest="pipeline_version")
    p_run.add_argument("--nxf-ver", dest="nxf_ver", type=_nxf_version,
                       help="pin the Nextflow engine version for this run (sets NXF_VER)")
    p_run.add_argument("--nxf-env", dest="nxf_env", action="append", default=[],
                       metavar="KEY=VALUE",
                       help="set an NXF_* env var for this run (repeatable), e.g. "
                            "NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true")
    # The nf-core-documented way to run on a machine smaller than the pipeline's default requests
    # (`process_high` is 12 CPUs / 72.GB in the stock nf-core base.config): a `process.resourceLimits`
    # ceiling. nfclaw generates the config and passes it with `-c`, so no hand-written file is needed.
    p_run.add_argument("--limit-cpus", dest="limit_cpus", type=_positive_int, metavar="N",
                       help="cap every process request at N CPUs "
                            "(Nextflow process.resourceLimits)")
    p_run.add_argument("--limit-memory", dest="limit_memory", metavar="SIZE",
                       help="cap every process request at SIZE memory, e.g. 15.GB")
    p_run.add_argument("--limit-time", dest="limit_time", metavar="DURATION",
                       help="cap every process request at DURATION, e.g. 1.h")
    p_run.add_argument("-c", "--config", dest="config", action="append", default=[],
                       metavar="PATH",
                       help="extra Nextflow config file passed through as `-c` (repeatable), e.g. "
                            "a docker host-network or custom-resources config")
    p_run.add_argument("--allow-spaces", dest="allow_spaces", action="store_true",
                       help="run even if a path contains spaces (off by default; spaces break "
                            "many bioinformatics tools and Nextflow's work dir)")
    p_run.add_argument("--check", action="store_true")
    p_run.add_argument("--demo", action="store_true")
    p_run.add_argument("--resume", action="store_true")
    p_run.add_argument("--no-provenance", action="store_true")
    # No wall-clock limit by default: a real nf-core run (a sarek WGS, a large rnaseq) can take days,
    # and Nextflow already bounds each task with its own `time` directive.
    p_run.add_argument("--timeout", type=_positive_int, default=None, metavar="SECONDS",
                       help="stop the whole run after SECONDS (default: no limit)")
    # A Model Context Protocol server on stdin/stdout for agents (runner.mcp_server). Each of its tools
    # runs one of the commands above, so this CLI stays the single implementation.
    sub.add_parser("mcp", help="serve nfclaw to MCP clients over stdio (see docs/mcp.md)")
    return parser


def run_option_names() -> frozenset[str]:
    """Every option `nfclaw run` keeps for itself, spelled as a parameter key (`--nxf-env` -> `nxf_env`).
    A pipeline parameter with one of these names cannot be passed as `--name=value`: argparse would
    take it as nfclaw's own option."""
    commands = next(a for a in build_parser()._actions
                    if isinstance(a, argparse._SubParsersAction))
    return frozenset(opt[2:].replace("-", "_")
                     for action in commands.choices["run"]._actions
                     for opt in action.option_strings if opt.startswith("--"))


def _main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # argparse reads a value attached to a short option, so Nextflow's own `-config x.config` (or a
    # stray `-cpus 4`) would silently become `-c onfig` and leave the real path behind as a
    # misleading "extra argument". Name the nfclaw spelling before parsing instead.
    if argv[:1] == ["run"]:
        for tok in argv[1:]:
            name = tok.split("=", 1)[0]
            if name.startswith("-c") and not name.startswith("--") and name != "-c":
                print(NfclawError(
                    ErrorCode.PARAMS_INVALID, f"unexpected argument: {tok!r}",
                    fix=("Nextflow's `-config` is `--config PATH` (or `-c PATH`) for nfclaw."
                         if name == "-config" else
                         "nfclaw sets Nextflow's own single-dash options itself; pass a config "
                         "file with `--config PATH` (or `-c PATH`) and pipeline parameters as "
                         "--param value.")), file=sys.stderr)
                return 1
    args, extras = parser.parse_known_args(argv)
    # Only `run` forwards unrecognised flags (to the pipeline). Anywhere else an unknown flag is a typo
    # that must not be ignored: `show X --pipeline-versoin 1.0.0` printed the *latest* docs.
    if extras and args.cmd != "run":
        parser.error(f"unrecognized arguments: {' '.join(extras)}")
    try:
        root = _repo_root()
    except NfclawError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    pdir = root / "pipelines"

    if args.cmd == "mcp":
        from runner import mcp_server                       # lazy: only the server needs it
        return mcp_server.serve(root)

    if args.cmd == "list":
        for p in discovery.discover(pdir):
            fm = p.frontmatter
            print(f"{p.name}\t{fm.get('version', '')}\t{fm.get('description', '')}")
        return 0

    if args.cmd == "show":
        try:
            p = discovery.find(args.name, pdir)                # 404 before any git work
            if args.pipeline_version:
                st = versions.ensure(args.name, args.pipeline_version,
                                     pipelines_dir=pdir, repo_root=root)
                for note in st.notes:                          # e.g. `dev` is unreleased code
                    print(f"warning: {note}", file=sys.stderr)
                if versions.is_cached(st):                     # a non-pinned version → generate on demand
                    skill_path, ref_path = versions.generate_docs(st, dest_dir=st.path.parent)
                    print(skill_path.read_text(encoding="utf-8"))
                    print(f"reference.md for this version cached at {ref_path}", file=sys.stderr)
                    return 0
                # requested version IS the pin → fall through to the committed skill.md
        except NfclawError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(p.skill_md.read_text(encoding="utf-8") if p.skill_md.exists()
              else f"(no skill.md for {args.name})")
        return 0

    if args.cmd == "versions":
        try:
            avail = versions.available(args.name, pipelines_dir=pdir, repo_root=root)
            dev_commit, dev_fresh = versions.dev_head(args.name, pipelines_dir=pdir,
                                                      repo_root=root)
        except NfclawError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if not avail:
            print(f"No releases found for {args.name} (check network connectivity).",
                  file=sys.stderr)
        for tag, is_pin in avail:
            print(f"{tag}\tlatest (pinned)" if is_pin else tag)
        # The unreleased development branch goes last, after every release: it is not one, and a
        # caller reading the first line still gets the newest release.
        if dev_commit:
            when = "" if dev_fresh else ", last fetched — remote unreachable"
            print(f"{versions.DEV_BRANCH}\tdevelopment branch, unreleased "
                  f"(head {dev_commit[:12]}{when})")
        return 0

    if args.cmd == "verify":
        try:
            cmp = verify.compare(Path(args.against).expanduser().resolve(),
                                 Path(args.replay).expanduser().resolve())
        except NfclawError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(verify.report(cmp), end="")
        # The default compares file presence. Strict verification additionally checks every byte and
        # recorded link identity; neither comparison by itself establishes analytical accuracy.
        # --strict also requires the same execution environment where both runs recorded one.
        return 0 if ((cmp.byte_identical and cmp.same_environment) if args.strict
                     else cmp.structurally_equal) else 1

    if args.cmd == "status":
        log = _run_log_path(args.outdir)
        chain_log = (Path(args.outdir).expanduser().resolve() / chain.RECORD_DIRNAME / "logs"
                     / chain.LOG_NAME)
        if not log.is_file() and chain_log.is_file():       # the --outdir of a chain
            log = chain_log
        st = runlog.read_state(log)
        print(_status_report(st), end="")
        if st.kind == "chain":
            print(f"chain: `nfclaw chain status {args.outdir}` lists its stages and verifies "
                  "their lineage")
        return 0 if st.state == "success" else 3 if st.state == "running" else 1

    shown: list[str] = []

    def warn(message: str) -> None:                           # advisory, non-blocking
        shown.append(message)
        print(f"warning: {message}", file=sys.stderr, flush=True)

    if args.cmd == "chain":
        return _chain(args, parser, root, warn)

    if args.cmd == "run":
        log_path = _run_log_path(args.outdir)
        size_before = log_path.stat().st_size if log_path.is_file() else None

        def unlaunched(outcome: str, error: str) -> None:
            # An attempt that ended before launching wrote nothing; if the --outdir already holds a
            # run log, its last line is the *previous* attempt's — record this one after it. A fresh
            # --outdir stays untouched (so the next attempt is not refused as "not empty"), and
            # --check never writes there.
            if args.check or size_before is None:
                return
            try:
                if log_path.stat().st_size != size_before:
                    return                                    # launched: the log has it already
            except OSError:
                return
            runlog.record_unlaunched(log_path, command=shlex.join(["nfclaw", *argv]),
                                     outcome=outcome, error=error)

        try:
            if not args.input:
                raw_input = None
            elif len(args.input) == 1:
                raw_input = args.input[0] or None
            else:
                raw_input = list(args.input)
            sheet_set = sheetgen.parse_assignments(args.sheet_set)
            # `kill` (SIGTERM) or a closing terminal (SIGHUP) stop the run the way Ctrl-C does —
            # Nextflow shut down, the run log closed with the outcome — instead of killing nfclaw on
            # the spot and leaving Nextflow running orphaned.
            with execution.stop_on_signals():
                res = orchestration.run_pipeline(
                    args.name, repo_root=root,
                    input_path=raw_input,                  # interpreted against the pipeline schema
                    outdir=Path(args.outdir).expanduser().resolve(),
                    profile=args.profile,
                    params_file=Path(args.params_file) if args.params_file else None,
                    cli_overrides=_collect_overrides(extras),
                    resume=args.resume, demo=args.demo, check_only=args.check,
                    write_provenance=not args.no_provenance, timeout_seconds=args.timeout,
                    pipeline_version=args.pipeline_version,
                    nxf_ver=args.nxf_ver, nxf_env=resources.parse_nxf_env(args.nxf_env),
                    allow_spaces=args.allow_spaces, configs=args.config,
                    limits=resources.parse(args.limit_cpus, args.limit_memory, args.limit_time),
                    on_warning=warn, sheet_set=sheet_set)
        except NfclawError as exc:
            print(str(exc), file=sys.stderr)
            if not exc.details.get("active_run") and not exc.details.get("unsafe_write_boundary"):
                unlaunched("refused before launch", str(exc))
            return 1
        except (execution.Terminated, KeyboardInterrupt) as exc:
            code = _stopped(exc, log_path)
            unlaunched(f"{execution.stop_outcome(exc)} before launch",
                       f"nfclaw: {_stop_words(exc)} before launching")
            return code
        for w in res.warnings:                                # any not already said before launch
            if w not in shown:
                warn(w)
        print(nextflow_command.shell_line(res.command, res.env))
        if res.generated_samplesheet is not None:
            print(f"samplesheet: {res.generated_samplesheet} (generated from --input)")
        rep = res.outputs_report
        if rep is not None:                                   # real run — surface where results landed
            print(f"outputs: {len(rep.files)} files in {res.outdir}")
            if rep.multiqc_report is not None:
                print(f"multiqc: {rep.multiqc_report}")
        if res.log_path is not None:
            print(f"log: {res.log_path}")
        return 0
    return 2
