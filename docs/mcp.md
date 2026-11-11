# nf-claw over MCP

`nfclaw mcp` serves the nf-claw library and runner over stdin/stdout to any
[Model Context Protocol](https://modelcontextprotocol.io) client: Claude Code, Codex, Antigravity,
Hermes, MCP Inspector or the official SDKs. It is part of the `nfclaw` command and needs no extra
dependency, because the server is written in standard-library Python.

The tools run the same `nfclaw` commands as the CLI, and a replay runs the bundle's own guarded
script. Runs, chains and replays become **detached jobs** that keep going when the client
disconnects, and are followed by job id. The agent docs (`skill.md`, `reference.md`, `AGENTS.md`,
`docs/`) are served as they are in the repository.

---

## Navigation

[Setup](#setup) • [Tools](#tools) • [Jobs](#jobs-long-analyses-and-chains) • [Foreground Commands](#foreground-commands) • [Privacy](#privacy-and-redaction) • [Resources and Prompt](#resources-and-prompt) • [Environment](#environment) • [Protocol](#protocol)

---

## Setup

Install nf-claw as the [README](../README.md#quickstart) describes (`pip install -e .` in a virtualenv,
on a space-free path), then register the server with your client. Use the `nfclaw` from that
virtualenv, by absolute path if the client does not start from your shell.

**Claude Code**
```bash
claude mcp add --scope user nfclaw -- /abs/path/to/.venv/bin/nfclaw mcp
claude mcp list                 # nfclaw: … - ✔ Connected
```

**Codex** (`~/.codex/config.toml`)
```toml
[mcp_servers.nfclaw]
command = "/abs/path/to/.venv/bin/nfclaw"
args = ["mcp"]
tool_timeout_sec = 120          # a tool waits at most this long; jobs are unaffected
env_vars = ["PATH", "HOME", "JAVA_HOME", "NXF_OPTS"]
```
Codex asks before calling a tool that is not read-only (`run_pipeline`, `run_chain`, `cancel_job`).
`codex exec` has no one to ask and cancels the call (`user cancelled MCP tool call`); to run
pipelines from it, approve those tools in the same file:
```toml
[mcp_servers.nfclaw.tools.run_pipeline]
approval_mode = "approve"       # likewise for run_chain and cancel_job
```

**Antigravity** (the app, the IDE and the `agy` CLI all read `~/.gemini/config/mcp_config.json`)
```json
{"mcpServers": {"nfclaw": {"command": "/abs/path/to/.venv/bin/nfclaw", "args": ["mcp"]}}}
```
Antigravity stops a tool call after 3 minutes, whatever progress it reports, so `get_job` waits
there should stay below 180 seconds (the job itself is unaffected).

**Hermes** (`~/.hermes/config.yaml`)
```yaml
mcp_servers:
  nfclaw:
    command: /abs/path/to/.venv/bin/nfclaw
    args: [mcp]
    timeout: 180                # per tool call; jobs are unaffected
```

**Any other client** (the common `mcpServers` JSON)
```json
{"mcpServers": {"nfclaw": {"command": "/abs/path/to/.venv/bin/nfclaw", "args": ["mcp"]}}}
```

Without an install, use the checkout's interpreter: `command: python3`, `args: ["-m", "runner", "mcp"]`,
`cwd: /abs/path/to/nf-claw`. To try the server by hand:
`npx @modelcontextprotocol/inspector nfclaw mcp`.

To use nf-claw on another machine, start the server over `ssh`; its jobs then run on that host:
`claude mcp add nfclaw -- ssh -T host /abs/path/to/.venv/bin/nfclaw mcp` (or `command: ssh`,
`args: ["-T", "host", "/abs/path/to/.venv/bin/nfclaw", "mcp"]`). The remote command gets the
environment of a non-interactive shell.

---

## Tools

| Tool | Runs | What it is for |
|---|---|---|
| `list_pipelines` | reads `catalog.json` | Find a pipeline by assay, data type, method or tool; shows its input and what it can feed. Ranks as `nfclaw list <keywords>` does. |
| `show_pipeline` | `nfclaw show` | The pipeline's `skill.md` (default) or `reference.md`; `grep` returns only matching lines; `version` reads another release's docs. |
| `list_versions` | `nfclaw versions` | Published releases, the pinned one marked, plus `dev`. |
| `chain_edges` | `nfclaw chain edges` | Which pipeline can follow which in a chain. |
| `read_doc` | reads `docs/<name>.md` | A guide (`known-issues`, `chaining`, `replay`, …); `search` returns only the sections holding every word, e.g. a warning's, instead of the 120 KB symptom index. |
| `run_pipeline` | `nfclaw run` | Start a run as a job. Every CLI flag is an argument; pipeline parameters go in `params`; `check: true` validates and prints the command. |
| `run_chain` | `nfclaw chain run` | Start a chain as a job, from the chain spec as JSON ([format](chaining.md)). |
| `replay_run` | recorded `provenance/commands.sh` | Start a guarded replay as a supervised job in a fresh destination. |
| `read_artifact` | bounded file read | Preview UTF-8 text inside a job's outdir; reports truncation and rejects external symlinks/binary files. |
| `get_job` | `nfclaw status` | A job's state, nfclaw's status report and its latest output; `wait_seconds` returns as soon as it ends. |
| `list_jobs` | — | Jobs started through MCP, newest first. |
| `cancel_job` | `kill <nfclaw pid>` | Request process-group shutdown and outcome recording; detached/external executor work may need cleanup. |
| `run_status` | `nfclaw status` / `nfclaw chain status` | Any run or chain directory, including ones started from a shell; `chain: true` verifies lineage. |
| `verify_replay` | `nfclaw verify` | Compare a replay with the run it reproduces. |

The server's instructions give agents the workflow: find, read the skill, `check`, run, follow, read
the results. Every tool asks Antigravity to load it up front (`_meta` `antigravity/alwaysLoad`):
when the tools were loaded lazily, its model called them without their schemas, guessed arguments
or passed its own `toolSummary` field among them. A failed call (an invalid argument, a refused
launch) comes back as a result with `isError` and nfclaw's own message (`[code] message`, the
issues and a `fix:` line), so the model can correct the call. A parameter in `params` is refused if
it is one of `nfclaw run`'s own options (`outdir`, `resume`, …), because those are arguments of the
tool. `params` accepts scalars, arrays and objects; structured values are written to a private
params file and still go through the pipeline's schema validation.

Use absolute paths. A relative path means what it would on the command line in the directory the
client started the server from.

### Tool details

- **`run_pipeline.params`** accepts arrays and objects as well as scalar values. Structured values
  are merged with `params_file` into a JSON file (numbers kept exact) in the private job directory
  (mode 0600); explicit `params` values win, and your own params file is left unchanged. The
  pipeline's schema still decides which arrays and objects are valid.
- **`verify_replay(require_environment=true)`** adds the CLI's `--require-environment` check: complete,
  matching environment evidence even when the outputs agree. Add `strict=true` to require identical
  output bytes as well.
- **`replay_run(original, outdir)`** runs the original bundle's guarded replay script under the same
  job supervisor as runs and chains, so it is detached and can be followed and cancelled. Keep the
  original bundle: the replay directory holds the replay's results and execution records, not a new
  complete bundle. A retry needs a new, empty destination.
- **`read_artifact(job_id, path, max_bytes=16384)`** shows at most 65536 bytes of UTF-8 text from a
  path relative to the job's output directory. Paths that leave the directory, binary files, special
  files and symlinks pointing outside the output directory are refused; look at those on the server
  itself. A running job's files may be incomplete, and a preview does not validate results.
- **`list_versions`** still shows the committed pin in a clone that is offline, has no tags and has
  no initialised submodule. Its notes say which releases were seen on the remote, which tags are
  cached locally and when a pin's tag could not be confirmed; that fallback pin does not make other
  remote releases selectable.

---

## Jobs: long analyses and chains

`run_pipeline` and `run_chain` start `nfclaw run …` or `nfclaw chain run …` as a job and return its
id. They first wait up to `wait_seconds` (default 20), so that a refused launch (invalid parameters,
a non-empty `--outdir`, a failed preflight check) is reported in the same call. The analysis itself
can take days, and nothing needs to stay connected:

- A job runs in its own session under a small supervisor (`runner.jobs`, started with the server's
  Python), which runs the CLI unmodified. Closing the MCP client or restarting the server does not stop it.
- Its record is on disk in `$NFCLAW_STATE_DIR/jobs/<id>/` (default `~/.local/state/nfclaw/jobs/`):
  `job.json` (the command line, inherited `NXF_*` values and directory), `output.log` (everything
  nfclaw and Nextflow printed), `supervisor.json` (pids and exit code) and `child.json` (when and
  how the process was started, written before the command runs). The records are private (mode
  0600 in a 0700 directory). Any later server, from another session or another client, reads them
  back.
- The supervisor holds a lock on the job for as long as it lives, so "running" never depends on a
  pid that could have been reused. If the supervisor dies, a command that is still running can be
  identified by its boot and namespace, owner and exact start time. On Linux, cancellation also
  uses a pidfd.

`get_job` reports `running`, with a `phase`: `preparing` while nfclaw validates, stages inputs or
probes configs; `launched` from the start of Nextflow until the run log records the outcome
(provenance included); and `finishing` between that record and the job's exit. It then reports
`succeeded`, `failed`, `cancelled` or `lost`. A command that is confirmed to be still running after
its supervisor died stays `running` with `phase: orphaned` and can be cancelled. If its identity
cannot be confirmed, the outcome is `lost`: an identity that cannot be read does not prove that the
command ended. Old records without a start identity have to be checked by hand against the
executor. Once a run has written its run log, the result includes `nfclaw status`'s report: the
outcome, the error with Nextflow's own message, completion caveats and the log paths. A job refused
before it opened a run log (invalid parameters into a fresh `--outdir`) has no such report; its
`output_tail` holds the refusal. A finished job whose report could not be kept says why in
`status_error`; `run_status(outdir)` then reads the log directly.

A finished job keeps a private copy of its own status report, so a later retry into the same output
directory does not change an older job's outcome or caveats. Older jobs without that copy keep their
supervisor's outcome but do not take over a later run's report. A malformed job record is rejected
on its own and left out of job lists.

Long-poll with `get_job(job_id, wait_seconds=N)`, keeping `N` below your client's tool timeout; the
job is not affected when a call returns or is cancelled. Clients that send a progress token receive
progress notifications while a call waits.

`cancel_job` sends the job SIGTERM. That asks for the same shutdown as `kill <nfclaw pid>` from a
shell: the process group stops, the outcome is recorded and the Docker or Podman task containers the
run started are removed. Scheduler jobs, other detached work and host crashes can leave work
running or records unfinished, so check the executor before continuing with `resume: true`; a
`cancelled` or `lost` label alone does not prove that every task stopped. A second job into an
`outdir` that a running job holds is refused with that job's id (nfclaw's own `--outdir` lock
decides in any case), so resubmitting cannot start a run twice.

