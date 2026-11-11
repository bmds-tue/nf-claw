# Timeouts, long analyses and monitoring

`nfclaw run` and `nfclaw chain run` have **no overall time limit by default**. Nothing cancels a run
because it is slow or quiet: an analysis may spend hours computing, waiting in a queue or
downloading references. This page covers the optional deadline, the shorter limits on nfclaw's own
setup and shutdown steps, running in the background, and checking progress cheaply.

---

## Navigation

[Deadlines](#explicit-execution-budgets) • [Setup and shutdown limits](#configurable-safety-margins) • [Running in the background](#detached-execution) • [Progress versus verification](#cheap-progress-versus-verification)

---

## Explicit execution budgets

`--timeout SECONDS` sets one deadline, counted from before preparation starts. In a chain,
preparation, every stage and every retry share that deadline; a stage does not get a fresh one. The
remaining time is checked again just before launch, and a run whose budget has run out cannot end
as a success.

Most of nfclaw's own helper commands use the smaller of their own limit and the time left. File
listings, hashing and other filesystem work stop at safe points between steps, so a filesystem call
that blocks can still overrun the deadline. Shutting down and recording a failure's provenance may
also continue past the deadline, to keep the evidence. If a scheduler or CI job has a hard cutoff,
leave some time for this outside nfclaw. A failed or incomplete provenance bundle never counts as a
success.

When a run finishes, recording its provenance can query Nextflow's task history and the container
engine and fetch validation-only remote tables again. These steps have their own limits, capped by
the time left, rather than the `NFCLAW_*` settings below. Resolving the nf-core/configs branch has a
30-second limit per lookup, also capped by the time left; its helper is stopped when the deadline
passes, and the normal shutdown and recording limits still apply.

`--limit-time DURATION` is something else: it caps how long each task may run, retries included,
through Nextflow's `process.resourceLimits`. Use it only as a deliberate per-task or queue limit, not
as an estimate for the whole analysis; the executor's support and the pipeline's own task settings
still apply. Replays keep the task limits, but a replay is a new execution and does not inherit the
original run's deadline.

## Configurable safety margins

These environment variables take a finite number of seconds greater than zero. Unset, they keep the
defaults below; an invalid value is an error. None of them sets a deadline for the analysis.

| Variable | Default | Applies to |
|---|---|---|
| `NFCLAW_SHUTDOWN_GRACE` | 10 | Time between SIGTERM and SIGKILL for the process groups nfclaw owns |
| `NFCLAW_CONFIG_TIMEOUT` | 300 | Each configuration probe (`nfclaw run --check`, and each chain stage) |
| `NFCLAW_VERSION_TIMEOUT` | 30 | Engine and runtime version probes |
| `NFCLAW_DOCKER_TIMEOUT` | 60 | The `docker info` check before a Docker-profile run |
| `NFCLAW_GIT_TIMEOUT` | 10, 30, 60 or 120, by operation | Local Git checks, remote lookups and fetches |
| `NFCLAW_INIT_TIMEOUT` | 300 | Initialising a pipeline submodule |
| `NFCLAW_MCP_COMMAND_TIMEOUT` | 300 | Each MCP command that answers at once ([MCP environment](mcp.md#environment)) |

On a slow executor, raise the shutdown grace to match how long cancelling actually takes. Raise a
probe limit only when a cold setup needs it, rather than raising them all. A `--timeout` deadline
still takes precedence over these limits. The shutdown grace in force at launch is recorded in
`run_manifest.json` and written into new replay scripts; replay scripts written before this keep
the 10-second default.

After the grace period, nfclaw (and a replay's supervisor) force-removes every Docker or Podman task
container that the run's own processes started and that still exists, because a task wrapper killed
while `docker stop` waited on the container's first process never removes it. The engine may still
be creating a container when its client is stopped, so nfclaw keeps looking for containers it does
not see yet, for up to 30 seconds in total. A container that has not appeared by then is named on
stderr and in the run log, with how to find and remove it: on a heavily loaded host the engine can
take longer, and such a container stays behind without ever starting. Scheduler jobs and other
executors' remote work remain Nextflow's responsibility; signalling the process group cannot reach
processes that left it.

## Detached execution

To run in the background, detach the **whole nfclaw process**, which keeps supervising Nextflow:

```bash
NFCLAW_SHUTDOWN_GRACE=60 nohup nfclaw chain run spec.json \
  --outdir /data/analysis > /data/controller.log 2>&1 < /dev/null &
```

Use separate output and work directories. nfclaw holds the locks, runs the stages in order, checks
the handoffs and writes the final provenance; putting Nextflow in the background on its own would
skip all of that. A service manager or scheduler can supervise nfclaw for unattended work, but
`nohup` alone does not recover from a failed host or process. Do not restart scientific work
automatically without looking at its recorded outcome.

## Cheap progress versus verification

`nfclaw status OUTDIR` reads the logs without hashing any results. To list a chain's stages just as
cheaply, use `nfclaw chain status OUTDIR --quick`. It prints `lineage: not checked`, and exit code 0
then means only that the stages recorded success, not that their data was verified.

`nfclaw chain status OUTDIR` without `--quick` hashes the data and verifies the whole lineage. Use it
when the chain finishes and whenever you need to audit it. The checks at each handoff, on resume and
at the end of a chain always run; `--quick` monitoring does not skip them.
