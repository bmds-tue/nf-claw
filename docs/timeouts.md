# Timeouts, long analyses and monitoring

`nfclaw run` and `nfclaw chain run` have **no overall time limit by default**.
No output-silence watchdog or automatic cancellation is enabled. An analysis may
legitimately spend hours computing, waiting for a queue or downloading references.

---

## Navigation

[Execution Budgets](#explicit-execution-budgets) • [Safety Margins](#configurable-safety-margins) • [Detached Execution](#detached-execution) • [Monitoring vs Verification](#cheap-progress-versus-verification)

---

## Explicit execution budgets

`--timeout SECONDS` opts into one monotonic deadline, beginning before preparation.
For a chain, preparation, every stage and every retry share that deadline. A stage
does not receive a fresh budget. The remaining duration is checked again immediately
before launch, and an expired budget cannot produce a successful run outcome.

Most runner metadata subprocesses use the smaller of their operation limit and the
remaining execution budget. File inventories, hashing and filesystem operations
finish at safe boundaries; these are cooperative checks, not a guarantee that a
blocked filesystem call returns at a particular instant. Shutdown and failure
provenance recording may continue beyond the requested deadline to preserve evidence.
Keep additional time outside nfclaw for this work when a scheduler or CI job has a
hard cutoff. A failed or incomplete provenance bundle never certifies success.

Completion recording can query Nextflow task history and container engines and
refetch validation-only remote tables. These recorder probes have their own operation
limits, capped by the remaining execution budget, rather than the `NFCLAW_*` overrides
below. Institutional-config branch resolution has a 30-second per-lookup cap, also
bounded by the remaining active execution budget. Its supervised helper is stopped
when that budget expires; the normal shutdown/evidence-recording limits still apply.

`--limit-time DURATION` is separate: it caps each task's requested runtime, including
retry growth, through Nextflow's `process.resourceLimits`. Use it only for a deliberate
task/queue limit, not as an estimate of the whole analysis. Executor support and
pipeline-specific task settings still apply. Replays retain task resource limits;
they start a new execution and do not inherit the original run's execution deadline.

## Configurable safety margins

These environment variables accept finite, strictly positive seconds. Unset variables
retain the historical defaults; invalid values produce an explicit error. They do
not create an overall analysis deadline.

| Variable | Default | Applies to |
|---|---|---|
| `NFCLAW_SHUTDOWN_GRACE` | 10 | SIGTERM-to-SIGKILL grace for owned process groups |
| `NFCLAW_CONFIG_TIMEOUT` | 300 | Each chain configuration probe |
| `NFCLAW_VERSION_TIMEOUT` | 30 | Engine/runtime metadata probes |
| `NFCLAW_DOCKER_TIMEOUT` | 60 | The `docker info` daemon check before a Docker-profile run |
| `NFCLAW_GIT_TIMEOUT` | 10, 30, 60 or 120 by operation | Local Git checks, remote discovery and fetching |
| `NFCLAW_INIT_TIMEOUT` | 300 | Pipeline submodule initialization |

For a slow executor, increase shutdown grace according to measured cancellation
latency. Increase probe limits when deliberate cold setup needs longer, rather than
raising all limits. An explicit execution budget still takes precedence over setup
limits. Shutdown grace is captured at launch, recorded in `run_manifest.json`, and
embedded into new standalone replay scripts. Historical replay scripts keep their
ten-second default. Nextflow remains responsible for executor-specific remote-job
and container cleanup; process-group signaling cannot cover escaped processes.

## Detached execution

Detach the **whole nfclaw controller**, leaving Nextflow supervised by it:

```bash
NFCLAW_SHUTDOWN_GRACE=60 nohup nfclaw chain run spec.json \
  --outdir /data/analysis > /data/controller.log 2>&1 < /dev/null &
```

Use distinct output and work directories. The controller owns locks, stage sequencing,
handoff checks and final provenance. Backgrounding Nextflow separately would break
that completion contract. A service manager or scheduler can supervise the controller
for unattended work; nohup alone does not recover a failed host or process. Do not
automatically restart scientific work without inspecting its recorded outcome.

## Cheap progress versus verification

`nfclaw status OUTDIR` already reads execution logs without hashing results. To also
list chain stages cheaply, use `nfclaw chain status OUTDIR --quick`. Its output says
`lineage: not checked`; exit zero means recorded execution success, not verified data.

Normal `nfclaw chain status OUTDIR` continues to hash data and verify full lineage.
Use it at completion and audit checkpoints. Full integrity checks at handoff, resume
and chain completion remain mandatory; quick monitoring does not bypass them.
