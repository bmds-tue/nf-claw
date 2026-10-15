# Engine & Version Compatibility

nf-claw wraps each nf-core pipeline **unmodified**, pinned to a commit resolved from a release tag. The runtime requirements of any pipeline are therefore dictated by that pinned release and its upstream dependencies, not by nf-claw.

---

### Navigation

[DSL2 Invariant](#1-only-dsl2-pipelines-are-supported) • [Nextflow Engine Matching](#2-matching-nextflow-engine-to-pinned-releases) • [Parser Transition](#the-parser-transition) • [Engine Controls](#runtime-engine-controls-in-nfclaw) • [Continuous Validation](#3-automated-continuous-validation) • [Host Requirements](#4-host-environment-requirements)

---

## 1. Only DSL2 Pipelines Are Supported

Nextflow permanently removed legacy DSL1 workflow syntax in version **22.12** (DSL2 became default in 22.03). Consequently, legacy DSL1 workflows cannot execute on modern Nextflow runtimes:

- **Automated Discovery:** `librarian/discover_pipelines.py` inspects nf-core metadata and skips any pipeline that is not marked as DSL2, ensuring legacy workflows are never onboarded.
- **Manual Additions:** Any pipeline contributed manually must adhere strictly to DSL2 structure.

---

## 2. Matching Nextflow Engine to Pinned Releases

There is **no single Nextflow version that can run every pipeline release**. Each nf-core release declares its minimum engine requirement in `nextflow.config` via `manifest.nextflowVersion` (e.g., `!>=23.04.0` or `!>=25.10.4`), and is authored against the configuration parser of its era:

### Nextflow Generation Overview

| Generation | Era / Versions | Parser Behavior | Typical Pipeline Compatibility | Recommended Flag |
|---|---|---|---|---|
| **Legacy Parser** | Default through `25.10.x`; selectable with `NXF_SYNTAX_PARSER=v1` on 26.04 | Permissive Groovy parsing; allows `def check_max()`, dynamic inclusions, and parse-time manifest lookups. | `chipseq` 2.1.0, `atacseq` 2.1.2, `circdna` 1.1.0, `marsseq` 1.0.3, `scrnaseq` 4.2.0 | `--nxf-ver 25.10.4` |
| **Strict Parser** | Opt-in on 25.04/25.10; default from `26.04` | Strict declarative configuration validation before plugins load; rejects Groovy functions in config. | Releases using strict syntax (`mag` 5.5.0 declares `!>=26.04.0`) | Pin a tested compatible engine, e.g. `--nxf-ver 26.04.0` for mag 5.5.0 |

### The Parser Transition
Nextflow 25.04 and 25.10 default to the legacy parser; the strict parser is opt-in via `NXF_SYNTAX_PARSER=v2`. Starting with 26.04, strict syntax is the default, and the legacy parser can be selected with `NXF_SYNTAX_PARSER=v1`. Strict configuration syntax rejects some Groovy constructs allowed by older releases. See the official [strict syntax guide](https://docs.seqera.io/nextflow/strict-syntax) and [26.04 migration notes](https://docs.seqera.io/nextflow/migrations/26-04).

Older pinned releases such as `chipseq` 2.1.0, `atacseq` 2.1.2 and `circdna` 1.1.0 have reproduced parser failures with the default 26.04 parser. Pin an engine that works with that release; a minimum-version declaration alone is not proof of compatibility with every later engine.

### Runtime Engine Controls in `nfclaw`
To ensure reproducible execution across releases of varying ages, nf-claw provides explicit engine controls:

1. **`--nxf-ver X.Y.Z`**: Pins the Nextflow version for a run by setting `NXF_VER`. Nextflow's launcher automatically downloads and executes the requested version.
   - If your host Nextflow is too new for an older pipeline release, pin an engine that matches its era:
     ```bash
     nfclaw run chipseq --input samplesheet.csv --outdir results -profile docker --nxf-ver 25.10.4
     ```
   - If the installed engine is older than the pipeline's declared `nextflowVersion`, `nfclaw run` prints an informational advisory before launching.
2. **`--nxf-env KEY=VALUE`**: Passes `NXF_*` variables directly to Nextflow:
   - IPv6-only environments: `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`
   - Air-gapped / offline runs: `--nxf-env NXF_OFFLINE=true`
3. **Provenance Recording**: Both `--nxf-ver` and `--nxf-env` are recorded in `<outdir>/provenance/run_manifest.json`. Replay restores recorded non-sensitive `NXF_*` variables and pins the observed engine version; redacted secrets must be supplied again. Container images are pinned by the digest each process ran (`containers.config`), and the plugins and Java runtime the engine loaded are recorded in `environment.json` and compared after a replay. Other environment variables are not frozen.

> [!TIP]
> **Chaining Engine Overrides:** In pipeline chains (`nfclaw chain run`), each stage can declare its own `"nxf_ver"` in `spec.json`, allowing modern and older pipelines to use different compatible engines within one chain.

---

## 3. Automated Continuous Validation

The repository validates engine and workflow compatibility using automated GitHub Actions workflows:

| Workflow | Scope & Verification Level | Failure Criteria |
|---|---|---|
| **`smoke.yml`** | Builds and preflights each pipeline's demo command via `nfclaw run --check --demo` and validates registered registry chains. Validates schema parsing, CLI argument handling, and parameter composition without launching Nextflow tasks. | Any schema parsing exception, unknown parameter rejection, or invalid command assembly. |
| **`nextflow-validate.yml`** | Runs each pinned test profile with `-preview`, using the declared engine (or 24.10.5 when the declaration predates the preview-capable 22.10.0 floor). Checks configuration, applicable schema validation and DAG construction across parallel shards. Containers are not pulled or executed. | Any nonzero exit code, 15-minute timeout, initialization failure, or unresolvable remote staging — except a documented upstream defect of that exact commit failing with its recorded evidence (reported `known-*`, never accepted). |
| **`tests.yml`** | Tests the wrapper across Python 3.11–3.13 on Linux/macOS, exercises a real deterministic Nextflow run/replay/chain, and audits/builds the website. | A failing test, dependency audit or build. |
| **`drift-check.yml`** | Regenerates all pinned pipeline context and checks catalog, manifest and handoff consistency. | Any detected drift. |
| **`demo-validation.yml`** | Executes the pinned demo in native Linux Docker, checks basic FastQC statistics against an independent FASTQ oracle and requires its static plot exports. | Analysis failure, incorrect checked statistics or missing/invalid plot exports. |
| **`fastqrepair-validation.yml`** | Executes the affected release with recorded runtime corrections, checks independent single/paired read controls and replay. | Execution, read-conservation or replay-check failure. |
| **`pipeline-execution.yml`** | Executes a selected pinned pipeline's bundled test profile on native Linux Docker under bounded resources and its declared engine, then checks the run status and the recorded engine identity; outputs and task scripts are retained as evidence. It does not replay or verify the run (`demo-validation.yml` and `fastqrepair-validation.yml` do). | Process failure, timeout, or an engine identity that was not recorded. |

### Strict Exit Code Gating
Automated discovery and update workflows require **strict exit code 0** from Nextflow validation. Pipelines with a recognized remote-input staging error are labelled `staging-unverified`; other errors and timeouts are `rejected`. Both block automated merging. A failure caused by an unreachable remote file (a staging report, or nf-schema's existence check on a URL) or by a failed plugin download is retried twice, after 30 seconds and then 5 minutes, before it is reported: hosted test data and plugin releases are occasionally unreachable, once for over ten minutes. A preview that still fails is never accepted. Some upstream completion handlers wait for task results that preview never produces, so a compiled DAG can still fail the preview gate. Reduced-output previews and actual test executions must be reported separately from default-profile acceptance.

Upstream defects that make a pinned release's default preview fail — each investigated in [`known-issues.md`](known-issues.md#upstream-pipeline-bugs-documented-not-patched) — are recorded in [`scripts/nextflow_accept_exceptions.tsv`](../scripts/nextflow_accept_exceptions.tsv) by **exact commit**, expected outcome and an evidence pattern (searched in the console and the Nextflow log). Such a preview is reported `known-rejected`, `known-staging-unverified` or `known-timeout`: it is **not accepted**, but it does not turn the nightly gate red while it still fails exactly as documented, so a new regression elsewhere stays visible. A different failure, missing evidence, a preview that now passes (`stale-exception`), or any other commit — every release bump — is judged as above, so an exception never carries over to a new release. A documented `timeout` is bounded at 300 seconds, since its evidence (the task monitor's barrier after the DAG is built) is written within seconds.

Running `scripts/nextflow_accept.sh` locally requires GNU `timeout` (`gtimeout`
from Homebrew coreutils on macOS). Each preview gets 15 minutes, followed by a
10-second shutdown grace period before surviving process-group members are killed. The
script refuses to launch a preview when neither timeout utility is available.

> [!NOTE]
> Successful preview and smoke verification confirms syntactic correctness and DAG construction within the tested environment; it does not constitute execution or biological verification on experimental datasets.

---

## 4. Host Environment Requirements

| Requirement | Supported Version | Notes & Invariants |
|---|---|---|
| **Operating System** | Linux or macOS | The test suite runs on Ubuntu and macOS (GitHub-hosted runners); pipeline executions are validated on native Linux x86_64 with Docker. On arm64 hosts a pipeline depends on arm64 containers or emulation of amd64 ones, which can fail (see [known-issues](known-issues.md#pipeline-specific-run-notes)). |
| **Python** | 3.11+ | Required for `nfclaw` CLI runtime and `librarian`. |
| **Java** | Java 17+ compatible with the selected engine | CI uses Temurin 17; newer Java releases are not necessarily supported by older pinned engines. See [Nextflow installation requirements](https://docs.seqera.io/nextflow/install#requirements). |
| **Nextflow** | Latest or matching `--nxf-ver` | Installed on system PATH. |
| **Container Engine** | Docker or Singularity / Apptainer | Container execution profile recommended for reproducibility. |
| **Filesystem Paths** | Space-free repository, output and work paths by default | `--allow-spaces` bypasses the space check at the caller's risk; LF/CR remain forbidden. Input basenames have separate safety checks. On macOS, avoid iCloud directories. |
