# Engine and version compatibility

nf-claw runs each nf-core pipeline unmodified, pinned to the commit of a release tag. What a pipeline
needs at run time (Nextflow version, Java, containers) is therefore set by that release, not by
nf-claw. This page covers matching the Nextflow version to a release, the controls nfclaw offers for
it, the CI workflows that check compatibility, and host requirements.

---

## Navigation

[DSL2 only](#dsl2-only) • [Matching the Nextflow version](#matching-the-nextflow-version) • [Engine controls](#engine-controls) • [Continuous validation](#continuous-validation) • [Host requirements](#host-requirements)

---

## DSL2 only

Nextflow removed DSL1 in version 22.12 (DSL2 had been the default since 22.03), so DSL1 pipelines
cannot run on a current engine.

- `librarian/discover_pipelines.py` skips archived and disabled pipelines and those nf-core marks
  `is_DSL2: false`. A missing DSL2 marker alone does not exclude a pipeline; it must still pass the
  Nextflow acceptance gate before it is added.
- A pipeline added by hand must be DSL2.

---

## Matching the Nextflow version

No single Nextflow version runs every pinned release. Each release declares its minimum engine in
`nextflow.config` (`manifest.nextflowVersion`, for example `!>=23.04.0` or `!>=25.10.4`) and was
written for the configuration parser of its time.

| Parser | Engines | Behaviour | Examples | What to pass |
|---|---|---|---|---|
| Legacy | Default up to 25.10; selectable on 26.04 with `NXF_SYNTAX_PARSER=v1` | Permissive Groovy: allows `def check_max()`, dynamic includes and manifest lookups while parsing. | `chipseq` 2.1.0, `atacseq` 2.1.2, `circdna` 1.1.0, `marsseq` 1.0.3, `scrnaseq` 4.2.0 | `--nxf-ver 25.10.4` |
| Strict | Opt-in on 25.04 and 25.10; default from 26.04 | Validates the configuration before plugins load and rejects Groovy functions in config. | `mag` 5.5.0 declares `!>=26.04.0` | An engine tested with the release, e.g. `--nxf-ver 26.04.0` for mag 5.5.0 |

### The parser change in 26.04

Nextflow 25.04 and 25.10 use the legacy parser by default; the strict parser is opt-in with
`NXF_SYNTAX_PARSER=v2`. From 26.04 the strict parser is the default and `NXF_SYNTAX_PARSER=v1` selects
the legacy one. The strict parser rejects some Groovy that older releases rely on; see Nextflow's
[strict syntax guide](https://docs.seqera.io/nextflow/strict-syntax) and
[26.04 migration notes](https://docs.seqera.io/nextflow/migrations/26-04).

Older releases such as `chipseq` 2.1.0, `atacseq` 2.1.2 and `circdna` 1.1.0 fail to parse under
26.04's default parser. Pin an engine that works with the release: a minimum-version declaration does
not mean every later engine works.

Nextflow 26.10 also moves console logs from stdout to stderr
([migration notes](https://docs.seqera.io/nextflow/migrations/26-10#breaking-changes)). nfclaw writes
both streams to the run log and keeps them separately in `stdout.txt` and `stderr.txt`; what each
contains depends on the engine.

---

## Engine controls

- **`--nxf-ver X.Y.Z`** pins the Nextflow version for a run by setting `NXF_VER`; the Nextflow
  launcher downloads that version on first use. If your Nextflow is too new for an older release,
  pin one from the release's era:
  ```bash
  nfclaw run chipseq --input samplesheet.csv --outdir results -profile docker --nxf-ver 25.10.4
  ```
  Nextflow itself refuses an engine older than the release's `nextflowVersion` (every pinned release
  uses the strict `!>=` form). nfclaw does not repeat that check before launch, but its error names
  the `--nxf-ver` the release declares, and `--check`, which launches nothing, prints it as an
  advisory.
- **`--nxf-env KEY=VALUE`** passes an `NXF_*` variable to Nextflow, for example
  `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true` on an IPv6-only host, or
  `--nxf-env NXF_OFFLINE=true` for an offline run.
- **Recording.** Both are recorded in `<outdir>/provenance/run_manifest.json`. A replay restores the
  recorded `NXF_*` variables that are not secret and pins the engine version that ran; redacted
  secrets must be supplied again. Eligible Docker and Podman processes are pinned to image digests in
  `containers.config`, and Singularity/Apptainer image files are recorded by SHA-256.
  `environment.json` records the loaded plugins and the Java runtime: a replay with different
  plugins fails its environment comparison, while a different Java is reported as a note. Other
  environment variables are not frozen; [replay and verification](replay.md) gives the limits.
- **Chains.** Each stage of `nfclaw chain run` can set its own `"nxf_ver"`, so old and new
  pipelines can run on different engines in one chain.

---

## Continuous validation

| Workflow | Runs | What it checks | What fails it |
|---|---|---|---|
| `smoke.yml` | weekly, and on `main` when the runner or a pin changes | `nfclaw run --check --demo` for every pipeline on the engine its `skill.md` advises, which includes that engine parsing the release's configuration, and the registered chains. It also reports, without failing, which pins the launcher's default engine refuses when no `--nxf-ver` is given. Nothing is launched. | A schema parsing error, a rejected parameter, a wrong command, or a configuration the advised engine cannot parse. |
| `nextflow-validate.yml` | weekly, and on `main` when a pin changes | `nextflow run -preview` of every pipeline's test profile on its declared engine (24.10.5 when the declaration is older than 22.10.0, the first engine with `-preview`), in parallel shards. This checks the configuration, the schema validation that applies, and that the DAG builds. No container is pulled or run. | A nonzero exit, a 15-minute timeout, an initialisation failure or remote test data that cannot be staged, unless it is a documented upstream defect of that exact commit failing as recorded (reported `known-*`, never accepted; see below). |
| `tests.yml` | push to `main`, pull requests, and the maintenance gate | pytest on Ubuntu and macOS with Python 3.11–3.15, with the pinned sources and the scientific format libraries (macOS 3.15 skips H5AD, as declared), integration tests against a real Nextflow, and the website audit, build and Chromium tests. | A failed test or an undeclared skip. See the [publication policy](maintenance.md). |
| `drift-check.yml` | pull requests, daily, manual | Regenerates the context of every pinned pipeline and checks the catalog, the manifest and the handoff rules. | Any drift. |
| `demo-validation.yml` | pull requests that change `runner/`, the demo pin or the workflow; manual | Runs nf-core/demo in Docker on Linux, replays it into a fresh directory and from the bundle's source archive, and compares each run with the release's own nf-test snapshot (expected paths and checksums). It also checks what nfclaw recorded: engine, parameters, container digests and the replay's environment comparison. | A failed run, a result that differs from the snapshot, or a failed recording or replay check. |
| `fastqrepair-validation.yml` | pull requests that change `runner/`, the fastqrepair pin or the workflow; manual | Runs the release with its recorded corrections, checks single-end and paired-end read controls and the replay. | A failed run, reads lost or mispaired, or a failed replay check. |
| `pipeline-execution.yml` | manual (and pull requests that change the workflow) | Runs one chosen pipeline's test profile in Docker on Linux with bounded resources and its declared engine, then checks the run status and the recorded engine. Outputs and task scripts are kept as evidence. It does not replay or verify the run. | A failed run, a timeout, or no recorded engine. |
| `maintenance-gate.yml` | called by both maintenance bots | Runs `tests.yml`, `maintenance-native.yml` and the drift gate on one frozen candidate, then the publisher, the only job with write permission. | Any failed gate or invalid evidence; nothing is published. |
| `maintenance-native.yml` | called by the maintenance gate | Runs the bundled test of every changed pin for real on Linux amd64 with Docker; the publisher then checks the raw task evidence. | Stub-only, failed, empty, cached or incomplete runs, a wrong pin, changed dependencies or missing evidence. |

### Preview acceptance

The update and discovery workflows accept a new or bumped pin only if its preview exits 0. A preview
that fails while staging remote input is labelled `staging-unverified`; any other failure, an
unexpected timeout included, is `rejected`. Both block publication. A failure caused by an
unreachable remote file (a staging error, or nf-schema's existence check on a URL) or a failed plugin
download is retried twice, after 30 seconds and after 5 minutes, because hosted test data and plugin
releases are sometimes unreachable, once for more than ten minutes. A preview that still fails is
never accepted. Some completion handlers wait for task results a preview never produces, so a
release whose DAG builds can still fail its preview. Reduced-output previews and real test runs are
reported separately from this acceptance.

Upstream defects that make a pinned release's default preview fail are investigated in
[known issues](known-issues.md#upstream-pipeline-bugs-documented-not-patched) and listed in
[`scripts/nextflow_accept_exceptions.tsv`](../scripts/nextflow_accept_exceptions.tsv) with the exact
commit, the expected outcome and an evidence pattern searched in the console and the Nextflow log.
Such a preview is reported `known-rejected`, `known-staging-unverified` or `known-timeout`. It is not
accepted, but while it fails exactly as documented it does not turn the weekly run red, so a new
regression elsewhere stays visible. A different failure, missing evidence, a preview that now passes
(`stale-exception`) or any other commit, including every release bump, is judged normally: an
exception never carries over to a new release. A documented `timeout` is cut off after 300 seconds,
since its evidence (the task monitor waiting after the DAG is built) appears within seconds.

Running `scripts/nextflow_accept.sh` locally needs Python 3.11+. The script uses `$PYTHON` (default
`python3`, often 3.9 on macOS) and refuses an older interpreter before any preview. Each preview gets
15 minutes, then 10 seconds to shut down before the remaining processes in its group are killed. GNU
`timeout` (or `gtimeout` from Homebrew coreutils) enforces this when installed; otherwise
`scripts/run_with_timeout.py` enforces the same deadline, grace period and exit statuses.

A passing preview or smoke check shows that the configuration parses and the DAG builds in the tested
environment. It does not run the analysis and says nothing about results on real data.

---

## Host requirements

| Requirement | Version | Notes |
|---|---|---|
| Operating system | Linux or macOS; on Windows, inside WSL 2 | `nfclaw run`, `nfclaw chain run` and MCP jobs refuse a Python without POSIX file locks (native Windows) rather than run without their writer locks, and Nextflow needs WSL 2 there anyway. The tests run on Ubuntu and macOS; pipelines are validated on Linux x86_64 with Docker. On arm64, a pipeline needs arm64 containers or emulation of amd64 ones, which can fail ([known issues](known-issues.md#pipeline-specific-run-notes)). |
| Python | 3.11+ | For `nfclaw` and `librarian`. |
| Java | 17+, as supported by the engine you run | CI uses Temurin 17. Older engines do not necessarily support newer Java; see Nextflow's [requirements](https://docs.seqera.io/nextflow/install#requirements). |
| Nextflow | The version each `skill.md` names (`--nxf-ver`) | The launcher on `PATH` downloads a pinned engine on first use. |
| Containers | Docker, Singularity/Apptainer or Podman | Use a container profile for reproducible runs. The pipeline sweeps ran on Docker, CI runs the demo on Singularity/Apptainer, and Podman is covered only by unit tests ([validation limits](validation.md#limits)). |
| Paths | Repository, output and work paths without spaces | `--allow-spaces` lifts the space check at your own risk; line breaks are always refused. Input file names have their own checks. On macOS, avoid iCloud folders. |
