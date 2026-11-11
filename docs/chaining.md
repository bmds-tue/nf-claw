# Chaining pipelines

`nfclaw chain run` runs several nf-core pipelines in sequence, for example `fetchngs` → `rnaseq` →
`differentialabundance`. Each stage starts only after the one before it succeeded, and its inputs
are prepared from that stage's outputs. There is no DAG syntax, daemon or scheduler: every stage is
an ordinary `nfclaw run` in `<outdir>/NN-<stage>/`, with its own preflight, lock, run log and
provenance bundle, and the chain keeps its state, handoff snapshots and log in `<outdir>/chain/`.

```bash
nfclaw chain edges                                       # every registered handoff
nfclaw chain edges fetchngs                              # handoffs from or into fetchngs
nfclaw chain run spec.json --outdir /abs/chain --check   # validate every stage and handoff; run nothing
nfclaw chain run spec.json --outdir /abs/chain           # run the chain
nfclaw chain status /abs/chain                           # stage outcomes, and which outputs became which inputs
```

---

## Navigation

[The spec file](#the-spec-file) • [How a chain runs](#how-a-chain-runs) • [Handoff rules](#handoff-rules) • [Failures and resume](#failures-and-resume) • [Lineage](#lineage) • [Sensitive environment values](#sensitive-environment-values-in-chain-records)

---

## The spec file

A chain is described in JSON (or YAML, with `pip install -e ".[yaml]"`). Relative paths in the spec
are resolved against the caller's working directory; the copy recorded in `<outdir>/chain/chain.json`
has absolute paths.

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

### Chain options

These apply to every stage. A stage can override all of them except `allow_spaces`, which is set
for the whole chain.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `profile` | string | `"docker"` | Nextflow profile. |
| `nxf_ver` | string | `null` | Nextflow version (`NXF_VER`) for every stage. |
| `nxf_env` | object | `{}` | `NXF_*` variables with string values, e.g. `{"NXF_OFFLINE": "true"}`. |
| `config` | array | `[]` | Extra Nextflow config files, passed with `-c`. |
| `limits` | object | `null` | Resource ceilings: `{"cpus": N, "memory": "SIZE", "time": "DURATION"}` (`process.resourceLimits`, Nextflow 24.04.0 or newer). `time` caps every task and every retry, so set it only as a deliberate ceiling. |
| `allow_spaces` | boolean | `false` | Allow paths that contain spaces. |

### Stage keys

| Key | Type | Required | Meaning |
|---|---|---|---|
| `pipeline` | string | yes | A pipeline in the library. |
| `id` | string | no | The stage's name; defaults to the pipeline name and must match `^[a-z0-9][a-z0-9_-]*$`. |
| `input` | string, array or boolean | no | The stage's `--input`, usually for stage 1. It replaces the input a handoff would supply. A directory, glob or list of data files makes nfclaw generate the samplesheet, as `nfclaw run` does. Use `false` only for an analysis mode that runs without input. |
| `sheet_set` | object | no | Values for the generated samplesheet's columns that no file name determines (`--sheet-set`), e.g. `{"strandedness": "auto", "patient": "{sample}"}`. Only for a stage whose `input` names data files. On `--resume`, a succeeded stage whose data directory now holds files it never analysed is refused, because the resume would skip them silently; data removed after the stage succeeded is not needed again. |
| `params` | object | no | The pipeline's parameters, e.g. `{"genome": "GRCh38", "aligner": "star_salmon"}`; look them up in its `reference.md`. |
| `params_file` | string | no | A JSON or YAML parameter file. |
| `pipeline_version` | string | no | A release tag (e.g. `3.14.0`) or `dev`. |
| `demo` | boolean | no | Adds the release's `test` profile before the selected profiles. |
| `retries` | integer | no | How many times to relaunch the stage with Nextflow's `-resume` after a pipeline failure (default `0`). A validation error is never retried. |
| `handoff` | object or string | no | An inline handoff rule, or the path to one, used instead of the registered rule. |
| `nxf_ver` | string | no | This stage's Nextflow version, for example to run an older release after a newer one. |
| `nxf_env` | object | no | `NXF_*` variables merged over the chain's. |
| `config` | array | no | Replaces the chain's config list; repeat shared configs here if needed. |
| `limits` | object | no | Replaces the chain's limits; `null` or `{}` removes them for this stage. |

---

## How a chain runs

### Checks before the first stage

Before any pipeline starts, `nfclaw chain run` checks that:

1. every stage's pipeline and requested version exist and resolve;
2. every handoff rule names valid parameters and provides columns the downstream input schema
   accepts (published paths are checked when the handoff happens, since there is no general schema
   for a pipeline's outputs);
3. every stage's explicit parameters pass preflight (values a handoff will supply, and complex
   schema rules, are checked later);
4. `nextflow config` resolves each stage's configuration under that stage's Nextflow version, so a
   config error in stage 3 fails at once instead of after stage 1 has run for hours.

The configuration probe checks parsing and resolution only, not the full parameter contract or the
tasks. Values that come from a handoff are validated when the consuming stage receives them.

`--check` runs the same checks and probes and leaves `--outdir` untouched. It can fetch pipeline
versions and fill engine caches. The probes' time limit, and the deadline `--timeout` sets for the
whole chain, are described in [timeouts](timeouts.md).

Then the chain takes its lock and runs the stages in order. After a stage succeeds, its outputs are
checked against its `outputs.sha256`, the next stage's inputs are prepared in
`chain/handoffs/NN-<id>/`, and that stage starts. The outcome is written to `chain.log` and
`state.json`.

### Locking, logs and stopping

- `runner/chain.py` takes a non-blocking lock on `<outdir>/chain/.lock`. If another chain is
  running in the same directory, it stops at once with `ErrorCode.ENVIRONMENT`.
- The chain logs to `<outdir>/chain/logs/chain.log`. Its last line, once the chain is done, is
  `==> nfclaw chain finished <timestamp>: <outcome>`, so `tail -n 1` shows whether it finished.
- `nfclaw chain status <outdir> --quick` lists the recorded state without hashing outputs
  ([progress versus verification](timeouts.md#cheap-progress-versus-verification)).
- `kill <pid>` stops the running stage cleanly: Nextflow shuts down and the logs are completed.

---

## Handoff rules

A handoff rule says how the outputs one pipeline publishes become the next pipeline's inputs.
Registered rules are in `handoffs/<upstream>/<downstream>.json`. For example,
`handoffs/fetchngs/rnaseq.json`:

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

### Source types

| Source | What it does | Example |
|---|---|---|
| `samplesheet` | Copies an upstream samplesheet and adapts it. `provides` lists the columns it is guaranteed to have, which the drift gate checks. | `fetchngs` → `rnaseq`, `fetchngs` → `mag` |
| `build` | Builds a new samplesheet from matching output files, using `{placeholders}` to group rows and fill columns. | `bamtofastq` → `rnaseq` |
| `file` | Passes one published file to a parameter. A glob must match exactly one file. A list of patterns is tried in order; `"paired_with": "<param>"` takes the pattern at the position that the named parameter's list chose, so both files come from the same step. | `rnaseq` → `differentialabundance` (`--matrix`, and `--feature-length-matrix` paired with it) |
| `upstream_param` | Reuses a parameter value from the upstream run's `params.json`. | `rnaseq` `--gtf` → `differentialabundance` `--gtf` |

Source paths are relative to the upstream output directory. Any source can set `"optional": true`
to leave out a value that is not available; checksum, listing and downstream validation failures
are still errors. A `build` source has `rows` (a relative pattern with `{placeholders}`), `columns`
(a template for each column) and, optionally, `format` (`csv` by default, or `tsv`). In a path
column, a template ending in `?` leaves the cell empty when the companion file is missing. An
optional `exhaustive` glob names files that must all end up in a row: a matching file that no row
uses, such as bamtofastq's single-end reads beside its paired ones, fails the handoff (even an
optional one) instead of being dropped.

Explicit stage `input` and `params` values override the handoff's values, with an advisory, and
unused sources are not prepared; the rule must still pass its static checks. A `params_file` has
lower priority and does not override a mapped source.

An `upstream_param` reference uses the downstream parameter's path format (`file-path`,
`directory-path`, `path` or `file-path-pattern`). Relative local references are anchored to the
producer's launch directory, including references its profile set. A file pattern keeps its selected
files, and every one of them needs recorded bytes and listing. The consumer's record from before its
launch must match that selection, so a file added while the consumer ran and removed later still
breaks lineage. A pattern that points to external input data needs the producer's input inventory,
not only older file checksums.

### Samplesheet transformations

A `samplesheet` source applies its transformations in this order:

1. `rename` renames columns (`{"fastq_1": "short_reads_1"}`).
2. `set` sets a value or template on every row (`{"lane": "{run_accession}"}`).
3. `add_empty` adds declared columns the upstream sheet lacks.
4. `drop_rows_not_allowed` drops rows with values the downstream schema rejects.
5. `allowed_values` refuses the whole handoff (it never drops rows) when a column holds a value
   outside a list. This catches rows the downstream pipeline must not analyse although its schema
   cannot tell, such as a long-read or colour-space run in fetchngs's sheet for a short-read
   pipeline (`{"instrument_platform": ["ILLUMINA", …]}`).
6. `require_values` requires the listed columns to be non-empty.

`refuse_rows_in` lists other sheets the upstream writes for the same downstream pipeline that this
handoff cannot take, such as detaxizer's `mag-se.csv` (samples without a second short-read file)
beside `mag-pe.csv`. A row in any of them fails the handoff and names the samples, instead of
leaving them out. A pattern that also matches the sheet being handed over never refuses that sheet.

### What a rule does not infer

- **Co-assembly in mag.** nf-core/mag pools the reads of samples that share a `group` and assembles
  them together. The registered rules into mag (`fetchngs` → `mag`, `detaxizer` → `mag`) give every
  sample its own group, `"group": "{sample}"`. To pool samples, write an inline handoff rule.
- **Long-read platforms.** mag chooses its long-read preprocessing and assembler mode (for example
  Flye's ONT or PacBio mode) from `long_reads_platform`. The `fetchngs` → `mag` rule takes each run's
  short-read platform from its ENA `instrument_platform` (fetchngs itself labels every run
  `ILLUMINA`), so a long-read run is refused rather than analysed as Illumina short reads. detaxizer
  records no long-read platform, so the `detaxizer` → `mag` rule refuses samples with long reads
  until an inline handoff names their platform, for example for PacBio HiFi:
  ```json
  {"pipeline": "mag", "handoff": {
    "upstream_params": {"generate_downstream_samplesheets": true, "generate_pipeline_samplesheets": "mag"},
    "params": {"input": {"samplesheet": "downstream_samplesheets/mag-pe.csv",
      "provides": ["sample", "run", "group", "short_reads_1", "short_reads_2", "long_reads"],
      "set": {"group": "{sample}", "short_reads_platform": "ILLUMINA", "long_reads_platform": "PACBIO_HIFI"}}}}}
  ```
- **Short-read pipelines.** The `fetchngs` rules into `rnaseq`, `atacseq`, `sarek`, `metatdenovo` and
  `viralrecon` refuse runs whose ENA `instrument_platform` is not a short-read platform, so long-read,
  capillary and colour-space runs are not analysed as Illumina reads. ampliseq needs
  `--pacbio` or `--iontorrent` for such runs.
- **Sequencing runs in ampliseq.** `fetchngs` → `ampliseq` leaves `run` empty, so ampliseq learns one
  DADA2 error model for all samples. Data from several sequencing runs needs `run` filled per run:
  use an inline handoff whose `set` fills it from a column that identifies the run, or your own
  samplesheet.
- **Tumour/normal design in sarek.** `fetchngs` → `sarek` and `demultiplex` → `sarek` write no
  `status` or `sex`, so sarek treats every sample as normal tissue and runs germline analyses only.
  A tumour/normal design needs its own samplesheet, because a handoff's `set` gives every row the
  same value.

---

## Failures and resume

| What happens | What the chain does | Exit code |
|---|---|---|
| A check before launch fails | No pipeline task starts (configuration probes may have run); the error is printed. | `1` |
| A stage fails and `retries` is above 0 | The stage is relaunched with Nextflow's `-resume`. | — |
| Retries are used up, or the failure cannot be retried | The chain stops; later stages stay `pending`. | `1` |
| A handoff cannot be prepared (`[handoff_failed]`) | The upstream stage stays succeeded; the downstream stage does not start. | `1` |
| `SIGINT`, `SIGTERM` or `SIGHUP` | The running stage shuts Nextflow down and the logs are completed. | `128 + signal` (`130` for Ctrl-C) |

To continue after fixing the cause:

```bash
nfclaw chain run spec.json --outdir /abs/chain --resume
```

Leave out `spec.json` to reuse the recorded spec. On resume:

1. Succeeded stages are verified and kept as they are; changing a succeeded stage in the spec is
   refused.
2. The failed stage reuses Nextflow's cache if its declared local inputs (bytes and listing) are
   unchanged. A handoff prepared again from unchanged upstream outputs keeps the files the failed
   attempt ran on, at the same paths. If inputs changed, or the previous snapshot is unavailable,
   the stage's previous run is archived and all its tasks run again.
3. New stages can be appended to a finished chain to extend the analysis.

---

## Lineage

The chain records checksum evidence for every link between stages:

- each stage's `run_manifest.json` has a `chain` block with the chain ID, the stage index and the
  stages it depends on;
- each handoff record stores the rule's digest and the inventories of what it handed over, and the
  downstream stage records the handed-over files and samplesheet in its `inputs.sha256`;
- before a handoff, the upstream stage's published files are checked against `outputs.sha256`, and
  its complete published listing (empty directories, entry types and link identities included)
  against `outputs.inventory.json`.

### Checking a chain

```bash
nfclaw chain status /abs/chain
```

`nfclaw chain status`:

1. checks that every finished stage's manifest matches the recorded chain state;
2. checks that each stage's outputs on disk still match their `outputs.sha256`;
3. compares the handed-over files and reference inventories with the upstream evidence and with the
   input hashes the downstream stage recorded, internal reference directories included;
4. exits `0` when every link is verified and the chain is complete, `3` while a stage is running,
   and `1` on any failure or mismatch.

This verifies the recorded links and the current outputs. It does not re-verify every original input
or configuration, show that the analysis is correct, or detect someone who rewrites the whole bundle.
Static rule checks use the parameter and input schemas and the declared published paths, since there
is no general schema for outputs; whether files exist, and their past identity, are checked when the
chain runs. A configuration probe that fails or times out blocks both `--check` and the run.

### Directories, references and samplesheets

- Resuming a failed stage creates a new handoff snapshot in `chain/handoffs/<stage>/attempts/<id>/`.
  When the stage's definition changes, earlier handoff records and prepared inputs stay at the paths
  the old run manifests name.
- Published results are checked against both their checksums and their complete
  `outputs.inventory.json` listing before a handoff, so empty directories and aliases count as
  separate entries. A local reference inherited from a producer also needs the producer's recorded
  input listing and bytes; a changed alias does not pass just because its new target holds identical
  data. A directory handoff without a recorded listing is refused rather than trusted. Older chains
  that handed over individual files keep their checksum checks. New bundles declare their inventory
  version, so a missing or malformed record is an error.
- A directory handoff records the exact listing and files at the handoff. Chain status compares the
  current source and the consumer's record from before its launch, allowing for the root
  normalisation applied to path parameters while keeping nested aliases. An empty reference
  directory is accepted when its listing is recorded; the downstream schema and tools decide whether
  it is a valid input.
- A samplesheet handoff also records the local data named in the schema's path columns, including
  directory and glob membership. Checking the generated sheet alone is not enough: the consumer's
  recorded hashes and listing must agree with the producer's data and the handoff record. Glob
  membership is compared with what the consumer recorded, so a file consumed and later removed is
  still detected. Every finished stage passes these checks before the chain launches another stage
  or reports success. Older file-only records keep their checksum checks; directory identity that
  was never recorded cannot be reconstructed.
- When a rule hands over a whole run directory, the execution records and engine state in it are
  handed over too. They are recorded at the handoff, separately from the published results, whose
  original byte and listing manifests stay authoritative. The directory is passed intact, and a
  later change to either part breaks that link's lineage. This does not make the execution records
  scientific results of the pipeline.

### Sensitive environment values in chain records

Chain records redact the environment the same way run provenance does. The chain directory has mode
0700 and its JSON records mode 0600. A recorded `<redacted>` value is never passed to Nextflow: a
resume needs the real value again, exported in the environment or written in the original private
spec. Stages with sensitive environment values also record a keyed, versioned identity of the whole
effective `NXF_*` environment. A different private value, or changed ordinary JVM flags next to a
sensitive argument, prevents a succeeded stage from being reused.

The key is created under the chain's writer lock as `chain/.environment-key` (mode 0600, in the
mode-0700 chain directory). Keep this private binary file to be able to resume; it is never copied
into stage provenance, JSON records or logs, and it should not be shared with the chain records. A
missing, replaced, symlinked or insufficiently protected key prevents a resume. Restore the original
key, or keep the results and start a new chain: a new key cannot reproduce the original identity.

Chains recorded before this identity existed stored only `<redacted>` values, so their original
environment cannot be established. Resuming a succeeded stage of such a chain that had a sensitive
value is refused, even with the same value supplied, because nfclaw cannot show it is the same.
Version-2 fingerprints of chains without sensitive values stay compatible and need no key. Appending
a stage with a sensitive value to such a chain creates the key when the chain takes its lock.
