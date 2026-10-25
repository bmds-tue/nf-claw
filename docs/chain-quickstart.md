# Chain quickstart

## To chain pipelines (A, then B, then C)

Several pipelines in sequence — each stage starts only after the previous one **succeeded**, and its inputs are prepared from that stage's outputs (fetchngs → rnaseq: fetchngs's samplesheet becomes rnaseq's `--input`). Write a spec (JSON) and run it:
```json
{
  "nxf_env": {"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"},
  "stages": [
    {"pipeline": "fetchngs", "input": "/abs/ids.csv", "retries": 2},
    {"pipeline": "rnaseq", "params": {"genome": "GRCh38"}}
  ]
}
```

Preflight check first:
```bash
nfclaw chain run spec.json --outdir /abs/chain --check
```
It validates every stage, every handoff, and verifies that every stage's config parses with its target engine (`nextflow config`), leaving `--outdir` untouched — then run the same without `--check`. Unavailable engines and timed-out configuration probes block the chain before any stage launches.

Which pipeline can follow which: `nfclaw chain edges [name]`, or the `## Chaining` section of a `skill.md`; without a rule there is no chain (or give the stage an inline `"handoff"`).

- **Stage parameters:** A stage's `params` are its own flags (look them up in its `reference.md`). Explicit stage `input` and `params` values override mapped handoff values with an advisory; unused sources are not materialized, though the rule must still pass static checks. Values in `params_file` have lower priority and do not suppress mapped sources. `demo: true` adds that release's `test` profile.
- **Engine tuning:** Run options (`profile`, `nxf_ver`, `nxf_env`, `config`, `limits`) go on the chain or on a stage: releases of different ages can need different engines (`"nxf_ver": "25.10.4"` on an older one).
- **Option inheritance:** Stage `nxf_env` merges over chain-level values; stage `config` and `limits` replace the entire inherited list/object. Include shared configs explicitly when overriding. `--timeout SECONDS` opts into one shared deadline for preparation, stages, retries and completion checks; cleanup/failure recording may finish beyond it. Each config probe defaults to 300 seconds (`NFCLAW_CONFIG_TIMEOUT`); all analyses remain unlimited without `--timeout`. [Timeouts and long analyses](timeouts.md) documents configurable margins and whole-controller background execution. `nfclaw chain status OUTDIR --quick` avoids data hashing and explicitly leaves lineage unchecked; normal chain status retains full verification.
- **Chain locking:** Concurrent chain processes targeting the same `--outdir` are blocked by an exclusive POSIX flock on `<outdir>/chain/.lock`.
- **Logs and state:** Each stage is an ordinary run in `<outdir>/NN-<stage>/`, with its own run log and provenance. The chain logs to `<outdir>/chain/logs/chain.log`; its **last line** is `==> nfclaw chain finished <time>: <outcome>` — poll it with `tail -n 1` for a background chain (`nohup nfclaw chain run ... &`); `kill <pid>` stops it cleanly. Per-stage state: `<outdir>/chain/state.json`.
- **Verification and safety:** Before feeding stage outputs into a downstream stage, the handoff engine verifies upstream file bytes against `outputs.sha256` and the complete published namespace against `outputs.inventory.json`, including empty directories, entry types and link identities. Local reference handoffs also require the producer's input namespace and byte records. Directory handoffs record their complete boundary inventory, and chain status compares it with the downstream prelaunch inventory after the schema-defined root canonicalization. A whole-run-directory handoff preserves every entry, including execution records; published results remain anchored to their original manifest, while the complete directory is recorded separately at the handoff boundary. Metagenomic assembly handoffs (fetchngs → mag, detaxizer → mag) isolate individual samples (`group: {sample}`) to avoid accidental multi-sample co-assembly pooling.
- **Resuming:** A failed chain continues with `nfclaw chain run [spec.json] --outdir /abs/chain --resume`: succeeded stages are skipped (and frozen), the failed one — which you may edit in the spec — resumes with Nextflow's cache. `"retries": N` relaunches a stage automatically after a pipeline failure (never after a validation error).
- **Lineage check:** `nfclaw chain status <outdir>` reconstructs the chain and verifies every link by SHA-256 (which run's outputs became which run's inputs); like `nfclaw status` (which also reads a chain's `--outdir`) it exits 0 succeeded, 3 still running, 1 otherwise — a chain whose nfclaw was killed outright is reported "stopped without an outcome". Spec, rules and failure modes: [`docs/chaining.md`](chaining.md).

---

