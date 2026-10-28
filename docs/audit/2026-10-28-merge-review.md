# Merge review of the audit remediation (2026-10-28)

Independent review of `fix/audit-remediation-20261026` before merging it into `main`, with fresh
real executions on `denbi_instance` (Linux amd64, Docker 29.1.3, Nextflow 25.10.4/24.10.5) in a
separate clone (`/mnt/volume/claude-review-20261028`). The remediation ledger is
[2026-10-26-progress.md](2026-10-26-progress.md); this file records only what the review checked
and changed.

## Defects found and fixed in review

| Commit | Finding |
|---|---|
| fix(web): resolve pipeline guidance links | The new operating-guidance panels hardcoded a personal repository URL and no document map, so `docs/…` links left the site for a redirected GitHub path. They now use the docs pages' link context. |
| ci: check out the trusted triggering commit | CodeQL raised five high-severity cache-poisoning alerts: jobs in the default-branch context checked out a ref taken from a workflow input and then ran code. They now check out `github.sha` (always equal to the validated base) and the restore action refuses a checkout that is not the candidate's base. |
| fix(assess): refuse an oversized run manifest | The pipeline binding parsed a manifest read capped at 1 MiB, so an oversized one surfaced as a misleading JSON error. |
| fix(chain): report a missing redacted secret once | The resume refusal was wrapped twice: `chain spec: chain: chain spec: chain: …`. |
| docs: name Bactmap among the corrected releases | README listed only Createtaxdb and Funcscan. |
| fix(ci): judge a module-level collection skip | pytest's JUnit writer records a module-level `importorskip` as `classname=""`, `message="collection skipped"`. The full-matrix evidence checker therefore refused the declared h5py exception, so the macOS Python 3.15 lane would fail with every test passing. Reproduced against that lane's real CI report. |

Hosted CI also caught one regression the server runs had not: `test_nextflow_accept_timeout_is_portable`
still asserted the preview gate's old inline `nextflow` call after `1725642` routed it through
`scripts/nextflow_preview.py`. Codex's `8db1cbb` replaced it with a behavioral test under both
`timeout` and `gtimeout`; the review kept that version.

## Test suites

- Full Python suite, all 95 pinned sources, Python 3.12 on the server: **3398 tests, 0 failures,
  0 errors, 3 skips** (obsolete rnasplice audit pin; two website-parser tests that need `npm ci`
  and run in the CI `website` job). Ruff, generated-document drift and actionlint passed.
- Hosted CI on the PR: Ubuntu and macOS, Python 3.11–3.15, plus website (production build and
  browser tests), Nextflow integration, drift, CodeQL and the native demo/fastqrepair workflows.

## Real executions (run → fresh replay via `provenance/commands.sh` → `nfclaw verify`)

| Pipeline (route exercised) | Tasks orig/replay | verify | `--require-environment` |
|---|---|---|---|
| rnaseq 3.27.0 demo (core regression) | 234/234 | 0 missing/extra, environment identical | pass |
| fastqrepair 1.1.1 demo (U23 paired control) | 22/22 | 0 missing/extra, environment identical | pass |
| hgtseq 1.1.0 demo (U03 historical fixture) | 63/63 | 0 missing/extra, environment identical | pass |
| bamtofastq 2.2.1 demo (U01 reference default) | 32/32 | 0 missing/extra, environment identical | refused, by design: the demo validates a moving remote samplesheet whose bytes were refetched |
| bactmap 1.0.0 demo, recipe v2 (`8db1cbb`) | 47/47 | 0 missing/extra, environment identical | pass |
| tumourevo 1.0.0 demo (U11 `sparsesignatures_k`) | 66/66 | 0 missing/extra, environment identical | pass |
| createtaxdb 3.1.0 demo (Sourmash correction) | 32/32 | at merge: 6 missing/6 extra, the random `kraken2-build` library names, all six pairs byte-identical; after the follow-up below: 0 missing/extra, 7 renamed, environment identical | refused at merge for the same structural difference |
| funcscan 4.0.0 demo (HMM metadata correction; host-network config for its in-task DeepARG download) | 68/68 | 0 missing/extra, environment identical | refused, by design: moving remote demo samplesheet refetched |
| rnaseq with a samplesheet generated from a FASTQ directory (`--skip-deseq2-qc`; two real samples on the yeast chrI test genome leave every gene with a zero) | 100/100 | 0 missing/extra, environment identical | pass |

Scientific checks beyond file structure:

- `nfclaw assess` with the bundled contracts: HGTseq BAMs identical decoded records
  (1220/1340/1465); Tumourevo 9/9 artifacts identical records, expected counts 630/626/429, binding
  of `sparsesignatures_k=2:3` verified. A mismatched contract is refused (exit 1).
- FastQRepair: `BBMAP_REPAIR (paired_control)` ran in both runs; 646/646 pairs, 0 singletons,
  24 valid single-end reads; decompressed R1 identical across replay.
