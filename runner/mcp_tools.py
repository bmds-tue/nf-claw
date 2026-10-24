"""nfclaw's MCP tools, resources and prompt — each one a documented `nfclaw` command.

Nothing here reimplements the runner. A tool turns its arguments into the command line a person
would type, runs the CLI (`python -m runner …`), and hands back what it printed. Commands that
answer at once (`show`, `versions`, `status`, `verify`, `chain edges`, `chain status`) run in the
foreground; `run` and `chain run` — which can take days — run as detached jobs (runner.jobs) that
keep going after the client disconnects and are followed with `get_job`. The pipeline docs an agent
reads (`skill.md`, `reference.md`, `AGENTS.md`, `docs/`) are served as they are, as resources and
through `show_pipeline`.
"""
from __future__ import annotations

import json
import math
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from runner import chain, cli, jobs, settings
from runner.errors import NfclawError
from runner.mcp_server import INVALID_PARAMS, RESOURCE_NOT_FOUND, Context, RpcError, tool_result

INSTRUCTIONS = """\
nf-claw runs pinned nf-core pipelines through its own CLI (nfclaw), with validation before launch \
and a provenance bundle after. Workflow:
1. list_pipelines(query) to find a pipeline.
2. show_pipeline(pipeline): its skill.md is authoritative for inputs, required parameters and the \
reference genome. For any other parameter use show_pipeline(pipeline, document="reference", \
grep=...). Never invent a parameter or value.
3. run_pipeline(..., check=true) validates everything and prints the exact command without running \
it.
4. run_pipeline(...) starts a detached job and returns its job_id. It keeps running after this \
session ends; nothing needs to stay connected.
5. get_job(job_id, wait_seconds=N) follows it: running (phase preparing or launched), then \
succeeded, failed, cancelled or lost. On failure, read status_report and output_tail, fix the \
cause, and resubmit with resume=true to continue from Nextflow's cache.
Chains: chain_edges shows which pipeline can feed which; run_chain(spec) runs stages in order, \
each started only after the previous one succeeded (spec format: resource nfclaw://docs/chaining). \
run_status(outdir, chain=true) verifies a chain's lineage. cancel_job stops a job cleanly \
(Nextflow and its tasks shut down, provenance written). Use absolute paths and one new outdir per \
run. Before reporting a warning as a fault, check nfclaw://docs/known-issues.
"""

_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_PARAM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_DOC = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_URI = re.compile(r"^nfclaw://(?:(?P<guide>guide)|(?P<catalog>catalog)|docs/(?P<doc>[^/]+)|"
                  r"pipelines/(?P<pipeline>[^/]+)/(?P<document>skill|reference))$")
_MAX_WAIT = 600
_DEFAULT_RUN_WAIT = 20


def server_version() -> str:
    """nfclaw's version: the installed distribution's, else this checkout's pyproject.toml."""
    try:
        from importlib.metadata import version
        return version("nfclaw")
    except Exception:
        pass
    try:
        import tomllib
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    except Exception:
        return "unknown"


class ToolError(Exception):
    """A call the model should read, correct and retry: returned as an `isError` result."""


@dataclass(frozen=True)
class CliResult:
    code: int
    stdout: str
    stderr: str

    @property
    def text(self) -> str:
        return "\n".join(part.rstrip("\n") for part in (self.stdout, self.stderr) if part.strip())


# --- argument schemas -----------------------------------------------------------------------------
# Kept to keywords every client and model provider accepts (type, items, enum, minimum, maximum,
# default, description): no anyOf, type lists or additionalProperties. `_check_args` enforces them.

def _s(description: str, **extra) -> dict:
    return {"type": "string", "description": description, **extra}


def _b(description: str) -> dict:
    return {"type": "boolean", "description": description}


def _i(description: str, **extra) -> dict:
    return {"type": "integer", "description": description, **extra}


def _o(description: str) -> dict:
    return {"type": "object", "description": description}


def _a(description: str) -> dict:
    return {"type": "array", "items": {"type": "string"}, "description": description}


_WAIT = _i("Seconds to wait for the job before returning (0-600). Keep it below your client's tool "
           "timeout; the job is unaffected when the call returns.", minimum=0, maximum=_MAX_WAIT)
_JOB_ID = _s("A job id returned by run_pipeline or run_chain (see list_jobs).")
_PIPELINE = _s("Pipeline name exactly as list_pipelines returns it, e.g. rnaseq.")


def _tool(name: str, title: str, description: str, properties: dict, required: list[str],
          *, read_only: bool, destructive: bool = False, idempotent: bool = False,
          open_world: bool = False, always_load: bool = False) -> dict:
    tool = {
        "name": name,
        "title": title,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required},
        "annotations": {"title": title, "readOnlyHint": read_only,
                        "destructiveHint": destructive, "idempotentHint": idempotent,
                        "openWorldHint": open_world},
    }
    if always_load:
        # Antigravity hides MCP tools behind one generic call tool unless a tool asks to be
        # loaded up front; its model then guessed their arguments instead of reading the schema.
        tool["_meta"] = {"antigravity/alwaysLoad": True}
    return tool


