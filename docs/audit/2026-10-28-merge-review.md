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
| createtaxdb 3.1.0 demo (Sourmash correction) | 32/32 | 6 missing/6 extra: the documented random `kraken2-build` library names; all six pairs byte-identical | refused for the same structural difference |
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
- On this IPv6-only host, tasks that download inside the container (funcscan's DeepARG data)
  need `docker.runOptions = '--network host'`.

## Not covered by this review

Items the ledger leaves open (for example G06 transitive dependencies, G16 executor coverage and
U items needing external prerequisites) remain as documented there; no claim is made for them.