### Manage jobs from the shell

The CLI reads the same persisted jobs as MCP, including after a client disconnects. Run on the
same host, as the same user, with the same `NFCLAW_STATE_DIR` (or state-directory defaults):

```bash
nfclaw jobs list                              # newest 20 jobs
nfclaw jobs list --state running --limit 50
nfclaw jobs status <job-id> --log-lines 40
nfclaw jobs status <job-id> --log-lines 0 --json
nfclaw jobs cancel <job-id> --json
```

These commands manage jobs started through MCP. Foreground runs and runs started with `nohup` have
no job ID; use `nfclaw status <outdir>` for those. Nothing cleans up the job store: delete a finished
job's directory under `$NFCLAW_STATE_DIR/jobs/` once you no longer need its report. The run's own
results and log stay in its `--outdir`. The job commands need no pipeline files, no Nextflow and no
MCP client. `list` skips malformed records, filters before applying `--limit` (a positive number),
and returns an empty list when there are no jobs. `status` shows 20 lines of output by default;
`--log-lines 0` hides them. The output shown is at most the supervisor's last 64 KiB.

The state, command, output paths, times, recorded exit code, output and run report are the same as
in MCP's job view. A finished job shows its own saved report, completion caveats included, which a
later retry into the same output directory cannot replace. The `next` hint suggests CLI commands.