- Bactmap v2: pseudogenome alignment, IQ-TREE tree and RAxML best tree byte-identical across
  replay; VCF records identical (only the dated `##bcftools_callCommand` header differs).
  Identical files rose from 37 (v1 recipe) to 89 of 113.
- Funcscan: the corrected route passes each sample's HMM search output to its AMPcombi command.
  The demo's 26 HMM models report no hits, so AMPcombi has none to summarize.
- Generated samplesheet: 2 paired samples from 4 FASTQs, md5 sidecars reported as ignored; the
  replay consumed the recorded sheet without re-scanning the directory.

## Features exercised end to end

- **Chain** fetchngs → rnaseq with a secret in `nxf_env`: SIGTERM during stage 2, resume without
  the secret refused, resume with it completed (rnaseq 100 tasks), `nfclaw chain status` lineage
  verified. No file contains the secret; Nextflow received the real value; `chain/` is 0700 and
  its records 0600.
- **MCP** through the official SDK against `nfclaw mcp`: check, real detached run, `get_job`,
  bounded `read_artifact` (512 bytes, truncated; traversal refused), `replay_run`,
  `verify_replay` (also with `require_environment`), and `cancel_job` (run recorded
  `terminated by SIGTERM`, no lingering processes).
- `nfclaw prepare-dramp`, `--check` preflight scope report, and `nfclaw assess` negative control.

## Host notes

- Disk was full (0.8 GB free). With the user's approval, 1,777 stale Nextflow `work/` trees
  (183 GB, untouched since before 2026-10-25) and unused Docker images were removed; records are in
  the review directory's `cleanup-record/`.
- A second dockerd configured with `"bridge": "none"` deletes the host's `docker0` interface, which
  breaks every container of the main daemon. The main daemon was restarted to recreate it.