TOOLS = [
    _tool("list_pipelines", "Find a pipeline",
          "Search the nf-claw library of pinned nf-core pipelines by keyword: assay, data type, "
          "method or tool (e.g. 'rna-seq', 'variant calling', 'nanopore', 'kraken'). Returns each "
          "match's pinned version, description, expected input and the pipelines it can feed in a "
          "chain. An empty query lists the library.",
          {"query": _s("Words to match; a pipeline matching more of them ranks higher."),
           "limit": _i("Maximum results (1-100, default 25).", minimum=1, maximum=100)},
          [], read_only=True, idempotent=True, always_load=True),
    _tool("show_pipeline", "Read a pipeline's skill",
          "Return a pipeline's skill.md — how to run it: inputs and samplesheet columns, required "
          "parameters with allowed values, reference genome handling, outputs and chaining — or "
          "its reference.md (every parameter with type, allowed values, constraints and default). "
          "Both are generated from the pinned release and override anything remembered. Use grep "
          "to get only the matching lines of a long document.",
          {"pipeline": _PIPELINE,
           "document": _s("'skill' (default) or 'reference'.", enum=["skill", "reference"]),
           "grep": _s("Only lines containing any of these words (case-insensitive), with their "
                      "section heading and table header."),
           "version": _s("Another release (e.g. 3.14.0) or 'dev': its docs are generated from that "
                         "release's schema (fetched on first use). Default: the pinned release.")},
          ["pipeline"], read_only=True, idempotent=True, open_world=True, always_load=True),
    _tool("list_versions", "List a pipeline's releases",
          "List the published releases of a pipeline, newest first, marking the pinned one, plus "
          "its unreleased development branch (dev).",
          {"pipeline": _PIPELINE}, ["pipeline"], read_only=True, idempotent=True, open_world=True),
    _tool("chain_edges", "List pipeline handoffs",
          "Which pipeline can follow which in a chain (e.g. fetchngs -> rnaseq), with what each "
          "handoff passes on. Without a rule there is no chain between two pipelines.",
          {"pipeline": _s("Only the handoffs from or to this pipeline.")},
          [], read_only=True, idempotent=True),
    _tool("run_pipeline", "Run a pipeline",
          "Run a pinned nf-core pipeline with `nfclaw run`, as a detached job that survives this "
          "session. nfclaw validates the samplesheet and parameters against the pinned schema and "
          "checks the environment before launching, then records a provenance bundle "
          "(<outdir>/provenance). Returns a job_id: follow it with get_job. With check=true "
          "nothing runs: the job validates and prints the exact command. Arguments mirror "
          "the CLI flags.",
          {"pipeline": _PIPELINE,
           "outdir": _s("Results directory, absolute path. New or empty, unless resume=true. One "
                        "directory per run."),
           "input": _a("The pipeline's --input: one samplesheet, directory, URL or accession list "
                       "as skill.md describes; or several data files / a quoted glob / a directory "
                       "of FastQ files to generate the samplesheet from (see "
                       "sheet_set). Absolute paths."),
           "sheet_set": _o("Samplesheet columns no file determines, when generating it from data "
                           "files: {column: value}; a value may use {sample} or {lane}."),
           "params": _o("Pipeline parameters by their schema name, e.g. {\"genome\": \"GRCh38\", "
                        "\"skip_trimming\": true}. Scalar values only (string, number, boolean). "
                        "Look names and allowed values up with show_pipeline."),
           "params_file": _s("A JSON or YAML parameters file; values in params override it."),
           "profile": _s("Nextflow profile(s), comma-separated. Default: docker."),
           "pipeline_version": _s("Run another release (or 'dev') instead of the pinned one."),
           "nxf_ver": _s("Pin the Nextflow engine version, e.g. 25.10.4 (sets NXF_VER)."),
           "nxf_env": _o("NXF_* variables for this run, e.g. {\"NXF_JVM_ARGS\": "
                         "\"-Djava.net.preferIPv6Addresses=true\"} on an IPv6-only host."),
           "config": _a("Extra Nextflow config files (passed with -c)."),
           "limit_cpus": _i("Cap every task at N CPUs (process.resourceLimits).", minimum=1),
           "limit_memory": _s("Cap every task's memory, e.g. 15.GB."),
           "limit_time": _s("Cap every task's run time, e.g. 8.h — a deliberate ceiling only."),
           "timeout_seconds": _i("Stop the whole run after this many seconds (default: no limit).",
                                 minimum=1),
           "demo": _b("Run the release's bundled test profile (small test data)."),
           "resume": _b("Continue a previous run in the same outdir from Nextflow's cache."),
           "check": _b("Validate and print the command only; launch nothing, write nothing."),
           "allow_spaces": _b("Run even if a path contains spaces (they break many tools)."),
           "no_provenance": _b("Skip the replay bundle and checksum records."),
           "wait_seconds": {**_WAIT, "description": _WAIT["description"]
                            + f" Default {_DEFAULT_RUN_WAIT}: a refused launch "
                              "is reported inline."}},
          ["pipeline", "outdir"], read_only=False, open_world=True, always_load=True),
    _tool("run_chain", "Run a chain of pipelines",
          "Run several pipelines in sequence with `nfclaw chain run`, as one detached job: each "
          "stage starts only after the previous one succeeded, and its input is prepared from that "
          "stage's outputs, verified by checksum. The spec is the chain file's JSON (format: "
          "resource nfclaw://docs/chaining), e.g. {\"stages\": [{\"pipeline\": \"fetchngs\", "
          "\"input\": \"/abs/ids.csv\"}, {\"pipeline\": \"rnaseq\", \"params\": {\"genome\": "
          "\"GRCh38\"}}]}. Each stage gets <outdir>/NN-<pipeline>/. check=true validates every "
          "stage and handoff and runs nothing. Follow the job with get_job; verify lineage "
          "with run_status(chain=true).",
          {"spec": _o("The chain spec. Omit only with resume=true (the recorded spec is reused)."),
           "outdir": _s("The chain's directory, absolute path."),
           "check": _b("Validate every stage and handoff; launch nothing."),
           "resume": _b("Continue the chain recorded in outdir: succeeded stages are kept, the "
                        "failed one resumes from cache."),
           "timeout_seconds": _i("One deadline for the whole chain (default: no limit).",
                                 minimum=1),
           "wait_seconds": {**_WAIT, "description": _WAIT["description"]
                            + f" Default {_DEFAULT_RUN_WAIT}."}},
          ["outdir"], read_only=False, open_world=True),
    _tool("get_job", "Follow a job",
          "State of a job started by run_pipeline or run_chain: running (phase 'preparing' = "
          "validating or staging, 'launched' = Nextflow is running), succeeded, failed, cancelled, "
          "or lost (its supervisor was killed). Includes nfclaw's status report and the job's "
          "latest output. With wait_seconds it returns as soon as the job ends.",
          {"job_id": _JOB_ID, "wait_seconds": _WAIT,
           "log_lines": _i("How many of the job's last output lines to include "
                           "(0-500, default 20).",
                           minimum=0, maximum=500)},
          ["job_id"], read_only=True, idempotent=True, always_load=True),
    _tool("list_jobs", "List jobs",
          "Jobs started through this server, newest first, with their state. Jobs persist across "
          "sessions and server restarts.",
          {"state": _s("Only jobs in this state.",
                       enum=["running", "succeeded", "failed", "cancelled", "lost"]),
           "limit": _i("Maximum results (1-200, default 20).", minimum=1, maximum=200)},
          [], read_only=True, idempotent=True),
    _tool("cancel_job", "Stop a job",
          "Stop a running job the way `kill <nfclaw pid>` does: nfclaw shuts Nextflow and its "
          "tasks down, records the outcome in the run log and writes the provenance bundle, so the "
          "run can be resumed later with resume=true. A chain stops at its current stage.",
          {"job_id": _JOB_ID,
           "wait_seconds": {**_WAIT, "description": "Seconds to wait for the job to finish "
                            "stopping (default 15)."}},
          ["job_id"], read_only=False, destructive=True, idempotent=True),
    _tool("run_status", "Status of any run directory",
          "nfclaw's report on a run or chain directory, including ones not started through MCP: "
          "`nfclaw status` (success, running, how it ended, the error and where the logs are), or "
          "with chain=true `nfclaw chain status`, which lists the stages and verifies every "
          "handoff by SHA-256 (quick=true skips the hashing).",
          {"outdir": _s("The run's or chain's --outdir."),
           "chain": _b("Report a chain's stages and verify its lineage."),
           "quick": _b("With chain=true: report states without hashing data.")},
          ["outdir"], read_only=True, idempotent=True),
    _tool("verify_replay", "Compare a replay with its original",
          "`nfclaw verify`: compare a replayed run (provenance/commands.sh) with the run it "
          "reproduces, by path: identical, changed, missing and extra files, and the recorded "
          "execution environments. Passes when the replay made the same set of files; strict=true "
          "also requires identical bytes and environment.",
          {"replay": _s("The replay's output directory."),
           "against": _s("The original run's output directory."),
           "strict": _b("Also require identical bytes, links and execution environment.")},
          ["replay", "against"], read_only=True, idempotent=True),
]
_TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}
_TYPES = {"string": str, "boolean": bool, "object": dict, "array": list}