`cancel` asks the job's supervisor to shut down and returns at once, so a successful request can
still show `state: "running"`; check the status until it ends. `cancel_requested: true` means that
this command sent the request, not that every task has stopped. Cancelling a job that already ended
succeeds and does nothing (`cancel_requested: false`); an unknown or invalid ID is an error. The
limits on executor cleanup described above apply.

Every `--json` response is one object with `version: 1` and the command's `exit_code`:

| Command | Fields | Exit codes |
|---|---|---|
| `jobs list` | `jobs`: array of summaries (`job_id`, `kind`, `pipeline`, `state`, `check`, `outdir`, `created_at`, `finished_at`) | 0 on success, including an empty list; 1 on an operational error |
| `jobs status` | `job`: full MCP job view, with CLI `next` hints | 0 succeeded; 3 running; 1 failed, cancelled, lost or unknown |
| `jobs cancel` | `job`: current full view; `cancel_requested`: whether this call issued a request | 0 for an accepted request or an already-ended job; 1 on error |

On an operational error the object has an `error` string and `job` set to `null` (or `jobs` to
`[]`), and a readable message goes to stderr. When cancelling fails, `cancel_requested` may be
missing; when present, it says whether a request was sent before the error. Invalid command syntax
exits 2 with argparse's usage text on stderr, also with `--json`. An incompatible change to the JSON
will increase `version`.

