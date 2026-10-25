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
| 1 Resume attribution | Scalar/config/source changes evade input-only resume guard | Pending | Audit real-engine reproduction retained; add candidate regressions |
| 2 createtaxdb | Nightly `40181265673`, shard 4 timed out | Investigating | Retained engine log and server reproduction pending |
| 3 Container identity | Mutable reference inspection deduplicated for 600 seconds | Pending | Deterministic race and live isolated Docker probe pending |
| 4 Execution gates | Preview does not execute tasks | Pending | Selected-pin policy and rotating sweep needed |
| 5 Complete evidence / offline | Historical strict mode permits missing evidence | Pending | Preserve compatibility; new opt-in contract and offline run needed |
| 6 Acceptance policy | Caveated successful stages feed consumers | Pending | CLI/chain/MCP rejection policy and integration coverage needed |
| 7 Composition / handoffs | Sequential controller; re-count registry | Pending | DAG scheduling, lineage, examples and real handoff checks needed |
| 8 Packaging / release | Installed library assumes adjacent source content | Pending | Wheel/sdist, external data root, constraints and release preparation needed |
| 9 Browser regressions | No committed browser suite | Pending | Production export, base path, keyboard/mobile/accessibility needed |
| 10 Full-text search | Document title/filename search only | Pending | Build-time section index and snippets needed |
| 11 Agent context | Both entry points about 42.6 KB | Pending | Preserve content in focused docs and byte-identical entry points |
| 12 Diagnostics / jobs | Prose parsing; unbounded list; no retention policy | Pending | Structured contract, diagnostics, progress, preview-only prune default needed |

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