- Tasks that download inside their container (funcscan's DeepARG data) stall on this VM because
  the host link has MTU 1450 while Docker's bridge uses 1500, the documented
  [MTU issue](../known-issues.md#downloads-inside-task-containers-stall-dockers-mtu-is-larger-than-the-hosts).
  The funcscan run used the documented host-network config.


## Post-merge follow-up

Main's first push-triggered runs after the merge (`9fd2a4c`) found:

- **Flaky browser test, real race.** `holding the search shortcut opens once and a new press closes
  it` passed on the PR and failed on main. The palette's global Ctrl/Cmd+K listener read `open`
  from a closure that a passive effect re-registered; the search input autofocuses during commit,
  so a key pressed right after it appeared could still see `open=false`. The state now lives in a
  ref updated by a layout effect and the listener is registered once. Production-build stress on
  the server, 80 repetitions with 4 workers: main's palette failed 21/80, the fix passed 80/80;
  typecheck, build and the whole browser suite (13/13) pass with the fix.
- **createtaxdb replay verification.** `nfclaw verify` now pairs exactly the names
  `kraken2-build --add-to-library` generates under `library/added/` (one to one, within their
  directory, bytes compared). Re-verifying the real replay: 0 missing/extra, 7 renamed (6 library
  files and the launch-stamped params file), environment identical.
- **Two transient workflow failures**, re-run: `smoke` (a runner's Docker did not respond) and
  `nextflow-validate` shard 7, where sarek 3.11.0's preview stalled for 12 minutes downloading the
  `nf-amazon` plugin from `registry.nextflow.io`. sarek 3.11.0 arrived in bot commit `18331a5`,
  whose push does not trigger that workflow; 3.10.0 needed the same plugin and passed. The same
  preview completes in 52 s on the server.

## Disposition of all 88 audit items

Status: **fixed** (implemented, with tests and evidence), **documented** (a stated limit, no code
change decided), **partial**, **upstream/external** (an nf-core pipeline defect or a prerequisite
nfclaw cannot supply: credentials, GPUs, full references, an unreleased upstream fix), **optional**
(a product decision the report itself lists as optional). "Here" means verified by this review's
fresh server executions.

| ID | Status | Disposition |
|---|---|---|
| B01–B09, B11–B19 | fixed | Ledger "Verified defect batch": each reproduced before its fix; regression tests in the suite. B03 (secret redaction), B07–B09 (MCP jobs) and B13–B18 (website) also exercised here. |
| B10 | fixed | Already fixed upstream in #215; regression test retained. |
| G01 | fixed | `--check` prints checked/deferred/unsupported scopes; real runs record `validation_scope`. Exercised here. |
| G02 | documented | [preflight.md](../preflight.md) states the supported schema subset; nf-schema stays authoritative. |
| G03, G04 | fixed (opt-in) | `nfclaw assess` contracts check sample coverage, record counts and format-aware content with reasoned tolerances. Exit status alone still cannot establish completeness without a contract. |
| G05 | fixed | `verify --require-environment`. Exercised here; correctly refuses refetched validation inputs. |
| G06 | partial | Container identities, plugins, configs and staged remote inputs are recorded. Conda environments, task-managed downloads and `includeConfig` targets are not frozen (stated in AGENTS.md). |
| G07 | partial | Refetched remote inputs are labelled (`read_by`) and refused by `--require-environment`. Bytes consumed during nf-schema validation are not captured; the 100 MiB refetch cap is unchanged. |
| G08 | fixed | Extracted replay source is rehashed after execution. |
| G09, G10 | documented | Tracked-byte source integrity scope and the before/after (not continuous) snapshot limit are stated; corrected working copies additionally bind file modes. Read-only staging is not implemented. |
| G11, G12, G13 | fixed | Structured MCP params, `replay_run`, bounded `read_artifact`. Exercised here through the official SDK. |
| G14 | partial | New validations are stored as commit-bound JSON under `evidence/`; older historical records were not converted. |
| G15 | fixed | Automatic publication requires real bundled tasks for every changed pin. |
| G16 | partial | CI runs the full Python suite on Ubuntu and macOS and an Apptainer demo. Real executions remain Linux amd64/Docker; no scheduler executors are exercised. |
| G17 | fixed | CI and publication require Python 3.11–3.15 on Ubuntu and macOS (all ten lanes green on the merged head). |
| G18 | fixed | Scientific CI artifacts are retained 90 days. |
| G19 | partial | The contract mechanism plus two exact-pin contracts (HGTseq, Tumourevo, both passing here); other pipelines and branches need their own contracts. |
| G20, G21 | fixed | Corrected stray-file wording; generation support matrix for all 95 pins in preflight.md. |
| G22 | documented | Cancellation is a process-group shutdown; detached containers, scheduler jobs and host crashes need executor reconciliation, which is not implemented. |
| G23 | fixed | Production-build Playwright suite runs in CI; its one flaky case was a real race, fixed above. |
| G24 | fixed | Institutional lookups use the supervised, budget-bound probe. |
| U01 | fixed | bamtofastq demo receives its matched reference. Here: 32/32 tasks, replay verified. |
| U02 | fixed | createtaxdb exact-pin Sourmash correction. Here: run, replay and (after the follow-up) verify pass. |
| U03 | fixed | HGTseq historical immutable fixture. Here: 63/63 tasks, replay verified, contract passes. |
| U04 | partial | `nfclaw prepare-dramp` builds a clean DRAMP reference (exercised here); the released AMPcombi 3.0.0 downloader still crashes upstream. |
| U05 | upstream/external | taxprofiler zero-hit outputs in some profilers; restricted configurations work. Not changed here. |
| U06 | fixed | Bactmap matched data, preserved module defaults, preview, deterministic alignment order and seeded trees. Here: 47/47 tasks, trees byte-identical across replay. |
| U07 | upstream/external | createpanelrefs, proteinfamilies and stableexpression previews wait on values preview never produces; recorded as known timeouts in the acceptance gate; real analyses pass. |
| U08, U18 | upstream/external | multiplesequencealign preview hang (known timeout) and the unavailable `learnmsa:2.0.9` image. |
| U09 | documented | marsseq needs a separate reference build; its `mm10` key selects GRCm39 (known-issues). |
| U10, U20 | upstream/external | rnafusion reference placeholders and a full GRCh38 build, which needs more disk than this host has. |
| U11 | fixed | Tumourevo receives the intended `sparsesignatures_k=2:3`. Here: 66/66 tasks, contract and replay identical. |
| U12, U21 | upstream/external | Engine syntax (cutandrun) and ignored task failures (cutandrun, hicar, mag); nfclaw reports ignored failures as completion caveats. |
| U13 | upstream/external | MultiQC exports under macOS arm64 emulation; no arm64 execution host. The Linux route is verified. |
| U14 | upstream/external | sopa's demo data is a mutable GitHub HTML page; the replay's environment check correctly fails (known-issues). |
| U15 | upstream/external | seqsubmit's real ENA submission needs credentials and authorization; stub coverage only. |
| U16, U17 | upstream/external | ProteinFold real prediction and lsmquant GPU quantification need GPUs and databases; ProteinFold's stub demo is reported as a caveat. |
| U19, U28 | upstream/external | rnasplice LeafCutter/RegTools branches not executed; MISO/Salmon variation characterized only by snapshot checks. |
| U22 | fixed | Nonempty CreatePanelRefs antitarget control (ledger U22). |
| U23 | fixed | FastQRepair demo exercises paired repair. Here: `BBMAP_REPAIR (paired_control)` ran in both runs, 646/646 pairs retained. |
| U24 | upstream/external | circdna's `test_AA` profile is stub-only upstream. |
| U25, U29 | partial | rnaseq demo replay verified here (234/234 tasks, identical environment); broader benchmarks were not run. |
| U26 | documented | ampliseq's unseeded DADA2/QIIME2 randomness is announced before launch and in known-issues. |
| U27 | upstream/external | genomeassembler Flye replay differences are documented, not resolved. |
| U30 | fixed (createtaxdb) / documented | createtaxdb's random names are now paired by `verify`; the others are classified one by one in known-issues ("Outputs that differ between a run and its replay by design"). No broad ignoring of renamed files. |
| O01–O15 | optional | Product decisions the report lists as optional; none were implemented in this remediation. |