def _check_args(tool: dict, args: dict) -> None:
    """Enforce a tool's input schema, saying exactly what to change."""
    schema = tool["inputSchema"]
    props = schema["properties"]
    problems = [f"unknown argument {k!r} (accepted: {', '.join(sorted(props))})"
                for k in args if k not in props]
    problems += [f"missing required argument {k!r}" for k in schema["required"] if k not in args]
    for key, value in args.items():
        spec = props.get(key)
        if spec is None:
            continue
        kind = spec["type"]
        if kind == "integer":
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif kind == "array" and isinstance(value, str):
            ok = True                                 # one item given as a plain string: accepted
        else:
            ok = isinstance(value, _TYPES[kind])
        if not ok:
            problems.append(f"{key!r} must be {'an' if kind[0] in 'aeiou' else 'a'} {kind}")
            continue
        if kind == "array" and not isinstance(value, str) and \
                not all(isinstance(v, str) for v in value):
            problems.append(f"{key!r} must be a list of strings")
        if "enum" in spec and value not in spec["enum"]:
            problems.append(f"{key!r} must be one of {', '.join(spec['enum'])}")
        if kind == "integer" and "minimum" in spec and value < spec["minimum"]:
            problems.append(f"{key!r} must be >= {spec['minimum']}")
        if kind == "integer" and "maximum" in spec and value > spec["maximum"]:
            problems.append(f"{key!r} must be <= {spec['maximum']}")
    if problems:
        raise ToolError(f"{tool['name']}: invalid arguments:\n"
                        + "\n".join(f"- {p}" for p in problems))