### Chains as jobs

`run_chain` takes the chain spec ([format](chaining.md)) as a JSON object, writes it into
the job's directory, and runs `nfclaw chain run`: each stage starts only after the previous one
succeeded, from inputs prepared out of that stage's checksummed outputs. Validate first with
`check: true`; continue a failed chain with `resume: true`; verify its lineage with
`run_status(outdir, chain: true)`.

---

## Foreground commands

Tools that answer at once (`show_pipeline`, `run_status`, `verify_replay`, …) run their CLI command
under a separate process supervisor. A timeout, a cancelled request, a disconnect or the death of the
MCP server stops the command and its helpers, including metadata probes in other process groups. On
Linux, a subreaper adopts helpers whose parent exits; on macOS, nfclaw follows the process tree while
the command runs. If processes cannot be inspected, the command is refused before it starts, and a
process list that cannot be read during cleanup is reported as unconfirmed cleanup. Detached
analysis jobs are not affected by any of this.

One case is weaker on macOS: a helper that forks twice and is reparented before nfclaw sees it
cannot be traced by following the process tree, because Darwin refuses automatic descendant tracking
(`NOTE_TRACK`, see the
[kernel source](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_event.c)).
Linux's subreaper covers that case.

---

## Privacy and redaction

Job views, in the shell and over MCP, redact sensitive `NXF_*` values from commands, saved and live
diagnostics and output, following the provenance redaction rules. That covers overridden options,
quoted and JSON-escaped values, multi-line values and credentials cut off at the edge of the output
shown. The private environment of chains and stages, and the environment the server inherited, stay
available for redaction after a restart. Older records cannot redact values from the environment
that they never recorded. The raw execution records and logs on disk are not redacted; redact them
yourself before sharing them.

---

## Resources and prompt

| URI | Content |
|---|---|
| `nfclaw://guide` | `AGENTS.md` |
| `nfclaw://catalog` | `catalog.md` |
| `nfclaw://docs/{name}` | `docs/{name}.md` (chaining, timeouts, known-issues, mcp, …) |
| `nfclaw://pipelines/{pipeline}/skill` | the pipeline's `skill.md` (listed for every pipeline) |
| `nfclaw://pipelines/{pipeline}/reference` | the pipeline's `reference.md` |

The prompt `use_pipeline` (arguments `pipeline`, optional `goal`) returns a pipeline's `skill.md` with
the steps to validate, launch and follow it; Claude Code offers it as a slash command.

---

## Environment

