# Diagnostics, structured reports and job retention

`nfclaw doctor` checks the library selection, executables, bounded metadata
version probes, accessible container profiles and available disk space without
launching an analysis. It prints actionable issues and does not change services,
stop jobs or prune caches. Add `--json` for its versioned result. An unresolved
version remains `null`; diagnostic failures are not fabricated identities.

The following commands support `--json`:

```bash
nfclaw status /data/results --json
nfclaw chain status /data/chain --quick --json
nfclaw verify /data/replay --against /data/original --strict --json
nfclaw doctor --json
nfclaw jobs list --limit 20 --json
nfclaw jobs prune --older-than-days 30 --keep 20 --json
```

Each object has `schema_version: 1`. Status and verification include the human
`report`, their CLI `exit_code`, and structured evidence. Run status includes
`state` (`missing`, `running`, `success`, `ended`, `dead`, `elsewhere`), `outcome`,
timestamps, log paths, bounded recent output, completion conditions and acceptance.
Verification includes `passed`, `strict` and a `comparison` object containing file,
directory, link and environment differences. A chain report contains its recorded
`state`, integrity `problems` and exit code; quick mode explicitly leaves lineage
unchecked. New compatible fields may be added; consumers should ignore unknown
fields and require a supported schema version. Terminal failures and running state
retain the human CLI's exit codes: success 0, failure/unknown 1, running 3.

Task progress counts rows in an available Nextflow execution trace. These are
observations, not a workflow's eventual task count: `expected_tasks` is always
`null`, and `observed_tasks` is `null` when there is no reliable trace. Counts
include only recorded task IDs. Trace reading is bounded at 100,000 unique tasks;
`truncated: true` identifies a lower bound. No completion percentage is invented.
MCP status, verification and job views consume JSON results and expose the original
structured result; they do not infer caveats from human prose.

Job listing loads a bounded page of metadata in descending UTC job-ID order.
Use the previous result's `next_cursor` as `--before` (MCP `before`) to continue.
MCP `list_jobs` also supports state filtering. A final empty page returns a null
cursor; concurrent new jobs do not move an existing cursor forward.

Job pruning **previews by default**. Add `--apply` only after reviewing the eligible
IDs. It protects active supervisors with their actual lock, records lacking a
terminal outcome, the newest retained jobs, recent jobs, scientific output trees
and metadata used by recorded input/configuration dependencies. Applying pruning
removes only the known job metadata and console log. Run outputs, provenance,
work/engine caches, stored chain specifications and unknown files remain. Retained
job directories and lock files are intentional. A pruned job is no longer listed;
the scientific run can still be inspected directly with `nfclaw status OUTDIR`.