def _strings(value) -> list[str]:
    return [value] if isinstance(value, str) else list(value or [])


def _flag_value(key: str, value) -> str:
    """A JSON scalar as the CLI expects it after `--key=`."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ToolError(f"params.{key}: {value} is not a finite number")
        return repr(value)                            # shortest exact round-trip decimal
    if isinstance(value, str):
        return value
    raise ToolError(f"params.{key} must be a string, number or boolean (got "
                    f"{type(value).__name__}); pass structured values in a params_file")


def _mapping(name: str, value: dict) -> list[tuple[str, str]]:
    out = []
    for key, val in value.items():
        if not isinstance(val, str):
            raise ToolError(f"{name}.{key} must be a string")
        out.append((key, val))
    return out


class NfclawTools:
    """The MCP handler (see runner.mcp_server.Handler) for one nf-claw checkout."""

    def __init__(self, repo_root: Path, *, cwd: str | None = None):
        self.root = Path(repo_root)
        self.pipelines_dir = self.root / "pipelines"
        # Relative paths in arguments mean what they would on the command line, here.
        self.cwd = cwd or os.getcwd()
        self.reserved = cli.run_option_names()
        self.command_timeout = settings.seconds("NFCLAW_MCP_COMMAND_TIMEOUT", 300)

    # --- MCP handler interface ------------------------------------------------------------------

    def list_tools(self, ctx: Context) -> list[dict]:
        return TOOLS

    def call_tool(self, name: str, arguments: dict, ctx: Context) -> dict:
        tool = _TOOLS_BY_NAME[name]
        # Many clients send null for an optional argument they leave unset: it means "omitted".
        arguments = {k: v for k, v in arguments.items() if v is not None}
        try:
            _check_args(tool, arguments)
            return getattr(self, f"_tool_{name}")(arguments, ctx)
        except ToolError as exc:
            return tool_result(str(exc), error=True)
        except NfclawError as exc:
            return tool_result(str(exc), error=True)
        except jobs.JobError as exc:
            return tool_result(f"{name}: {exc}", error=True)
        except subprocess.TimeoutExpired as exc:
            return tool_result(f"{name}: `{shlex.join(['nfclaw', *exc.cmd[3:]])}` did not finish "
                               f"within {exc.timeout:.0f} s (NFCLAW_MCP_COMMAND_TIMEOUT).",
                               error=True)

    def list_resources(self, ctx: Context) -> list[dict]:
        out = [_resource("nfclaw://guide", "AGENTS.md",
                         "How to use nf-claw: finding, running, chaining and replaying pipelines."),
               _resource("nfclaw://catalog", "catalog.md",
                         "Every pipeline in the library with its version, input and output.")]
        for doc in self._docs():
            out.append(_resource(f"nfclaw://docs/{doc}", f"docs/{doc}.md", f"nf-claw docs: {doc}"))
        for name in self._pipelines():
            out.append(_resource(f"nfclaw://pipelines/{name}/skill", f"{name} skill.md",
                                 f"How to run nf-core/{name} (pinned release)."))
        return out

    def list_resource_templates(self, ctx: Context) -> list[dict]:
        return [
            {"uriTemplate": "nfclaw://pipelines/{pipeline}/skill", "name": "skill.md",
             "description": "How to run a pipeline: inputs, required parameters, outputs.",
             "mimeType": "text/markdown"},
            {"uriTemplate": "nfclaw://pipelines/{pipeline}/reference", "name": "reference.md",
             "description": "Every parameter of a pipeline, with allowed values and defaults.",
             "mimeType": "text/markdown"},
            {"uriTemplate": "nfclaw://docs/{name}", "name": "docs",
             "description": "nf-claw documentation (chaining, timeouts, known-issues, mcp, ...).",
             "mimeType": "text/markdown"},
        ]

    def read_resource(self, uri: str, ctx: Context) -> list[dict]:
        m = _URI.match(uri)
        path = None
        if m and m["guide"]:
            path = self.root / "AGENTS.md"
        elif m and m["catalog"]:
            path = self.root / "catalog.md"
        elif m and m["doc"] and m["doc"] in self._docs():
            path = self.root / "docs" / f"{m['doc']}.md"
        elif m and m["pipeline"] and m["pipeline"] in self._pipelines():
            path = self.pipelines_dir / m["pipeline"] / f"{m['document']}.md"
        if path is None or not path.is_file():
            raise RpcError(RESOURCE_NOT_FOUND, f"resource not found: {uri}", {"uri": uri})
        return [{"uri": uri, "mimeType": "text/markdown",
                 "text": path.read_text(encoding="utf-8")}]

    def list_prompts(self, ctx: Context) -> list[dict]:
        return [{"name": "use_pipeline",
                 "description": "Run an nf-core pipeline through nf-claw: loads its skill.md and "
                                "the steps to validate, launch and follow it.",
                 "arguments": [{"name": "pipeline", "description": "Pipeline name, e.g. rnaseq",
                                "required": True},
                               {"name": "goal", "description": "What the analysis should achieve "
                                "(data, organism, question)", "required": False}]}]

    def get_prompt(self, name: str, arguments: dict, ctx: Context) -> dict:
        if name != "use_pipeline":
            raise RpcError(INVALID_PARAMS, f"unknown prompt: {name}")
        pipeline = str(arguments.get("pipeline") or "")
        if pipeline not in self._pipelines():
            raise RpcError(INVALID_PARAMS, f"unknown pipeline: {pipeline!r} (see list_pipelines)")
        goal = str(arguments.get("goal") or "").strip()
        skill = (self.pipelines_dir / pipeline / "skill.md").read_text(encoding="utf-8")
        text = (f"Run nf-core/{pipeline} with the nf-claw tools"
                + (f" for this goal: {goal}" if goal else "") + ".\n\n"
                "Steps: prepare inputs exactly as the skill below describes (absolute paths); look "
                "up any parameter beyond the required ones with "
                "show_pipeline(document=\"reference\", grep=...); validate with "
                "run_pipeline(check=true); then run_pipeline and follow the job with "
                "get_job(wait_seconds=...). On failure, read the report, fix, and resubmit with "
                "resume=true.\n\n"
                f"--- pipelines/{pipeline}/skill.md ---\n{skill}")
        return {"description": f"Run nf-core/{pipeline} with nf-claw",
                "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}

    # --- helpers --------------------------------------------------------------------------------

    def _pipelines(self) -> list[str]:
        if not self.pipelines_dir.is_dir():
            return []
        return sorted(d.name for d in self.pipelines_dir.iterdir()
                      if _NAME.match(d.name) and (d / "skill.md").is_file())

    def _docs(self) -> list[str]:
        docs = self.root / "docs"
        return sorted(p.stem for p in docs.glob("*.md") if _DOC.match(p.stem)) \
            if docs.is_dir() else []

    def _pipeline(self, name: str) -> str:
        if name not in self._pipelines():
            raise ToolError(f"unknown pipeline {name!r}; list_pipelines shows the library")
        return name

    def _path(self, value: str) -> str:
        """A path argument made absolute the way the CLI would, from the server's directory."""
        return str((Path(self.cwd) / Path(value).expanduser()).resolve())

    def _cli(self, argv: list[str]) -> CliResult:
        proc = subprocess.run(jobs.cli_command(argv), cwd=self.cwd, env=jobs.child_env(),
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=self.command_timeout)
        return CliResult(proc.returncode, proc.stdout, proc.stderr)

    def _cli_or_error(self, argv: list[str]) -> CliResult:
        res = self._cli(argv)
        if res.code != 0:
            raise ToolError(res.text or f"nfclaw {shlex.join(argv)} failed (exit {res.code})")
        return res

    # --- discovery tools ------------------------------------------------------------------------

    def _tool_list_pipelines(self, args: dict, ctx: Context) -> dict:
        catalog = json.loads((self.root / "catalog.json").read_text(encoding="utf-8"))
        # Compared without punctuation or spacing, so "RNA-seq", "rna seq" and "rnaseq" all meet.
        words = [w for w in (_squash(w) for w in re.split(r"[\s,;]+", args.get("query") or ""))
                 if w]
        limit = args.get("limit") or 25

        def score(p: dict) -> int:
            if not words:
                return 1
            name = _squash(p.get("name", ""))
            fields = [(name, 10), (_squash(p.get("description", "")), 4),
                      (_squash(" ".join(p.get("tools") or [])), 4),
                      (_squash(p.get("input", "")), 2), (_squash(p.get("summary", "")), 1)]
            total = 0
            for w in words:
                total += max((weight for text, weight in fields if w in text), default=0)
                total += 30 if w == name else 0
            return total

        ranked = sorted(((score(p), p) for p in catalog), key=lambda sp: (-sp[0], sp[1]["name"]))
        found = [p for s, p in ranked if s > 0]
        shown = [{k: p.get(k) for k in ("name", "version", "description", "input", "feeds",
                                        "tools", "summary")} for p in found[:limit]]
        lines = [f"{len(found)} of {len(catalog)} pipelines match"
                 + (f" {args.get('query')!r}" if words else "")
                 + (f" (showing {len(shown)})" if len(shown) < len(found) else "") + ":"]
        for p in shown:
            lines.append(f"- {p['name']} {p['version']}: {p['description']}")
            lines.append(f"  input: {p['input']}")
            if p.get("feeds"):
                lines.append(f"  feeds: {', '.join(p['feeds'])}")
        if len(shown) < len(found):
            lines.append(f"{len(found) - len(shown)} more not shown: narrow the search with query, "
                         "or raise limit (up to 100).")
        lines.append("Next: show_pipeline(pipeline) for how to run one.")
        return tool_result("\n".join(lines), {"total": len(found), "pipelines": shown})

    def _tool_show_pipeline(self, args: dict, ctx: Context) -> dict:
        name = self._pipeline(args["pipeline"])
        document = args.get("document") or "skill"
        version = args.get("version")
        notes = ""
        if version:
            res = self._cli_or_error(["show", name, f"--pipeline-version={version}"])
            text = res.stdout
            cached = re.search(r"reference\.md for this version cached at (.+)", res.stderr)
            notes = "\n".join(ln for ln in res.stderr.splitlines() if ln.startswith("warning:"))
            if document == "reference":
                ref = Path(cached.group(1).strip()) if cached else \
                    self.pipelines_dir / name / "reference.md"
                text = ref.read_text(encoding="utf-8")
        else:
            text = (self.pipelines_dir / name / f"{document}.md").read_text(encoding="utf-8")
        if args.get("grep"):
            text = _grep(text, args["grep"], f"{name} {document}.md")
        return tool_result((notes + "\n\n" if notes else "") + text)

    def _tool_list_versions(self, args: dict, ctx: Context) -> dict:
        res = self._cli_or_error(["versions", self._pipeline(args["pipeline"])])
        versions = []
        for line in res.stdout.splitlines():
            tag, _, note = line.partition("\t")
            if tag:
                versions.append({"version": tag, "pinned": note.startswith("latest (pinned)"),
                                 "note": note})
        return tool_result(res.text, {"pipeline": args["pipeline"], "versions": versions})

    def _tool_chain_edges(self, args: dict, ctx: Context) -> dict:
        argv = ["chain", "edges"]
        if args.get("pipeline"):
            argv.append(self._pipeline(args["pipeline"]))
        res = self._cli_or_error(argv)
        edges = []
        for line in res.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                edges.append({"from": parts[0], "to": parts[1], "description": parts[2]})
        text = "\n".join(f"{e['from']} -> {e['to']}: {e['description']}" for e in edges) \
            or "No handoff rule matches."
        return tool_result(text, {"edges": edges})

    # --- execution ------------------------------------------------------------------------------

    def run_argv(self, args: dict) -> list[str]:
        """The `nfclaw run` command line for run_pipeline's arguments. Every value is one
        `--option=value` token, so a value starting with '-' can never be read as an option."""
        argv = ["run", self._pipeline(args["pipeline"]), f"--outdir={self._path(args['outdir'])}"]
        for item in _strings(args.get("input")):
            argv.append(f"--input={item}")
        for key, val in _mapping("sheet_set", args.get("sheet_set") or {}):
            argv.append(f"--sheet-set={key}={val}")
        for key in ("profile", "pipeline_version", "nxf_ver", "limit_memory", "limit_time"):
            if args.get(key):
                argv.append(f"--{key.replace('_', '-')}={args[key]}")
        if args.get("params_file"):
            argv.append(f"--params-file={self._path(args['params_file'])}")
        for key, val in _mapping("nxf_env", args.get("nxf_env") or {}):
            argv.append(f"--nxf-env={key}={val}")
        for cfg in _strings(args.get("config")):
            argv.append(f"--config={self._path(cfg)}")
        if args.get("limit_cpus"):
            argv.append(f"--limit-cpus={args['limit_cpus']}")
        if args.get("timeout_seconds"):
            argv.append(f"--timeout={args['timeout_seconds']}")
        for flag in ("demo", "resume", "check", "allow_spaces", "no_provenance"):
            if args.get(flag):
                argv.append(f"--{flag.replace('_', '-')}")
        for key, value in (args.get("params") or {}).items():
            if not isinstance(key, str) or not _PARAM.match(key):
                raise ToolError(f"params: {key!r} is not a parameter name")
            if key.replace("-", "_") in self.reserved:
                raise ToolError(f"params.{key} is an nfclaw option, not a pipeline parameter: pass "
                                f"it as the {key.replace('-', '_')!r} argument of run_pipeline")
            if value is None:
                raise ToolError(f"params.{key} is null; omit a parameter to keep its default")
            argv.append(f"--{key}={_flag_value(key, value)}")
        return argv

    def chain_argv(self, args: dict, spec_path: Path | None) -> list[str]:
        argv = ["chain", "run"]
        if spec_path is not None:
            argv.append(str(spec_path))
        argv.append(f"--outdir={self._path(args['outdir'])}")
        for flag in ("check", "resume"):
            if args.get(flag):
                argv.append(f"--{flag}")
        if args.get("timeout_seconds"):
            argv.append(f"--timeout={args['timeout_seconds']}")
        return argv

    def _refuse_busy_outdir(self, outdir: str) -> None:
        for job in jobs.list_jobs():
            if job.outdir == outdir and not job.check and jobs.alive(job):
                raise ToolError(f"job {job.id} is already running in {outdir}; follow it with "
                                f"get_job, stop it with cancel_job, or use another outdir")

    def _tool_run_pipeline(self, args: dict, ctx: Context) -> dict:
        argv = self.run_argv(args)
        outdir = self._path(args["outdir"])
        check = bool(args.get("check"))
        if not check:
            self._refuse_busy_outdir(outdir)
        job_dir = jobs.create_dir(args["pipeline"])
        job = jobs.launch(job_dir, kind="run", argv=argv, cwd=self.cwd, outdir=outdir, check=check,
                          pipeline=args["pipeline"],
                          log_path=str(cli._run_log_path(outdir)))
        return self._after_submit(job, args, ctx)

    def _tool_run_chain(self, args: dict, ctx: Context) -> dict:
        spec = args.get("spec")
        if spec is None and not args.get("resume"):
            raise ToolError("run_chain needs a spec (or resume=true to continue a recorded chain)")
        outdir = self._path(args["outdir"])
        check = bool(args.get("check"))
        if not check:
            self._refuse_busy_outdir(outdir)
        job_dir = jobs.create_dir("chain")
        spec_path = None
        if spec is not None:
            spec_path = job_dir / "spec.json"
            spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        log_path = Path(outdir) / chain.RECORD_DIRNAME / "logs" / chain.LOG_NAME
        job = jobs.launch(job_dir, kind="chain", argv=self.chain_argv(args, spec_path),
                          cwd=self.cwd, outdir=outdir, check=check, log_path=str(log_path))
        return self._after_submit(job, args, ctx)

    def _after_submit(self, job: jobs.Job, args: dict, ctx: Context) -> dict:
        wait = args.get("wait_seconds")
        job = self._wait(job.id, _DEFAULT_RUN_WAIT if wait is None else wait, ctx,
                         until_launched=True)
        return self._job_result(job, log_lines=200 if job.check else 20, submitted=True)

    def _launched(self, job: jobs.Job) -> bool:
        """Whether nfclaw has opened this job's run (or chain) log: it passed validation and
        preflight and is starting Nextflow."""
        if not job.log_path or job.check:
            return False
        try:
            size = Path(job.log_path).stat().st_size
        except OSError:
            return False
        return job.log_size_before is None or size > job.log_size_before

    def _wait(self, job_id: str, seconds: int, ctx: Context, *,
              until_launched: bool = False) -> jobs.Job:
        """Wait up to `seconds` for the job to end (or, with until_launched, to reach Nextflow),
        reporting progress to clients that asked for it. Never affects the job itself."""
        start = time.monotonic()
        delay = 0.25
        while True:
            job = jobs.load(job_id)
            if jobs.state(job) != "running" or (until_launched and self._launched(job)):
                return job
            elapsed = time.monotonic() - start
            remaining = seconds - elapsed
            if remaining <= 0:
                return job
            ctx.progress(round(elapsed, 1), None,
                         f"{job_id}: {'launched' if self._launched(job) else 'preparing'}")
            if ctx.cancelled.wait(min(delay, remaining)):
                return job
            delay = min(delay * 2, 5.0)

    def job_view(self, job: jobs.Job, *, log_lines: int) -> dict:
        state = jobs.state(job)
        view = {"job_id": job.id, "kind": job.kind, "pipeline": job.pipeline, "state": state,
                "check": job.check, "outdir": job.outdir,
                "command": shlex.join(["nfclaw", *job.argv]), "cwd": job.cwd,
                "created_at": job.created_at, "finished_at": job.finished_at,
                "exit_code": job.exit_code}
        launched = self._launched(job)
        if launched:
            res = self._cli(["status", job.outdir])
            view["status_report"] = res.text
            view["run_state"] = {0: "success", 3: "running"}.get(res.code, "not successful")
            view["caveats"] = "with caveats" in (res.stdout.splitlines() or [""])[0]
            view["log"] = job.log_path
        if state == "running":
            view["phase"] = ("launched" if view.get("run_state") == "running"
                             else "finishing" if launched else "preparing")
        if job.error:
            view["error"] = job.error
        view["output_tail"] = jobs.output_tail(job, log_lines)
        view["output_log"] = str(job.dir / jobs.OUTPUT_LOG)
        view["next"] = _next_step(view)
        return view

    def _job_result(self, job: jobs.Job, *, log_lines: int, submitted: bool = False) -> dict:
        """A job as a tool result. Only a submission that already failed (refused before launch, an
        invalid check) is a failed tool call; reporting a failed job is a successful one."""
        view = self.job_view(job, log_lines=log_lines)
        failed = submitted and view["state"] in ("failed", "lost")
        return tool_result(_render_job(view), view, error=failed)

    def _tool_get_job(self, args: dict, ctx: Context) -> dict:
        job = jobs.load(args["job_id"])
        if args.get("wait_seconds"):
            job = self._wait(job.id, args["wait_seconds"], ctx)
        lines = args.get("log_lines")
        return self._job_result(job, log_lines=(200 if job.check else 20) if lines is None
                                else lines)

    def _tool_list_jobs(self, args: dict, ctx: Context) -> dict:
        wanted = args.get("state")
        rows = []
        for job in jobs.list_jobs():
            state = jobs.state(job)
            if wanted and state != wanted:
                continue
            rows.append({"job_id": job.id, "kind": job.kind, "pipeline": job.pipeline,
                         "state": state, "check": job.check, "outdir": job.outdir,
                         "created_at": job.created_at, "finished_at": job.finished_at})
            if len(rows) >= (args.get("limit") or 20):
                break
        text = "\n".join(f"{r['job_id']}  {r['state']:<9}  {'check ' if r['check'] else ''}"
                         f"{r['kind']}  {r['outdir']}" for r in rows) or "No jobs."
        return tool_result(text, {"jobs": rows})

    def _tool_cancel_job(self, args: dict, ctx: Context) -> dict:
        job = jobs.load(args["job_id"])
        if not jobs.cancel(job):
            view = self.job_view(job, log_lines=5)
            return tool_result(f"job {job.id} is not running ({view['state']}); "
                               "nothing to stop.\n\n"
                               + _render_job(view), view)
        wait = args.get("wait_seconds")
        job = self._wait(job.id, 15 if wait is None else wait, ctx)
        return self._job_result(job, log_lines=20)

    # --- reports --------------------------------------------------------------------------------

    def _tool_run_status(self, args: dict, ctx: Context) -> dict:
        outdir = self._path(args["outdir"])
        if args.get("chain"):
            argv = ["chain", "status", outdir] + (["--quick"] if args.get("quick") else [])
        else:
            argv = ["status", outdir]
        res = self._cli(argv)
        state = {0: "success", 3: "running"}.get(res.code, "not successful")
        return tool_result(res.text, {"outdir": outdir, "state": state, "exit_code": res.code,
                                      "report": res.text})

    def _tool_verify_replay(self, args: dict, ctx: Context) -> dict:
        argv = ["verify", self._path(args["replay"]), f"--against={self._path(args['against'])}"]
        if args.get("strict"):
            argv.append("--strict")
        res = self._cli(argv)
        return tool_result(res.text, {"passed": res.code == 0, "strict": bool(args.get("strict")),
                                      "exit_code": res.code, "report": res.text})


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _resource(uri: str, name: str, description: str) -> dict:
    return {"uri": uri, "name": name, "description": description, "mimeType": "text/markdown"}