Jobs inherit the server's environment, and clients start servers with a reduced one: Codex passes
only a few variables (on Linux `HOME`, `LANG`, `LOGNAME`, `PATH`, `SHELL`, `USER`) plus its
`env_vars`, Hermes a few too, and an app launched from a desktop may not have your shell's `PATH`.
If `nfclaw` reports `nextflow not found on PATH` or a missing `JAVA_HOME`, pass them in the
client's server configuration (`env` / `env_vars`). Per-run Nextflow settings are tool arguments:
`nxf_env`, `nxf_ver`, `config`, `limit_*`.

On an IPv6-only host the first run fails with `Network is unreachable` (Nextflow's JVM tries IPv4
first; see [known issues](known-issues.md#ipv6-only-host--jvm-cant-reach-github)), and nfclaw's
error names the fix. Pass it per run as `nxf_env: {"NXF_JVM_ARGS":
"-Djava.net.preferIPv6Addresses=true"}`, or once in the server's configuration, so that every job
has it and the first run already works. Claude Code (`-e` takes several values, so the name goes
before it):
```bash
claude mcp add --scope user nfclaw -e NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true \
  -- /abs/path/to/.venv/bin/nfclaw mcp
```
Codex: `env = { NXF_JVM_ARGS = "-Djava.net.preferIPv6Addresses=true" }` in its
`[mcp_servers.nfclaw]` table; Antigravity: `"env": {"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"}`.

| Variable | Default | Effect |
|---|---|---|
| `NFCLAW_STATE_DIR` | `$XDG_STATE_HOME/nfclaw` (when absolute), else `~/.local/state/nfclaw` | Where job records are kept; a relative value is resolved from the working directory. |
| `NFCLAW_MCP_COMMAND_TIMEOUT` | 300 | Seconds a foreground command (`show`, `versions`, `status`, `verify`, …) may take. |

Jobs need a POSIX system (Linux or macOS), as Nextflow does.

---

## Protocol

The server speaks MCP over stdio (newline-delimited JSON-RPC 2.0) and supports both generations of
the protocol:

- **2026-07-28** clients send their version in each request's `_meta`; there is no handshake.
  `server/discover` returns the supported versions, capabilities and instructions; every result
  carries `resultType`, and cacheable ones `ttlMs`/`cacheScope`. An unsupported version is refused
  with error `-32022` listing the supported ones.
- **2025-11-25, 2025-06-18, 2025-03-26 and 2024-11-05** clients open with `initialize` and are served
  under the version it negotiates; fields a version does not know (tool annotations, titles,
  `structuredContent`) are left out for it.

Requests are answered concurrently, so a waiting `get_job` never blocks another call;
`notifications/cancelled` ends a waiting call without a response. The server's stdout carries only
protocol messages: its own stray output, and that of any process it starts, goes to stderr. Closing
stdin ends the server, never a job.

Long polls and ordinary work each have a limited number of workers; a request beyond that gets a
retryable `server busy` JSON-RPC error (-32000). Quick job, status and cancel calls have workers of
their own, and ping is answered directly, so slow version lookups, source checkouts and verification
cannot block them. A chain status that hashes lineage counts as ordinary work. If a cancellation's
optional wait for completion cannot get a worker, the cancellation is still acknowledged and only the
wait is skipped.

Interoperability is tested against the official Python SDK in both protocol generations
(`tests/test_mcp_interop.py`, run when `mcp` is installed). On 2026-10-24, with `nfclaw mcp` and its jobs on an IPv6-only Linux
server, an agent in each client below found nf-core/demo, read its skill, validated, ran and
followed it to a MultiQC report through these tools alone, fixing that host's first network failure
from nfclaw's error:

| Client | Protocol it chose |
|---|---|
| Claude Code 2.1.300 (macOS, server started over `ssh`) | `initialize`, 2025-11-25 |
| Codex 0.144.4 | `initialize`, 2025-06-18 |
| Antigravity CLI (`agy`) 1.4.7 | `server/discover`, 2026-07-28 |
| MCP Python SDK 2.3.0 (scripted: runs, a chain, cancel, resume, replay) | both |
