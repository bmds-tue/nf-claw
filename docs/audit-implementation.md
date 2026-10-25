# Audit implementation and validation ledger

Started 25 October 2026 from `1de7a43` (audit baseline `a2b9730`).
Branch: `br/audit-implementation`. The user's subsequent instruction authorizes
merging after the implementation, review and server validation are complete.
Release publication and replacement of the active server installation remain out
of scope.

## Working locations and safety

- macOS denies access to the original Desktop checkout. It has not been modified.
- Isolated local checkout: `~/.codex/workspaces/nf-claw-audit-implementation`.
- SSH alias: `denbi_instance`; host: `danilo-instance`, Linux x86_64.
- Initial capacity: 28 CPUs, 62 GiB RAM (54 GiB available), volume 182 GiB free,
  45.6 million free inodes. Other Nextflow/container analyses are active.
- Active installation `/home/ubuntu/volume/nf-claw` was at `1e08f6b`; leave it intact.
- Server tools: Python 3.12.3, Git 2.43.0, Java 17.0.20.1, Nextflow 26.04.3,
  Node 22.23.2, npm 10.9.8, Docker 29.1.3. No Podman/Apptainer/Singularity on PATH.
- Start at one workload, at most 4 task CPUs and 8 GiB; reassess capacity before
  larger batches. Keep separate inputs, results, work and engine state. Retain
  logs and never prune shared images/caches or stop existing analyses.

## Checklist

An implementation is not accepted until its regression tests and applicable
server checks pass. Preview and stub execution never count as scientific execution.

| Area | Reproduced defect or scope | Implementation | Validation / blockers |
| --- | --- | --- | --- |
| 1 Resume attribution | Scalar/config/source changes evade input-only resume guard | `865a3b9`, `b054477`; analysis identity and whole-run preservation | 8 native resume/cache/replay cases passed remotely on `865a3b9`, both 25.10.4 and 26.04.0; final candidate rerun pending |
| 2 createtaxdb | Nightly `40181265673`, shard 4 timed out | Investigating retained logs; no exception added | Exact preview passed on server and GitHub rerun attempt 2; original stalled call remains unidentifiable without a thread dump |
| 3 Container identity | Mutable reference inspection deduplicated for 600 seconds | `a3ede23`; inspect container then immutable image, retain cached-task identities | 68 focused local cases and 13 server cases passed, including isolated live retag-before-inspection experiment |
| 4 Execution gates | Preview does not execute tasks | Pending | Selected-pin policy and rotating sweep needed |
| 5 Complete evidence / offline | Historical strict mode permits missing evidence | Pending | Preserve compatibility; new opt-in contract and offline run needed |
| 6 Acceptance policy | Caveated successful stages feed consumers | `05c98e7`; structured categories and repeatable reject policy in CLI/chain/MCP | Focused local suites passed; strict native cases rejected correctly; permissive native fixture exposed a same-name copy error, corrected locally pending rerun |
| 7 Composition / handoffs | Sequential controller; re-count registry | Pending | DAG scheduling, lineage, examples and real handoff checks needed |
| 8 Packaging / release | Installed library assumes adjacent source content | `05dac65`, `fefb9a7`; external library root, independent installs, preparation workflow and constraints | Clean local wheel and sdist installations discover all 94 pipelines; minimum-dependency focused checks passed (older SDK cannot run its modern-client test); server/final gates pending |
| 9 Browser regressions | No committed browser suite | Implemented production-export Playwright/axe suite and CI gate | Local desktop/mobile browser checks passed, including global parameter-index handoff; typecheck, production base-path build, parser checks and dependency audit passed; server/final CI pending |
| 10 Full-text search | Document title/filename search only | Build-time, lazily fetched section index with renderer IDs, snippets and literal query handling | Error-remedy navigation, duplicate heading IDs, code examples, unsafe queries, lazy loading and existing parameter search tested successfully |
| 11 Agent context | Both entry points were 42,587 bytes | `4a7b48e`; moved full content into five focused guides | Both entry points now 4,851 bytes (88.6% smaller); synchronization and guidance regressions passed |
| 12 Diagnostics / jobs | Prose parsing; unbounded list; no retention policy | `05dac65`; doctor, JSON status/verify, observed trace progress, bounded pages and lease-protected metadata pruning | Focused CLI/MCP/job tests and current-SDK interoperability passed locally; broader server suite running |