def _grep(text: str, pattern: str, label: str) -> str:
    """The lines of a markdown document that contain any of the words in `pattern`, each under its
    section heading and, inside a table, under that table's header row."""
    words = [w.lower() for w in pattern.split() if w]
    lines = text.splitlines()
    out: list[str] = []
    heading = shown_heading = None
    table_start = shown_table = None
    for i, line in enumerate(lines):
        if line.startswith("#"):
            heading = line
            continue
        if line.startswith("|"):
            if i == 0 or not lines[i - 1].startswith("|"):
                table_start = i
        else:
            table_start = None
        if not any(w in line.lower() for w in words):
            continue
        if heading != shown_heading:
            out += ["", heading] if heading else []
            shown_heading, shown_table = heading, None
        if table_start is not None and i > table_start + 1 and table_start != shown_table:
            out += lines[table_start:table_start + 2]
            shown_table = table_start
        out.append(line)
    if not out:
        return f"No line of {label} contains any of: {pattern}"
    return f"Lines of {label} matching {pattern!r}:\n" + "\n".join(out).strip("\n")


def _next_step(view: dict) -> str:
    state, jid = view["state"], view["job_id"]
    if state == "running":
        return (f"get_job(job_id={jid!r}, wait_seconds=60) to follow it; "
                f"cancel_job(job_id={jid!r}) to stop it.")
    if state == "succeeded":
        if view["check"]:
            return "Validation passed: run the same arguments without check to launch it."
        return (f"Results are in {view['outdir']} (provenance/ holds the replay bundle)."
                + (" Read the caveats in status_report before using them." if view.get("caveats")
                   else ""))
    if state == "cancelled":
        return "Stopped. Resubmit with resume=true to continue from Nextflow's cache."
    if state == "lost":
        return ("The job's supervisor was killed (or the host restarted). status_report says "
                "whether nfclaw itself is still running; otherwise resubmit with resume=true.")
    return ("Read status_report / output_tail for the cause (docs: nfclaw://docs/known-issues), "
            "fix it, then resubmit" + (" with resume=true." if view.get("status_report") and
                                   not view["check"] else "."))


def _render_job(view: dict) -> str:
    phase = f" ({view['phase']})" if view.get("phase") else ""
    kind = ("check " if view["check"] else "") + view["kind"]
    lines = [f"job {view['job_id']}: {view['state']}{phase}",
             f"{kind}: {view['command']}", f"outdir: {view['outdir']}"]
    if view.get("exit_code") is not None:
        lines.append(f"exit code: {view['exit_code']}")
    if view.get("error"):
        lines.append(f"error: {view['error']}")
    if view.get("status_report"):
        lines += ["", "nfclaw status:", view["status_report"]]
    if view.get("output_tail"):
        lines += ["", f"output (last {len(view['output_tail'])} lines of {view['output_log']}):",
                  *view["output_tail"]]
    lines += ["", f"next: {view['next']}"]
    return "\n".join(lines)
