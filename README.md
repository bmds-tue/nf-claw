<p align="center">
  <img src="docs/images/nf-claw-logo-with-text.png" alt="nf-claw" width="240">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://nextflow.io"><img src="https://img.shields.io/badge/Nextflow-DSL2-brightgreen.svg" alt="Nextflow DSL2"></a>
  <a href="https://nf-co.re"><img src="https://img.shields.io/badge/nf--core-compatible-green.svg" alt="nf-core compatible"></a>
  <a href="https://bmds-tue.github.io/nf-claw/"><img src="https://img.shields.io/badge/portal-live%20site-00ffff.svg" alt="Live Portal"></a>
</p>

# nf-claw

A self-maintaining, token-minimal library of [nf-core](https://nf-co.re) pipelines curated for AI agents and bioinformaticians. Each pipeline source is kept unchanged as a pinned git submodule accompanied by an auto-generated `skill.md` describing its declared inputs, parameters, and run commands. Documented runtime corrections are recorded in provenance configs; for the affected fastqrepair 1.1.1 commit they correct record splitting, quality-offset forwarding and publication without editing the pinned source tree. Exact pinned Createtaxdb and Funcscan releases use [recorded, independently copied workflow corrections](docs/source-corrections.md), with the actual corrected source bound to execution, resume and replay.

**🌐 Live Portal: [bmds-tue.github.io/nf-claw](https://bmds-tue.github.io/nf-claw/)** — an interactive digital interface to the entire library (pipeline explorer, parameters, architecture documentation, and automation status captured at build time), rebuilt from the repository on deployment.

---

nfclaw checks a run before it starts and again before it reports success. It refuses unknown flags,
invalid values, unsafe input filenames or sample identities and outputs that overlap their inputs
rather than silently correcting them, and it fails a run whose declared inputs, configs or pipeline
source changed while it ran. [AGENTS.md](AGENTS.md) states each rule,
[docs/architecture.md](docs/architecture.md) how it is enforced, and
[docs/known-issues.md](docs/known-issues.md) where its checks stop.

### Navigation

[Repository Layout](#layout) • [Quickstart](#quickstart) • [Provenance, Replay & Verification](#provenance-replay--verification) • [Maintenance & Adding Pipelines](#maintain) • [Continuous Automation](#how-it-stays-current) • [Scientific Validation](#scientific-validation--limitations) • [Citations](#citation--attribution)

---

## Layout

The repository is structured into four functional zones, plus the catalogs, documentation and portal built from them:

| Path | Component | Description |
|---|---|---|
| `pipelines/<name>/` | **Library Content** | `upstream/` (submodule pinned to a release) + generated `skill.md` (agent instructions, run commands, inputs, required parameters with constraints) and `reference.md` (complete schema catalog). |
| `runner/` | **Execution Engine** | The `nfclaw` CLI runtime handling parameter preflight, environment isolation, provenance generation, replay guards, and multi-stage chaining. |
| `librarian/` | **Maintenance Automation** | Tools for building context files, auditing schema drift, bumping releases, and discovering new DSL2 pipelines (`make build`, `make check`). |
| `handoffs/` | **Chaining Rules** | Declarative rules (`handoffs/<upstream>/<downstream>.json`) mapping outputs between sequential pipeline stages, statically verified by the drift gate. |
| `catalog.md` / `.json` | **Pipeline Catalog** | Auto-compiled index detailing declared inputs, conditional outputs, upstream descriptions, and citations for all tracked pipelines. |
| `sources.tsv` | **Release Manifest** | Registry mapping pipeline names to upstream remotes and version tracking policies (`latest-release`). |
| `docs/` | **Documentation** | The guides listed below. |
| `website/` | **Live Portal** | Next.js static site and documentation hub, rebuilt from the repository data on every push to `main`. |

### Documentation Guides

| Topic | Document | Scope & Contents |
|---|---|---|
| **Architecture** | [`docs/architecture.md`](docs/architecture.md) | Architectural zones, schema preflight, sibling file locks, and provenance structure. |
| **Engine Compatibility** | [`docs/compatibility.md`](docs/compatibility.md) | DSL2 enforcement, Nextflow 25 vs 26 parser transition, and `--nxf-ver` controls. |
| **Timeouts & Monitoring** | [`docs/timeouts.md`](docs/timeouts.md) | Optional execution deadlines, setup/shutdown margins, background runs, and quick chain status. |
| **Pipeline Chaining** | [`docs/chaining.md`](docs/chaining.md) | Multi-stage orchestration, spec schemas, handoff transforms, and lineage verification. |
| **Known Issues** | [`docs/known-issues.md`](docs/known-issues.md) | Host environment troubleshooting, benign Nextflow warnings, and upstream workarounds. |
| **Validation** | [`docs/validation.md`](docs/validation.md) | End-to-end runs of every pinned pipeline and of nfclaw's features, with the settings each needed. |
| **Preflight Scope** | [`docs/preflight.md`](docs/preflight.md) | Checked/deferred/unsupported validations, the schema subset, and the 95-pipeline samplesheet generation matrix. |
| **Updating & Drift** | [`docs/updating.md`](docs/updating.md) | GitHub Actions automation, tag discovery, and strict zero-drift enforcement. |
| **MCP Server** | [`docs/mcp.md`](docs/mcp.md) | `nfclaw mcp` for Claude Code, Codex, Antigravity, Hermes and other MCP clients: tools, detached jobs, chains. |
| **Agent Guidance** | [`AGENTS.md`](AGENTS.md) | Authoritative reference for autonomous coding assistants and LLM agents; [`CLAUDE.md`](CLAUDE.md) imports it for Claude Code. |
| **Agent Index** | [`llms.txt`](llms.txt) | Curated discovery map and navigation index for external AI agents (llms.txt standard). |

---

## Quickstart

### 1. Installation & Basic Execution

Clone into a space-free path (on macOS, avoid iCloud folders), use Python 3.11+,
and install Git, Nextflow, Java 17+ and the selected container runtime separately.

```bash
# Clone the library and its pinned pipeline sources
git clone --recurse-submodules https://github.com/bmds-tue/nf-claw.git
cd nf-claw
python3 -m venv .venv
source .venv/bin/activate

# Editable install places `nfclaw` on PATH (or use `python3 -m runner <cmd>` without installation)
pip install -e .

# List all available pipelines and descriptions
nfclaw list

# Read the pinned release's inputs and required parameters before preparing data
nfclaw show rnaseq

# Execute a pipeline run with your matched genome and annotation
nfclaw run rnaseq --input samplesheet.csv --outdir results -profile docker \
  --fasta /data/reference.fa --gtf /data/genes.gtf --igenomes-ignore true

# Check execution status (success / running / failed / stopped without outcome)
nfclaw status results
```

Replace the example reference paths with your own matched FASTA and GTF files.
Later rnaseq examples focus on individual options; include these reference arguments
or another reference selection supported by the chosen release. Schema-required
parameters alone do not describe every reference the analysis needs. Samplesheet data
paths, output directories and profiles follow the rules in [AGENTS.md](AGENTS.md).

> [!NOTE]
> The editable install is intentional: `nfclaw` resolves pinned submodules and generated schema context directly from the repository tree, even when invoked from another directory. An installation without that repository content emits a clear setup error instead of an empty catalog.

### 2. Command Inspection (Dry-Run)

```bash
# Inspect the exact Nextflow command that would run without executing it
# Validates parameters, schemas, and paths without creating or modifying --outdir
nfclaw run rnaseq --input samplesheet.csv --outdir results -profile docker \
  --fasta /data/reference.fa --gtf /data/genes.gtf --igenomes-ignore true --check
```

`--check` leaves `--outdir` untouched; conditional and complex schema rules remain subject to
upstream runtime validation.

### Samplesheet from Data Files

```bash
# Pass the data files instead of a samplesheet: a directory (searched recursively), a quoted glob,
# or files (--input once per file).
# nfclaw writes the samplesheet the pinned release's schema describes; set the columns no file
# name determines with --sheet-set (each skill.md lists them). --check previews the sheet.
nfclaw run rnaseq --input /data/fastq --sheet-set strandedness=auto --outdir results --check
nfclaw run sarek --input '/data/run1/*.fastq.gz' --sheet-set 'patient={sample}' --outdir results
```

The pinned schema decides the columns, sample names come unaltered from file names, and gaps,
ambiguous matches are refused; unrelated unmatched files may be ignored with recorded warnings; [AGENTS.md](AGENTS.md) gives the pairing and identity rules,
and [known issues](docs/known-issues.md#legacy-samplesheet-contracts-and-local-data-identity) the
releases whose contracts were corrected from their pinned source.

Review the generated sheet against the experimental design. Filename conventions and the first
read header provide limited identity evidence; they do not establish biological replicates,
complete read synchronization or correct study metadata. Distinct SRA `accession.spot-id`
values remain distinct molecules. Explicit mate labels that contradict an inferred pairing
are refused; `_R1`/`_R2` filenames remain authoritative with an advisory about contradictions.

### 3. Provenance Replay & Verification

```bash
# Reproduce a completed run into a fresh target directory
./results/provenance/commands.sh                         # -> results.replay/

# Verify structural equivalence against the original run
nfclaw verify results.replay --against results           # structural check (file inventory)

# Require matching bytes, link identities and the compared environment evidence
nfclaw verify results.replay --against results --strict
```

What each mode checks, and what it cannot certify, is in
[the verification engine](docs/architecture.md#27-verification-engine-nfclaw-verify).

### 4. Release Selection & Development Code

```bash
# List available release tags (pinned latest flagged; dev branch listed last)
nfclaw versions rnaseq

# Inspect on-demand documentation for a specific published release
nfclaw show rnaseq --pipeline-version 3.14.0

# Run a specific published release tag
nfclaw run rnaseq --pipeline-version 3.14.0 --input samplesheet.csv --outdir results -profile docker

# Run unreleased development code (head of nf-core's `dev` branch, anchored by commit SHA)
nfclaw show rnaseq --pipeline-version dev
nfclaw run rnaseq --pipeline-version dev --input samplesheet.csv --outdir results -profile docker
```

### 5. Engine Pinning & Runtime Environment

```bash
# Pin a specific Nextflow engine version (records NXF_VER in provenance)
nfclaw run rnaseq --nxf-ver 25.10.4 --input ss.csv --outdir results -profile docker

# Pass NXF_* environment variables (e.g. JVM IPv6 preferences or offline execution)
nfclaw run rnaseq --nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true --input ss.csv --outdir results -profile docker
```

### 6. Pipeline Chaining

```bash
# Discover supported downstream handoffs for a pipeline
nfclaw chain edges fetchngs

# Preflight validate a multi-stage specification without launching processes
nfclaw chain run spec.json --outdir /abs/chain --check

# Execute a multi-stage chain (stage 1 -> stage 2 -> stage 3)
nfclaw chain run spec.json --outdir /abs/chain

# Resume a failed chain using Nextflow caching
nfclaw chain run spec.json --outdir /abs/chain --resume

# Inspect chain execution and verify cryptographic custody across all stages
nfclaw chain status /abs/chain
```

### 7. Workstation Resource Caps

```bash
# Apply a resource ceiling to prevent out-of-memory aborts on local workstations
nfclaw run rnaseq --input ss.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

Ceilings need Nextflow 24.04.0 or newer; [AGENTS.md](AGENTS.md) explains how they apply to
retries. Neither a task nor the analysis has a time limit by default: `--limit-time` caps each
task and `--timeout` the whole analysis ([timeouts and long analyses](docs/timeouts.md)).

### 8. AI Agents over MCP

```bash
# Serve nf-claw to an MCP client on stdio (Claude Code shown; Codex, Antigravity, Hermes: docs/mcp.md)
claude mcp add nfclaw -- "$PWD/.venv/bin/nfclaw" mcp
```

`nfclaw mcp` exposes the library and the runner as MCP tools (find a pipeline, read its
`skill.md`/`reference.md`, run, chain, follow, stop, verify), with no extra dependency. Every
tool runs the matching `nfclaw` command. Runs and chains become detached jobs that keep going
when the client disconnects and are followed by job id. See [`docs/mcp.md`](docs/mcp.md).

---

## Provenance, Replay & Verification

By default, `nfclaw run` writes a provenance bundle into `<outdir>/provenance/`: the run log, a
replay script with its dependency guard, the archived pipeline source, config copies, parameter,
checksum and inventory records, and what could be recorded of the execution environment.
[docs/architecture.md](docs/architecture.md#25-provenance-bundles--dependency-hashing) lists every
file and what it establishes. The bundle does not embed scientific input data, container images or
plugins, so those must stay available for a replay. [AGENTS.md](AGENTS.md) covers replaying,
resuming, run locking and their limits.

---

## Maintain

Generated context is never edited by hand: `make build` regenerates every `skill.md`,
`reference.md` and `catalog.*` from the pinned submodules, `make update` bumps them to their newest
releases, and `make check` runs the drift gate and the test suite. [`CONTRIBUTING.md`](CONTRIBUTING.md)
explains each target and how to add a pipeline or a chaining handoff rule.

---

## How It Stays Current

Automated GitHub Actions workflows keep the library, test suites, and website synchronized with upstream releases:

```
┌───────────────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐
│      auto-update.yml      │      │  discover-pipelines.yml   │      │     deploy-pages.yml      │
│    Daily tag discovery    │      │   Weekly DSL2 discovery   │      │  Rebuild & deploy portal  │
│    & acceptance gating    │      │ & strict exit-code 0 gate │      │      on push to main      │
└───────────────────────────┘      └───────────────────────────┘      └───────────────────────────┘
              │                                  │                                  │
              └──────────────────────────────────┼──────────────────────────────────┘
                                                 ▼
                                ┌─────────────────────────────────┐
                                │     Continuous Verification     │
                                │  • smoke.yml (preflight)        │
                                │  • nextflow-validate.yml (DAG)  │
                                │  • tests.yml (matrix & run)     │
                                │  • drift-check.yml (schemas)    │
                                │  • demo-validation.yml (demo)   │
                                │  • pipeline-execution.yml (PR)  │
                                └─────────────────────────────────┘
```

- **`auto-update.yml`** (daily) and **`discover-pipelines.yml`** (weekly) bump pinned releases and
  onboard new DSL2 pipelines. Each validates its update first, then publishes it by a checked
  fast-forward of `main`, which needs no pull-request permission ([docs/updating.md](docs/updating.md)).
- **`smoke.yml`**, **`nextflow-validate.yml`**, **`tests.yml`**, **`drift-check.yml`**,
  **`demo-validation.yml`**, **`fastqrepair-validation.yml`** and **`pipeline-execution.yml`**
  validate every change; [docs/compatibility.md](docs/compatibility.md#3-automated-continuous-validation)
  gives each one's scope and what fails it.
- **`deploy-pages.yml`** (push to `main`) rebuilds the portal, and **`codeql.yml`** (push, PR and
  weekly) scans the Python, JavaScript/TypeScript and GitHub Actions code.

---

## Scientific Validation & Limitations

Use `nfclaw assess OUTDIR --contract FILE [--against ORIGINAL]` to require declared scientific
outputs and sample coverage, and compare their parsed content. The
[output-contract guide](docs/scientific-output-contracts.md) defines the supported tables,
BAM/VCF/FASTA and selected H5AD matrix scope, exact comparisons, explicit tolerances and exclusions.
Two source-bound demo contracts are supplied; other pipelines/branches still need their own.

> [!WARNING]
> **Analytical Rigor & Validation Caveats:**
> nf-claw validates declared inputs, checks parameters against schemas, assembles commands, isolates execution environments, and tracks cryptographic provenance. Successful parameter validation, exit code 0 completion, or identical output file structures do not inherently establish biological or analytical accuracy.
>
> Prior to relying on results in production scientific research:
> 1. Validate chosen pipelines, parameters, and reference genomes using domain-appropriate benchmark datasets.
> 2. Read the caveats `nfclaw status` reports for a successful run: a pipeline can exit 0 after skipping samples or ignoring failed tasks (`completion_caveats` in the run manifest).
> 3. Use `nfclaw verify ... --strict` to verify byte agreement; employ format-aware bioinformatics tools to inspect numerical differences.
> 4. Consult [known issues](docs/known-issues.md) for documented engine boundaries, upstream workarounds, and runtime guidance.

---

## Citation & Attribution

**The pipelines themselves are the work of the [nf-core](https://nf-co.re) community** — the heart of this library. Pipeline source trees remain **unmodified** as pinned git submodules; each maintains its own authors, license, and citations. Recorded runtime corrections are documented separately from those upstream sources.

**nf-claw** was created by **Danilo Monge** (Eberhard Karls Universität Tübingen) and adapts architectural concepts and repository structures from [ClawBio](https://clawbio.ai) — created by **Manuel Corpas** (MIT license; copyright retained in [`LICENSE`](LICENSE), provenance in [`NOTICE`](NOTICE)).

When utilizing nf-claw in scientific research, cite via [`CITATION.cff`](CITATION.cff), alongside its foundational technologies:
- **Nextflow:** Di Tommaso P, *et al.* Nextflow enables reproducible computational workflows. *Nat Biotechnol* **35**, 316–319 (2017). [doi:10.1038/nbt.3820](https://doi.org/10.1038/nbt.3820)
- **nf-core:** Ewels PA, *et al.* The nf-core framework for community-curated bioinformatics pipelines. *Nat Biotechnol* **38**, 276–278 (2020). [doi:10.1038/s41587-020-0439-x](https://doi.org/10.1038/s41587-020-0439-x)
- **Executed Pipeline:** Cited individually in `pipelines/<name>/upstream/CITATIONS.md`.
- **ClawBio:** Corpas M. ClawBio: Bioinformatics-Native AI Agent Skill Library. Zenodo (2026). [doi:10.5281/zenodo.19420648](https://doi.org/10.5281/zenodo.19420648)

nf-claw is MIT-licensed (© Danilo Monge). Upstream nf-core pipelines are MIT-licensed, and Nextflow is Apache-2.0.
