# nf-claw over MCP

`nfclaw mcp` serves the nf-claw library and runner to any [Model Context Protocol](https://modelcontextprotocol.io)
client — Claude Code, Codex, Antigravity, Hermes, MCP Inspector, the official SDKs — on stdin/stdout. It is part
of the `nfclaw` command and adds no dependency: the server is standard-library Python.

Pipeline execution uses the existing CLI; replay uses the bundle's existing guarded script.
Library and bounded artifact previews read their existing files. Runs, chains and replays execute as **detached jobs** that keep going when the client disconnects, and are followed by
job id. The agent docs (`skill.md`, `reference.md`, `AGENTS.md`, `docs/`) are served unchanged.

---

## Navigation

[Setup](#setup) • [Tools](#tools) • [Jobs](#jobs-long-analyses-and-chains) • [Resources and prompt](#resources-and-prompt) • [Environment](#environment) • [Protocol](#protocol)

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

**Antigravity** — the app, the IDE and the `agy` CLI all read `~/.gemini/config/mcp_config.json`
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

nf-claw on another machine: start the server over `ssh`, and its jobs run on that host —
`claude mcp add nfclaw -- ssh -T host /abs/path/to/.venv/bin/nfclaw mcp` (or `command: ssh`,
`args: ["-T", "host", "/abs/path/to/.venv/bin/nfclaw", "mcp"]`). The remote command gets a
non-interactive shell's environment.

---

## Tools

| Tool | Runs | What it is for |
|---|---|---|
| `list_pipelines` | reads `catalog.json` | Find a pipeline by assay, data type, method or tool; shows its input and what it can feed. Ranks as `nfclaw list <keywords>` does. |
| `show_pipeline` | `nfclaw show` | The pipeline's `skill.md` (default) or `reference.md`; `grep` returns only matching lines; `version` reads another release's docs. |
| `list_versions` | `nfclaw versions` | Published releases, the pinned one marked, plus `dev`. |
| `chain_edges` | `nfclaw chain edges` | Which pipeline can follow which in a chain. |
| `run_pipeline` | `nfclaw run` | Start a run as a job. Every CLI flag is an argument; pipeline parameters go in `params`; `check: true` validates and prints the command. |
| `run_chain` | `nfclaw chain run` | Start a chain as a job, from the chain spec as JSON ([format](chaining.md)). |
| `replay_run` | recorded `provenance/commands.sh` | Start a guarded replay as a supervised job in a fresh destination. |
| `read_artifact` | bounded file read | Preview UTF-8 text inside a job's outdir; reports truncation and rejects external symlinks/binary files. |
| `get_job` | `nfclaw status` | A job's state, nfclaw's status report and its latest output; `wait_seconds` returns as soon as it ends. |
| `list_jobs` | — | Jobs started through MCP, newest first. |
| `cancel_job` | `kill <nfclaw pid>` | Request process-group shutdown and outcome recording; detached/external executor work may need cleanup. |
| `run_status` | `nfclaw status` / `nfclaw chain status` | Any run or chain directory, including ones started from a shell; `chain: true` verifies lineage. |
| `verify_replay` | `nfclaw verify` | Compare a replay with the run it reproduces. |

The server's own instructions give agents the workflow: find → read the skill → `check` → run →
follow → results. Every tool asks Antigravity to load it up front (`_meta`
`antigravity/alwaysLoad`): deferred, its model called them
without their schemas, guessing arguments or passing its call tool's `toolSummary` among them.
Tool failures (an invalid argument, a refused launch) come back as results with
`isError` and nfclaw's own message — `[code] message`, the issues, and `fix:` — so the model can correct
the call. A parameter is refused if it is one of `nfclaw run`'s own options (`outdir`, `resume`, …:
those are arguments of the tool). Scalars, arrays and objects are accepted in `params`; structured
values are staged privately in a params file and still undergo the pipeline's schema validation.

Use absolute paths. A relative path means what it would on the command line in the directory the
client started the server from.

---

## Jobs: long analyses and chains

`run_pipeline` and `run_chain` start `nfclaw run …` / `nfclaw chain run …` as a job and return its id,
after waiting up to `wait_seconds` (default 20) so that a refused launch — invalid parameters, a
non-empty `--outdir`, a failed preflight check — is reported in the same call. The analysis itself
can take days; nothing needs to stay connected:

- A job runs in its own session under a small supervisor (`python -m runner.jobs`), which runs the
  CLI unmodified. The MCP client closing, or the server restarting, does not stop it.
- Its record is on disk, in `$NFCLAW_STATE_DIR/jobs/<id>/` (default `~/.local/state/nfclaw/jobs/`):
  `job.json` (the command line and directory), `output.log` (everything nfclaw and Nextflow
  printed), `supervisor.json` (pids and exit code). Any later server — another session, another
  client — reads it back.
- The supervisor holds a lock on the job for as long as it lives, so "running" never rests on a pid
  that could have been reused.

`get_job` reports `running` (with `phase`: `preparing` while nfclaw validates, stages inputs or
probes configs; `launched` once it has started Nextflow, until its run log records the outcome —
provenance included; `finishing` for the moment between that record and the job's exit), then
`succeeded`, `failed`, `cancelled`, or `lost` (the supervisor was killed outright or the host
restarted; the status report then says whether nfclaw itself still runs). Once a run has reached its
run log, the result includes `nfclaw status`'s report — the outcome, the error with Nextflow's own
message, completion caveats, and the log paths. A finished job whose own report could not be
retained says why in `status_error`; `run_status(outdir)` then reads the live log.

Long-poll with `get_job(job_id, wait_seconds=N)`, keeping `N` below your client's tool timeout; the
job is not affected when a call returns or is cancelled. Clients that send a progress token receive
progress notifications while a call waits.

`cancel_job` sends the job SIGTERM, requesting the same process-group shutdown and outcome
recording as `kill <nfclaw pid>` from a shell. Detached containers, scheduler jobs and host crashes
can leave external work running or evidence unfinished. Inspect the executor and reconcile that
work before continuing with `resume: true`; a cancelled or lost MCP label alone does not prove
every task has stopped. A second job into an
`outdir` that a running job holds is refused with that job's id (nfclaw's own `--outdir` lock is the
authority either way), so retrying a submission cannot start a run twice.

**Chains.** `run_chain` takes the chain spec ([format](chaining.md)) as a JSON object, writes it into
the job's directory, and runs `nfclaw chain run`: each stage starts only after the previous one
succeeded, from inputs prepared out of that stage's checksummed outputs. Validate first with
`check: true`; continue a failed chain with `resume: true`; verify its lineage with
`run_status(outdir, chain: true)`.

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
| `NFCLAW_STATE_DIR` | `$XDG_STATE_HOME/nfclaw`, else `~/.local/state/nfclaw` | Where job records are kept. |
| `NFCLAW_MCP_COMMAND_TIMEOUT` | 300 | Seconds a foreground command (`show`, `versions`, `status`, `verify`, …) may take. |

Jobs need a POSIX system (Linux or macOS), as Nextflow does.

---

## Protocol

The server speaks MCP over stdio (newline-delimited JSON-RPC 2.0) and is dual-era:

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

Interoperability is tested against the official Python SDK in both eras (`tests/test_mcp_interop.py`,
run when `mcp` is installed). On 2026-10-24, with `nfclaw mcp` and its jobs on an IPv6-only Linux
server, an agent in each client below found nf-core/demo, read its skill, validated, ran and
followed it to a MultiQC report through these tools alone, fixing that host's first network failure
from nfclaw's error:

| Client | Protocol it chose |
|---|---|
| Claude Code 2.1.300 (macOS, server started over `ssh`) | `initialize`, 2025-11-25 |
| Codex 0.144.4 | `initialize`, 2025-06-18 |
| Antigravity CLI (`agy`) 1.4.7 | `server/discover`, 2026-07-28 |
| MCP Python SDK 2.3.0 (scripted: runs, a chain, cancel, resume, replay) | both |

Completed jobs retain a private snapshot of their own run status. Reusing the output directory
for a later retry does not replace an older job ID's outcome or caveats. Historical jobs without
that snapshot retain their supervisor outcome, but do not borrow a later run's status report.
Long polls use separate worker capacity so ordinary status, ping and cancellation requests remain
available. Malformed job records are rejected individually and omitted from global listing.

`run_pipeline.params` accepts arrays and objects as well as scalar values. Structured values are
merged with `params_file` into an exact-number JSON file inside the private job directory (0600);
explicit `params` values win. The user's source params file is preserved. Pipeline schemas still
determine which arrays/objects are valid.

`verify_replay(require_environment=true)` requests the CLI's `--require-environment` gate. It
requires complete matching environment evidence even when output structure agrees; combine it
with `strict=true` to require identical output bytes as well.

`replay_run(original, outdir)` reuses the original bundle's guarded replay script under the same
job supervisor as runs and chains. It supports detached execution, status and cancellation. Keep
the original bundle; the replay directory contains its results and execution records, not a new
complete replay bundle. A retry needs a new empty destination.

`read_artifact(job_id, path, max_bytes=16384)` previews at most 65536 bytes of UTF-8 text. The path
is relative to that job's output directory. Traversal, binary files, nonregular files and symlinks
outside the output tree are refused. For external published symlinks, inspect them explicitly on
the server. A running job's preview may be incomplete and does not validate scientific results.