## Final acceptance gates

- [ ] Full Python suite with development and YAML extras, native Nextflow suites,
  official MCP SDK modes, Ruff and repository checks.
- [ ] All pinned source/registry/catalog/documentation drift checks.
- [ ] Package builds and installation outside source checkout; dependency bounds.
- [ ] Website audit, typecheck, production build and browser suite.
- [ ] Exact final candidate tested remotely: execution, resume, replay, verify,
  chains, cancellation, detached jobs, immutable images and offline preparation.
- [ ] Every registered pipeline has exact-pin source/engine/input/preview records
  and honest executed/stub/preview/failed/blocked classifications.
- [ ] Independent output checks for the executed workflows; preserve artifacts.
- [ ] Review findings resolved, CI green, merge authorized candidate on GitHub.

## Evidence notes

The GitHub connector confirms the audit's nightly job failed while the other
seven shards passed. Current GitHub main is two documentation commits past the
audit baseline; neither changes these runtime defects. No open PR existed at
initial inspection. New implementation and validation evidence will be appended
here and linked to the final server report and pipeline matrix.

## Durable session state

- Server task root: `/home/ubuntu/volume/nfclaw-acceptance-20261025`, with separate
  `repo`, `venv`, `inputs`, `results`, `work`, `engine` and `evidence` directories.
- Latest server candidate is `4d727dd`. All 94 pinned source checkouts have been
  initialized there. Do not update that checkout while its full suite is running.
- Full suite PID initially `621326`; log `evidence/full-4d727dd.log`, JUnit
  `evidence/full-4d727dd.xml`, retained fixtures `results/full-4d727dd`.
- Prior native resume log `evidence/resume-native-865a3b9.log`: 8 passed.
- Container log `evidence/container-a3ede23.log`: 13 passed, including live Docker.
- Passing server preview logs: `evidence/createtaxdb-reproduction/`. The earlier
  bootstrap attempt in `createtaxdb-preview*` lacked the IPv6 JVM setting and is
  separate failed environmental evidence, not a pipeline acceptance.
- Dedicated engine cache was seeded by copying existing framework jars and plugin
  files; shared engine caches and active installations were not pruned or replaced.
- GitHub connector can read Actions evidence but cannot rerun jobs (403). Existing
  GitHub CLI authorization successfully reran only shard 4; attempt 2 is green.
- Original nightly artifacts are retained locally under this chat's visualization
  directory in `nightly-acceptance-4/`; inspect engine log before attributing the
  timeout to a particular network call or upstream race.
- Current local browser work has installed Playwright/axe, a production static
  server, full-text search and browser tests. Browser cache is
  `~/.codex/workspaces/nf-claw-browser-cache`; ignore test result/report directories.
- Two resource-bounded preview shards are running for every registered pipeline
  at server revision `4d727dd`: controller PID initially `662606`; logs and unique
  TSV classifications under `evidence/previews-4d727dd/`. These are previews only.
- Generated samplesheet annotation changes were independently reproduced as an
  additional resume edge case; their exact generated bytes now join the analysis
  identity, and focused regressions pass. Ordinary input-only identities retain
  their existing components.
- Remaining major implementation: execution-gated maintenance/rotation (4), complete
  evidence and offline preparation (5), DAG composition/new handoffs (7), and
  stronger preview timeout diagnostics (2). Browser/server/final CI still need
  validation on the final revision.
- No PR has been created and nothing has been merged. The final revision still
  needs the complete server matrix and actual registered pipeline executions.
