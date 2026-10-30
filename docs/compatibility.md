# Engine & Version Compatibility

nf-claw wraps each nf-core pipeline **unmodified**, pinned to a commit resolved from a release tag. The runtime requirements of any pipeline are therefore dictated by that pinned release and its upstream dependencies, not by nf-claw.

---

## Navigation

[DSL2 Invariant](#1-only-dsl2-pipelines-are-supported) • [Nextflow Engine Matching](#2-matching-nextflow-engine-to-pinned-releases) • [Parser Transition](#the-parser-transition) • [Engine Controls](#runtime-engine-controls-in-nfclaw) • [Continuous Validation](#3-automated-continuous-validation) • [Host Requirements](#4-host-environment-requirements)

---

## 1. Only DSL2 Pipelines Are Supported

Nextflow permanently removed legacy DSL1 workflow syntax in version **22.12** (DSL2 became default in 22.03). Consequently, legacy DSL1 workflows cannot execute on modern Nextflow runtimes:

- **Automated Discovery:** `librarian/discover_pipelines.py` skips archived or disabled entries and pipelines explicitly marked `is_DSL2: false` in nf-core metadata. A missing DSL2 marker alone does not exclude a candidate; the Nextflow acceptance gate must still pass before automated onboarding.
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

Nextflow 26.10 also moves console logs from stdout to stderr ([migration notes](https://docs.seqera.io/nextflow/migrations/26-10#breaking-changes)). nfclaw captures both streams in the run log and preserves them separately in `stdout.txt` and `stderr.txt`; their contents depend on the selected engine.

### Runtime Engine Controls in `nfclaw`
To ensure reproducible execution across releases of varying ages, nf-claw provides explicit engine controls:

1. **`--nxf-ver X.Y.Z`**: Pins the Nextflow version for a run by setting `NXF_VER`. Nextflow's launcher automatically downloads and executes the requested version.
   - If your host Nextflow is too new for an older pipeline release, pin an engine that matches its era:
     ```bash
     nfclaw run chipseq --input samplesheet.csv --outdir results -profile docker --nxf-ver 25.10.4
     ```
   - An engine older than the pipeline's declared `nextflowVersion` is refused by Nextflow itself at launch (every pinned release uses the strict `!>=` form). A launch does not repeat that check; nfclaw's error names the `--nxf-ver` the release declares. `--check`, which never starts Nextflow, prints an informational advisory instead.
2. **`--nxf-env KEY=VALUE`**: Passes `NXF_*` variables directly to Nextflow:
   - IPv6-only environments: `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`
   - Air-gapped / offline runs: `--nxf-env NXF_OFFLINE=true`
3. **Provenance Recording**: Both `--nxf-ver` and `--nxf-env` are recorded in `<outdir>/provenance/run_manifest.json`. Replay restores recorded non-sensitive `NXF_*` variables and pins the observed engine version; redacted secrets must be supplied again. Eligible Docker/Podman processes receive digest pins in `containers.config`; Singularity/Apptainer image files are recorded by SHA-256. `environment.json` records the loaded plugins and Java runtime. Plugin changes fail the replay's environment comparison, while Java runtime changes are informational notes. Other environment variables are not frozen; see [replay and verification](architecture.md#26-replay--replay-guard) for comparison limits.

> [!TIP]
> **Chaining Engine Overrides:** In pipeline chains (`nfclaw chain run`), each stage can declare its own `"nxf_ver"` in `spec.json`, allowing modern and older pipelines to use different compatible engines within one chain.

---

## 3. Automated Continuous Validation

The repository validates engine and workflow compatibility using automated GitHub Actions workflows:

| Workflow | Scope & Verification Level | Failure Criteria |
|---|---|---|
| **`smoke.yml`** (weekly & on changes) | Builds and preflights each pipeline's demo command via `nfclaw run --check --demo` and validates registered registry chains. Validates schema parsing, CLI argument handling, and parameter composition without launching Nextflow tasks. | Any schema parsing exception, unknown parameter rejection, or invalid command assembly. |
| **`nextflow-validate.yml`** (weekly & when a pin changes) | Runs each pinned test profile with `-preview`, using the declared engine (or 24.10.5 when the declaration predates the preview-capable 22.10.0 floor). Checks configuration, applicable schema validation and DAG construction across parallel shards. Containers are not pulled or executed. | Any nonzero exit code, 15-minute timeout, initialization failure, or unresolvable remote staging — except a documented upstream defect of that exact commit failing with its recorded evidence (reported `known-*`, never accepted). |
| **`tests.yml`** (push, PR & reusable maintenance gate) | Complete Python 3.11–3.15 Linux/macOS matrix with pinned sources and scientific adapters (documented macOS 3.15 H5AD exception), real Nextflow integration, website audit/build and Chromium tests. | Failed checks or undeclared skipped coverage; [publication evidence policy](maintenance.md). |
| **`drift-check.yml`** (PR, daily & manual) | Regenerates all pinned pipeline context and checks catalog, manifest and handoff consistency. | Any detected drift. |
| **`demo-validation.yml`** (PR & manual) | Executes the pinned demo in native Linux Docker and replays it into a fresh directory and from the bundle's source archive, then checks each run against nf-core/demo's own nf-test snapshot (its expected output paths and checksums) and checks what nfclaw recorded: engine identity, parameters, container digests and the replay's environment comparison. | Analysis failure, a result that differs from the release's snapshot, or a recording or replay check failure. |
| **`fastqrepair-validation.yml`** (PR & manual) | Executes the affected release with recorded runtime corrections, checks independent single/paired read controls and replay. | Execution, read-conservation or replay-check failure. |
| **`pipeline-execution.yml`** (PR & manual) | Executes a selected pinned pipeline's bundled test profile on native Linux Docker under bounded resources and its declared engine, then checks the run status and the recorded engine identity; outputs and task scripts are retained as evidence. It does not replay or verify the run (`demo-validation.yml` and `fastqrepair-validation.yml` do). | Process failure, timeout, or an engine identity that was not recorded. |
| **`maintenance-native.yml`** (reusable maintenance gate) | Runs real bundled tasks for every changed candidate pin on Linux amd64/Docker; the fresh publisher checks raw task evidence. | Stub-only, failed, empty, cached or incomplete execution, a wrong pin, changed dependencies or missing evidence. |

### Strict Exit Code Gating
Automated discovery and update workflows require **strict exit code 0** from Nextflow validation. Pipelines with a recognized remote-input staging error are labelled `staging-unverified`, timeouts `timeout`, and other errors `rejected`. All block automated merging. A failure caused by an unreachable remote file (a staging report, or nf-schema's existence check on a URL) or by a failed plugin download is retried twice, after 30 seconds and then 5 minutes, before it is reported: hosted test data and plugin releases are occasionally unreachable, once for over ten minutes. A preview that still fails is never accepted. Some upstream completion handlers wait for task results that preview never produces, so a compiled DAG can still fail the preview gate. Reduced-output previews and actual test executions must be reported separately from default-profile acceptance.

Upstream defects that make a pinned release's default preview fail — each investigated in [`known-issues.md`](known-issues.md#upstream-pipeline-bugs-documented-not-patched) — are recorded in [`scripts/nextflow_accept_exceptions.tsv`](../scripts/nextflow_accept_exceptions.tsv) by **exact commit**, expected outcome and an evidence pattern (searched in the console and the Nextflow log). Such a preview is reported `known-rejected`, `known-staging-unverified` or `known-timeout`: it is **not accepted**, but it does not turn the weekly gate red while it still fails exactly as documented, so a new regression elsewhere stays visible. A different failure, missing evidence, a preview that now passes (`stale-exception`), or any other commit — every release bump — is judged as above, so an exception never carries over to a new release. A documented `timeout` is bounded at 300 seconds, since its evidence (the task monitor's barrier after the DAG is built) is written within seconds.

Running `scripts/nextflow_accept.sh` locally needs Python 3.11+: the script uses `$PYTHON`
(default `python3`, which on macOS is often 3.9) and refuses an older interpreter before
any preview. Each preview gets 15 minutes, followed by a 10-second shutdown grace period
before surviving process-group members are killed. GNU `timeout` (or `gtimeout` from Homebrew
coreutils) enforces that when present; without either, the bundled
`scripts/run_with_timeout.py` enforces the same deadline, grace period and exit statuses, so a
preview is never unbounded.

> [!NOTE]
> Successful preview and smoke verification confirms syntactic correctness and DAG construction within the tested environment; it does not constitute execution or biological verification on experimental datasets.

---

## 4. Host Environment Requirements

| Requirement | Supported Version | Notes & Invariants |
|---|---|---|
| **Operating System** | Linux or macOS (Windows: inside WSL 2) | `nfclaw run`, `nfclaw chain run` and MCP jobs refuse a Python without POSIX file locks (native Windows) rather than run without their writer locks; Nextflow itself needs WSL 2 there. The test suite runs on Ubuntu and macOS (GitHub-hosted runners); pipeline executions are validated on native Linux x86_64 with Docker. On arm64 hosts a pipeline depends on arm64 containers or emulation of amd64 ones, which can fail (see [known-issues](known-issues.md#pipeline-specific-run-notes)). |
| **Python** | 3.11+ | Required for `nfclaw` CLI runtime and `librarian`. |
| **Java** | Java 17+ compatible with the selected engine | CI uses Temurin 17; newer Java releases are not necessarily supported by older pinned engines. See [Nextflow installation requirements](https://docs.seqera.io/nextflow/install#requirements). |
| **Nextflow** | Latest or matching `--nxf-ver` | Installed on system PATH. |
| **Container Engine** | Docker or Singularity / Apptainer | Container execution profile recommended for reproducibility. |
| **Filesystem Paths** | Space-free repository, output and work paths by default | `--allow-spaces` bypasses the space check at the caller's risk; LF/CR remain forbidden. Input basenames have separate safety checks. On macOS, avoid iCloud directories. |
