# nf-claw — agent entry point

The library provides pinned nf-core pipelines under `pipelines/<name>/`: generated
`skill.md` and `reference.md`, plus vendor-clean `upstream/` source. General runner
behavior must remain pipeline-agnostic and schema-driven.

## Setup and core commands

Use Python 3.11+ and a space-free checkout/virtualenv (also avoid iCloud paths).
Install with `pip install -e '.[dev,yaml]'`; without installation, use
`python3 -m runner <command>` from the repository root. An installed distribution
can select a separate library with `NFCLAW_LIBRARY_ROOT` ([installation](docs/installation.md)).

1. Find a pipeline with `nfclaw list` or search `catalog.json`; do not load the entire catalog.
2. Read only its `pipelines/<name>/skill.md`. Look up additional parameters in its
   `reference.md`; never invent flags, values, input columns or references.
3. Validate with `nfclaw run <name> --input /data/samples.csv --outdir /data/results --check`.
4. Run the same command without `--check`. `nfclaw run` executes for real: there is
   **no preview/dry-run default**. `--demo` selects the upstream bundled test profile.
5. Follow with `nfclaw status /data/results` (or `--json`); inspect completion caveats,
   the run log, `.nextflow.log` and task commands before accepting results.

## Essential integrity rules

- Keep inputs, pipeline source and configuration separate from outputs, work,
  engine state and logs. Use absolute samplesheet data paths and a distinct
  output directory per analysis. Preserve writer locks and all boundary checks.
- Never silently rename scientific samples or alter biological parameters.
  Refuse unsafe/ambiguous identities and require explicit safe aliases.
- Never edit pinned upstream source to conceal incompatibilities. Narrow runtime
  corrections and role exceptions require exact-source guards and recorded evidence.
- `--resume` reuses valid cache only when local inputs and the effective analysis
  identity agree. Changed configurations preserve the previous run in a sibling
  archive and start fresh; see [resume policy](docs/resume-policy.md).
- Success does not establish completeness or biological accuracy. Stubs, ignored
  failures and skipped samples retain the original caveat text. Use
  `--reject-caveat any` or selected categories for strict [result acceptance](docs/result-acceptance.md).
- Replay into a fresh directory with `OUT/provenance/commands.sh /data/replay`.
  Keep the original bundle and required data/work files. `nfclaw verify` compares
  inventory; `--strict` additionally checks bytes and available environment evidence.
  Read [replay limits](docs/replay-guide.md) before claiming reproducibility.
- Analyses have no overall timeout by default. Set resource ceilings from actual
  capacity; time ceilings must be deliberate. Never stop unrelated analyses,
  prune shared containers/caches or overwrite scientific results.

## Read detailed guidance only as needed

| Task | Guide |
| --- | --- |
| Input contracts, generated samplesheets, safety, logs and failures | [Execution guide](docs/execution-guide.md) |
| Version selection, engine/profile/config settings, resource limits | [Engine guide](docs/engine-guide.md) |
| Replay dependencies, environment records and verification | [Replay guide](docs/replay-guide.md) |
| Chaining, handoffs, lineage, retries and resume | [Quickstart](docs/chain-quickstart.md), [specification](docs/chaining.md) |
| MCP clients, persistent jobs and reconnection | [MCP workflow](docs/mcp-workflow.md), [client setup](docs/mcp.md) |
| Diagnostics, JSON results, progress, job listing and retention | [Structured results](docs/structured-results.md) |
| Symptoms, upstream limitations and runtime corrections | [Known issues](docs/known-issues.md) |
| Optional deadlines, setup/shutdown margins and cancellation | [Timeouts](docs/timeouts.md) |

MCP jobs survive client disconnection. Keep polling waits below the client's call
limit (Antigravity: 180 seconds); the analysis itself keeps running. Use absolute
paths, `get_job` and `cancel_job`, and retain execution/lineage evidence.

## Development

Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing the repository. Preserve
uncommitted work. Add meaningful regression coverage for fixes. Generated skills,
references, catalogs and handoffs must agree with pinned source, remain deterministic
and contain no generated timestamps. Keep `AGENTS.md` and `CLAUDE.md` byte-identical.

Core gates: `make test`, `ruff check .`, `python3 -m librarian.check_drift`; run
`make build` when generated context changes. Website changes also require the
production export, type checks and browser regressions. See the contribution guide
for environment setup and [the validation ledger](docs/audit-implementation.md)
for the current implementation and server acceptance work.
