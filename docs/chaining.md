# Chaining Pipelines

`nfclaw chain run` executes multiple nf-core pipelines in sequence (e.g. `fetchngs` → `rnaseq` → `differentialabundance`), initiating each subsequent stage only after the preceding stage has **succeeded**, and automatically preparing downstream inputs from upstream outputs.

It functions as a linear orchestrator:
- **No Complex Daemons:** No complex DAG syntax, no daemon processes, and no external scheduler dependencies.
- **Stage Isolation:** Every stage executes as a full, standard `nfclaw run` inside `<outdir>/NN-<stage>/`, with its own preflight parameter validation, sibling directory locking, run log, and provenance bundle.
- **Durable Orchestration:** Durable chain state, handoff snapshots, and unified logs are maintained in `<outdir>/chain/`.

```bash
nfclaw chain edges                                       # list all registered pipeline handoffs
nfclaw chain edges fetchngs                              # list handoffs originating from or feeding fetchngs
nfclaw chain run spec.json --outdir /abs/chain --check   # validate all stages and handoffs; run nothing
nfclaw chain run spec.json --outdir /abs/chain           # execute the full workflow
nfclaw chain status /abs/chain                           # inspect stage outcomes and verify cryptographic lineage
```

---

## Navigation

[Specification Format](#1-the-specification-file-specjson) • [Execution Lifecycle](#2-execution-lifecycle) • [Handoff Rules](#3-handoff-rules-and-transformations) • [Failure & Resume](#4-failure-recovery-and-resume) • [Cryptographic Lineage](#5-provenance-and-cryptographic-lineage)

---

## 1. The Specification File (`spec.json`)

The chain spec is authored in JSON (or YAML with `pip install -e ".[yaml]"`). Relative file paths in the spec resolve against the caller's working directory. The specification recorded in `<outdir>/chain/chain.json` is normalized to absolute paths.

```json
{
  "profile": "docker",
  "nxf_env": {"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"},
  "limits": {"cpus": 8, "memory": "30.GB"},
  "stages": [
    {
      "pipeline": "fetchngs",
      "input": "/data/accessions.csv",
      "retries": 2
    },
    {
      "pipeline": "rnaseq",
      "params": {"genome": "GRCh38"},
      "pipeline_version": "3.18.0"
    }
  ]
}
```

### Chain-Level Options
These settings apply globally to all stages. Individual stages can override the
execution options below; `allow_spaces` is a chain-only setting:

| Option | Type | Default | Description |
|---|---|---|---|
| `profile` | string | `"docker"` | Nextflow execution profile. |
| `nxf_ver` | string | `null` | Pin Nextflow engine version (`NXF_VER`) across all stages. |
| `nxf_env` | object | `{}` | `NXF_*` variables with string values passed to Nextflow (e.g. `{"NXF_OFFLINE": "true"}`). |
| `config` | array | `[]` | Additional Nextflow configuration files passed via `-c`. |
| `limits` | object | `null` | Global resource ceiling: `{"cpus": N, "memory": "SIZE", "time": "DURATION"}` (`process.resourceLimits`, Nextflow ≥ 24.04.0). `time` caps every task's run time, retries included: set it only as a deliberate ceiling. |
| `allow_spaces` | boolean | `false` | Allow filesystem paths containing spaces. |

### Stage-Level Keys
Options set on a stage override or merge with chain-level options:

| Key | Type | Required | Description |
|---|---|---|---|
| `pipeline` | string | Yes | Name of a tracked pipeline in the library. |
| `id` | string | No | Unique stage identifier (default: pipeline name; must match `^[a-z0-9][a-z0-9_-]*$`). |
| `input` | string/array/boolean | No | Explicit `--input` for the stage (typically stage 1); overrides a handoff's input if provided. A directory, glob or list of data files makes nfclaw generate the stage's samplesheet, as `nfclaw run` does. Use `false` only for an analysis mode that supports running without input. |
| `sheet_set` | object | No | Columns of that generated samplesheet no file name determines (`--sheet-set`), e.g. `{"strandedness": "auto", "patient": "{sample}"}`. Only for a stage whose `input` names data files. On `--resume`, a succeeded stage whose data now holds files it never analysed is refused — a resume would otherwise skip them without a word; data removed after it succeeded is not needed again. |
| `params` | object | No | Pipeline-specific parameters (e.g. `{"genome": "GRCh38", "aligner": "star_salmon"}`). Look up allowed flags in the pipeline's `reference.md`. |
| `params_file` | string | No | Path to an external parameter JSON or YAML file. |
| `pipeline_version` | string | No | Pinned release tag (e.g. `3.14.0`) or unreleased `dev`. |
| `demo` | boolean | No | Adds the pipeline's bundled `test` profile before the selected profiles. |
| `retries` | integer | No | Maximum automatic retries (using Nextflow `-resume`) upon task or pipeline failure (default: `0`). Never retries on schema errors. |
| `handoff` | object/string | No | Custom inline handoff rule object or path to a custom rule JSON file, replacing the library registry rule. |
| `nxf_ver` | string | No | Overrides engine version for this specific stage (essential when chaining an older pipeline release with a modern one). |
| `nxf_env` | object | No | Merges stage-specific `NXF_*` environment variables over chain-level variables. |
| `config` | array | No | Replaces the chain-level config list; include shared configs here too if needed. |
| `limits` | object | No | Replaces the entire chain-level limits object; `null` or `{}` disables inherited ceilings. |

---

## 2. Execution Lifecycle

```
┌────────────────────────────────────────────────────────────────────────┐
│ Preflight Verification Phase                                           │
│ 1. Spec Schema Validation: Verify syntax, stage IDs, and rule paths.  │
│ 2. Static Handoff Audit: Validate handoff sources against schemas.     │
│ 3. Parameter Check: Dry-run validate non-deferred stage parameters.    │
│ 4. Engine Config Probe: Run 'nextflow config' with per-stage engines. │
└────────────────────────────────────────────────────────────────────────┘
                                    │ (All checks pass)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Stage Execution Phase                                                  │
│ 1. Acquire Chain Lock: Non-blocking POSIX flock on chain/.lock.       │
│ 2. Execute Stage 1: Standard nfclaw run in 01-<id>/                   │
│ 3. Stage 1 Succeeded: Checksum outputs against outputs.sha256.         │
│ 4. Materialize Handoff: Transform outputs into chain/handoffs/02-<id>/ │
│ 5. Execute Stage 2: Standard nfclaw run in 02-<id>/                   │
│ 6. Finalize: Write final outcome to chain.log and state.json.          │
└────────────────────────────────────────────────────────────────────────┘
```

### Preflight Probing Before Launch
Before launching any pipeline, `nfclaw chain run` validates:
1. Every stage's pipeline and requested version exists and resolves.
2. Every handoff rule names valid parameters and provides columns compatible with the downstream input schema. Published paths are checked at handoff time; there is no general upstream output schema.
3. Every stage's explicit parameters pass preflight validation (parameters supplied by upstream handoffs and complex schema rules are deferred).
4. `nextflow config` resolves and parses configuration files under the exact Nextflow engine specified for each stage. A configuration syntax error in stage 3 fails immediately at minute 0, rather than crashing after stage 1 has executed for hours.

The configuration probe checks parsing and resolution, not the complete runtime
parameter contract or task execution. Handoff-derived values are validated when
they become available to the consuming stage.

`--check` performs the same preflight and configuration probes, leaving `--outdir`
untouched. It can fetch pipeline versions and populate engine caches. The probes' time
limit and the optional deadline one `--timeout` gives the whole chain are described in
[timeouts and long analyses](timeouts.md).

### Concurrency Locking
`runner/chain.py` locks `<outdir>/chain/.lock` via a non-blocking POSIX flock. If another chain process is active in the same directory, it terminates immediately with `ErrorCode.ENVIRONMENT`.

### Unified Logging
- The chain-wide execution log is written to `<outdir>/chain/logs/chain.log`.
- Background monitoring: `tail -n 1 <outdir>/chain/logs/chain.log` displays the terminal outcome line:  
  `==> nfclaw chain finished <timestamp>: <outcome>`
- `nfclaw chain status <outdir> --quick` lists recorded execution state without hashing
  outputs ([cheap progress versus verification](timeouts.md#cheap-progress-versus-verification)).
- Stopping a chain: `kill <pid>` stops the running stage cleanly, flushes the log, and shuts down Nextflow.

---

## 3. Handoff Rules and Transformations

Handoff rules describe how outputs published by an upstream pipeline are adapted into inputs for a downstream pipeline. Registered rules reside in `handoffs/<upstream>/<downstream>.json`.

Example: `handoffs/fetchngs/rnaseq.json`:
```json
{
  "description": "Feed fetched FASTQ samplesheet into rnaseq",
  "upstream_params": {
    "nf_core_pipeline": "rnaseq"
  },
  "params": {
    "input": {
      "samplesheet": "samplesheet/samplesheet.csv",
      "provides": ["sample", "fastq_1", "fastq_2", "strandedness", "instrument_platform"],
      "allowed_values": {
        "instrument_platform": ["ILLUMINA", "BGISEQ", "DNBSEQ", "ELEMENT", "ULTIMA", "ION_TORRENT", "LS454", "VELA_DIAGNOSTICS", "GENAPSYS", "GENEMIND", "TAPESTRI"]
      }
    }
  }
}
```

### Parameter Source Types

| Source Type | Description | Example |
|---|---|---|
| `samplesheet` | Copies and adapts an upstream samplesheet. `provides` declares guaranteed columns checked during static drift checks. | `fetchngs` → `rnaseq`, `fetchngs` → `mag` |
| `build` | Synthesizes a new samplesheet from matching output files. Uses `{placeholders}` for row grouping and column templating. | `bamtofastq` → `rnaseq` |
| `file` | Maps a single published output file to a downstream parameter. Globs must match exactly one file. A list of patterns is tried in order; `"paired_with": "<param>"` instead takes the pattern at the position the named parameter's list chose, so two files come from the same producer step. | `rnaseq` → `differentialabundance` (`--matrix`, and `--feature-length-matrix` paired with it) |
| `upstream_param` | Reuses a resolved parameter value from the upstream run's `params.json`. | `rnaseq` `--gtf` → `differentialabundance` `--gtf` |

Source paths are relative to the upstream output directory. A `file` source can be
an ordered list of fallback patterns; the first matching pattern must select exactly
one published file. Any source may set `"optional": true` to omit an unavailable
value, but checksum, namespace and downstream validation failures remain errors.
A `build` source supplies `rows` (a relative pattern with `{placeholders}`), `columns`
(column-to-template mappings) and optional `format` (`csv` by default, or `tsv`).
For a path column, a template ending in `?` leaves a missing companion file empty.
An optional `exhaustive` glob names files that must all reach a row: a file it matches that no
row uses, such as bamtofastq's single-end reads beside its paired ones, fails the handoff (even an
optional one) instead of being left out.

Explicit stage `input` and `params` values override mapped handoff parameters with an
advisory; unused sources are not materialized. The rule must still pass static checks.
A `params_file` supplies lower-priority values and does not suppress a mapped source.

An `upstream_param` reference uses the downstream parameter's declared path format (`file-path`,
`directory-path`, `path` or `file-path-pattern`). Relative local references are anchored to the
producer's launch directory, including references supplied by its profile. File patterns retain
their selection and require historical byte and namespace evidence for every member. The
consumer's prelaunch record must match that selection; a file added during consumption and
removed later still breaks lineage. A pattern referring to external input data requires the
producer's supported prelaunch input inventory, not only legacy file checksums.

### Samplesheet Transformations
When `samplesheet` is used, transformations are applied in a strict, predictable order:
1. `rename`: Rename columns (`{"fastq_1": "short_reads_1"}`).
2. `set`: Set values or template expressions for every row (`{"lane": "{run_accession}"}`).
3. `add_empty`: Insert declared columns that the upstream sheet lacks.
4. `drop_rows_not_allowed`: Filter out rows containing values rejected by the downstream schema.
5. `allowed_values`: Refuse (never drop) the handoff when a column holds a value outside a list — rows the downstream must not analyse although its schema cannot tell, such as a long-read or colour-space run in fetchngs's sheet for a short-read pipeline (`{"instrument_platform": ["ILLUMINA", …]}`).
6. `require_values`: Assert that specific columns must contain non-empty values before launch.

`refuse_rows_in` lists other sheets the upstream writes for the same downstream that the handoff
cannot take with this one, such as detaxizer's `mag-se.csv` for samples without a second short-read
file beside `mag-pe.csv`: a row in any of them fails the handoff, naming the samples, instead of
leaving them out. A pattern that also matches the handed-over sheet never refuses that sheet.

> [!IMPORTANT]
> **Metagenomic Co-Assembly Safety:**
> In metagenomic workflows (`fetchngs` → `mag`, `detaxizer` → `mag`), nf-core/mag treats identical sample `group` identifiers as an instruction to pool reads across samples for co-assembly. To preserve biological integrity:
> - The default registered rules assign each sample its own independent group: `"group": "{sample}"`.
> - Pooling samples requires an explicit custom inline handoff rule accompanied by domain justification.

> [!IMPORTANT]
> **Sequencing platforms and study design are not inferred:**
> - nf-core/mag chooses its long-read preprocessing and assembler mode (e.g. Flye's ONT vs PacBio mode) by `long_reads_platform`. The `fetchngs` → `mag` rule takes each run's short-read platform from its ENA `instrument_platform` (fetchngs itself labels every run `ILLUMINA`), so a long-read run is refused instead of being analysed as Illumina short reads. detaxizer records no long-read platform: the `detaxizer` → `mag` rule refuses samples with long reads until an inline handoff names their platform, e.g. for PacBio HiFi data:
>   ```json
>   {"pipeline": "mag", "handoff": {
>     "upstream_params": {"generate_downstream_samplesheets": true, "generate_pipeline_samplesheets": "mag"},
>     "params": {"input": {"samplesheet": "downstream_samplesheets/mag-pe.csv",
>       "provides": ["sample", "run", "group", "short_reads_1", "short_reads_2", "long_reads"],
>       "set": {"group": "{sample}", "short_reads_platform": "ILLUMINA", "long_reads_platform": "PACBIO_HIFI"}}}}}
>   ```
> - The `fetchngs` rules into short-read pipelines (`rnaseq`, `atacseq`, `sarek`, `metatdenovo`, `viralrecon`) refuse runs whose ENA `instrument_platform` is not a short-read platform: long-read, capillary and colour-space runs are not analysed as if they were Illumina reads. ampliseq needs `--pacbio`/`--iontorrent` set for such runs.
> - `fetchngs` → `ampliseq` leaves `run` empty, so ampliseq learns one DADA2 error model for all samples; data from several sequencing runs needs `run` filled per sequencing run — an inline handoff whose `set` templates it from a column that identifies the run, or your own samplesheet.
> - `fetchngs` → `sarek` and `demultiplex` → `sarek` write no `status` or `sex`: sarek treats every sample as normal tissue and runs germline analyses only. A tumour/normal design needs its own sarek samplesheet: a handoff's `set` gives every row the same value.

---

## 4. Failure, Recovery and Resume

| Condition | Engine Behavior | Exit Code |
|---|---|---|
| **Preflight check failure** | No pipeline tasks launched; configuration probes may have run. Detailed diagnostic printed. | `1` |
| **Pipeline failure with `retries > 0`** | The failed stage is automatically relaunched using Nextflow `-resume`. | — |
| **Exhausted retries or non-retryable failure** | Chain execution halts immediately; downstream stages remain `pending`. | `1` |
| **Handoff generation failure (`[handoff_failed]`)** | Upstream stage marked succeeded; downstream stage not launched. | `1` |
| **Interrupt signal (`SIGINT`, `SIGTERM`, `SIGHUP`)** | Running stage shuts down Nextflow cleanly; logs finalized. | `128 + signal` / `130` |

### Resuming a Failed Chain
To continue a chain after fixing a parameter or environmental issue:
```bash
nfclaw chain run spec.json --outdir /abs/chain --resume
```

Omit `spec.json` to reuse the recorded specification unchanged.

When resuming:
1. **Succeeded Stages Frozen:** Succeeded stages are frozen and verified; modifying the spec for an already-succeeded stage is rejected.
2. **Cached Retries:** The failed stage resumes using Nextflow's cache when declared local input bytes and namespaces are unchanged. A handoff prepared again from unchanged upstream outputs keeps the files its failed attempt ran on, at the same paths. Changed inputs or an unavailable previous snapshot archive that stage's prior run and recompute all its tasks.
3. **Pipeline Extension:** New stages may be appended to the end of a completed chain to extend an existing analysis.

---

## 5. Provenance and Cryptographic Lineage

Chaining records checksum evidence for the links between stages:
- Each stage's `run_manifest.json` contains a `chain` block recording chain ID, stage index, and upstream dependencies.
- The handoff record stores its rule digest and dependency inventories. Downstream stages snapshot
  the handed-over local files and samplesheet in `inputs.sha256`.
- Upstream outputs are verified against `outputs.sha256` before ingestion by downstream handoffs.

Before feeding stage outputs into a downstream stage, the handoff engine verifies upstream file bytes against `outputs.sha256` and the complete published namespace against `outputs.inventory.json`, including empty directories, entry types and link identities. Local reference handoffs also require the producer's input namespace and byte records. Directory handoffs record their complete boundary inventory, and chain status compares it with the downstream prelaunch inventory after the schema-defined root canonicalization. A whole-run-directory handoff preserves every entry, including execution records; published results remain anchored to their original manifest, while the complete directory is recorded separately at the handoff boundary. Metagenomic assembly handoffs (fetchngs → mag, detaxizer → mag) isolate individual samples (`group: {sample}`) to avoid accidental multi-sample co-assembly pooling.

### Chain Verification (`nfclaw chain status`)
```bash
nfclaw chain status /abs/chain
```

The status command:
1. Validates that every completed stage manifest matches the recorded chain state.
2. Checks that live stage outputs on disk match their original `outputs.sha256` digests.
3. Compares handoff files and reference inventories with upstream evidence and the input hashes
   recorded by the downstream stage, including internal reference directories.
4. Exits with code `0` if all links are verified and complete, code `3` if stages are currently executing, and code `1` if any failure or discrepancy is detected.

These checks verify the recorded links and live outputs. They do not independently verify every
initial input or configuration, prove analytical accuracy, or authenticate evidence against someone
who can rewrite the entire bundle. Static rule checks use parameter/input schemas and declared
published paths; the repository has no general upstream output schema. File existence and historical
identity are checked at runtime. A configuration probe that fails to execute or times out blocks
both `--check` and execution, rather than being treated as a passing result.

### Directory and reference lineage

Resuming a failed stage creates a new handoff snapshot under
`chain/handoffs/<stage>/attempts/<id>/`. Earlier handoff records and prepared inputs remain
at the paths named by the old run manifests when the stage's definition changes.

Published results are checked against both their file checksums and their complete
`outputs.inventory.json` namespace before a handoff. Empty directories and aliases
remain distinct entries. A local reference inherited from a producer also needs
the recorded input namespace and bytes; a changed alias cannot pass merely because
the new target contains identical data. Missing historical namespace records block
a directory handoff rather than certifying an unknown structure. Older individual-file chains
retain their historical checksum verification. New bundles explicitly declare their output
inventory version, so missing or malformed declared records remain failures.

Each directory handoff records its exact boundary namespace and file dependencies.
Chain status verifies the current source and the consumer's prelaunch snapshot,
accounting for the root canonicalization applied to path parameters while retaining
nested aliases. Empty reference directories are permitted when their complete
namespace is recorded; downstream schemas and tools decide whether they are valid
analytical inputs.

Samplesheet handoffs also record the local data named by schema-declared path columns,
including directory and glob membership. Checking the generated sheet alone is insufficient:
the consumer's recorded file hashes and namespace must agree with the producer's historical
data and the handoff boundary. Glob comparison uses the recorded consumer membership, so
additional files consumed and later removed remain detectable. Every completed stage undergoes
these checks before the chain can launch another stage or report success. Older file-only
records retain checksum checks; missing directory identity cannot be inferred retrospectively.

When a rule passes an entire run directory, execution records and engine state are
part of that directory too. They are recorded at the handoff boundary, separately
from the published results whose original byte and namespace manifests remain
authoritative. The directory is passed intact. Later changes to either part break
that boundary's lineage. This observation does not claim that execution records
were scientific products of the pipeline.

### Sensitive environment values in chain records

Chain records apply the same environment redaction as run provenance. The private chain directory
uses mode 0700 and its JSON records mode 0600. A recorded `<redacted>` value is never passed to
Nextflow: resume requires its real value again, either exported in the environment or supplied
in the original private spec. New sensitive-environment stages also record a versioned keyed
identity of the complete effective `NXF_*` environment. Different private values, or changed
ordinary JVM flags alongside a sensitive argument, refuse reuse of a succeeded stage.

The identity key is created under the chain's writer lock in `chain/.environment-key`, with mode
0600, beneath the mode-0700 chain directory. Keep this private binary file for resume; it is never
copied into stage provenance, JSON records or logs. Do not include it when sharing chain records.
A missing, replaced, symlinked or insufficiently protected key refuses resume. Restore the
original private key or keep the results and start a fresh chain; replacing a lost key cannot
recover the original identity.

Older sensitive-environment chains recorded only `<redacted>` values and cannot establish their
original effective identity. Resuming a succeeded legacy sensitive stage is refused even when
the caller supplies the same value; nfclaw cannot prove that it is the same. Existing nonsensitive
version-2 fingerprints remain compatible and need no key. Appending a new sensitive stage to a
compatible nonsensitive chain creates its private key when execution takes the chain lock.
