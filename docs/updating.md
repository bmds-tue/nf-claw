# Automated Updating & Maintenance

nf-claw maintains synchronization with upstream nf-core pipeline releases through fully automated workflows and a strict, bidirectional schema drift gate. No context file (`skill.md`, `reference.md`, or `catalog.*`) is ever edited manually.

---

### Navigation

[Version Policy](#1-version-policy--upstream-tracking) • [Daily Updates](#2-automated-daily-updates-auto-updateyml) • [Weekly Discovery](#3-automated-weekly-discovery-discover-pipelinesyml) • [Schema Drift Gate](#4-the-schema-drift-gate-librariancheck_driftpy) • [Maintenance Commands](#5-manual-maintenance-commands)

---

## 1. Version Policy & Upstream Tracking

Tracking policies are declared in `sources.tsv`:
- Each row contains `name<TAB>url<TAB>version-policy`.
- The primary policy is `latest-release`, directing automation to track the newest official git release tag.
- Submodules pin exact commits resolved from release tags. Tags can be moved upstream, but a
  committed gitlink remains tied to its recorded commit until deliberately updated.

---

## 2. Automated Daily Updates (`auto-update.yml`)

The `.github/workflows/auto-update.yml` workflow executes daily:

```
┌─────────────────────────┐     ┌───────────────────────────┐     ┌─────────────────────────┐
│ 1. Git Tag Discovery    │ ──► │ 2. Submodule Checkout     │ ──► │ 3. Context Generation   │
│ git ls-remote --tags    │     │ Pinned to latest tag      │     │ make build              │
└─────────────────────────┘     └───────────────────────────┘     └─────────────────────────┘
                                                                               │
                                ┌───────────────────────────┐                  ▼
                                │ 5. Automated Merge        │ ◄── ┌─────────────────────────┐
                                │ Squash merge into main    │     │ 4. Validation Gate      │
                                └───────────────────────────┘     │ Nextflow + Tests + Drift│
                                                                  └─────────────────────────┘
```

1. **Tag Discovery:** Queries upstream remotes via `git ls-remote --tags` (using standard git protocol to bypass GitHub REST API rate limits).
2. **Deterministic Bumping:** When a newer release tag is discovered for a `latest-release` pipeline, the workflow checks out that tag in `pipelines/<name>/upstream`.
3. **Context Regeneration:** Invokes `librarian/write_skill.py` and `librarian/write_catalog.py` to regenerate all parameter tables, input schemas, tool lists, and catalog manifests.
4. **Comprehensive In-Job Validation:**
   - Runs `scripts/nextflow_accept.sh` (`nextflow -preview`) to verify pipeline compilation, profile resolution, and parameter validation.
   - Requires one unique `accepted` verdict for every changed pipeline. A matching documented upstream exception can keep the nightly preview workflow green, but cannot authorize an automated release merge.
   - Executes the complete pytest suite.
   - Runs the website parsing tests, which check that the site reads every regenerated `skill.md`, with the site's own TypeScript. The step fails if they are skipped. The merged PR triggers no `tests.yml` run, so this is the only check before the site is redeployed.
   - Runs the drift gate (`python3 -m librarian.check_drift`).
5. **Automated Merging:** Only when all validation checks pass with exit code 0 is the PR automatically squash-merged into `main`, which dispatches `deploy-pages.yml` to refresh the live site.
6. **Error Reporting:** The maintenance scan attempts every source and returns failure after the scan if any remote could not be reached, rather than reporting that failure as "no new releases."

---

## 3. Automated Weekly Discovery (`discover-pipelines.yml`)

The `.github/workflows/discover-pipelines.yml` workflow runs weekly to onboard newly created nf-core pipelines:

1. **DSL2 Filtering:** Inspects the nf-core pipeline registry, onboarding only **DSL2** pipelines (legacy DSL1 workflows are permanently ignored).
2. **Name Sanitization & Security:**
   - Every candidate pipeline name is strictly validated: alphanumeric characters, dots, hyphens, and underscores, bounded by alphanumeric characters:
     ```regex
     ^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$
     ```
   - Remotes are deterministically constructed as `https://github.com/nf-core/<validated-name>.git`. Mutable catalog metadata cannot redirect automation to external repositories.
3. **Scaffolding:** Adds the submodule, pins its newest release tag, and generates initial context files.
   - Discovery shares the runner's submodule writer lock and checks ownership before mutation. Existing pipeline entries, Git index entries, registrations and cached object stores are preserved, including caches in linked worktrees. Reinitializing an existing pipeline is a separate `git submodule update --init pipelines/<name>/upstream` operation.
   - Git commands cannot wait for credential prompts. Clone and tag-fetch operations have a 300-second bound; other discovery Git commands have a 60-second bound. Timeout and handled interruption stop the command's process group before failure cleanup.
   - A failed owned addition restores the original `.gitmodules` working bytes and permission bits, its staged blob and its assume-unchanged, skip-worktree and intent-to-add state. Unmerged or nonregular metadata is refused before adding a pipeline. Cleanup removes only the newly reserved pipeline entry and its new cache; explicit `--rollback NAME` remains a request to remove that pipeline.
   - Partial addition failures return a nonzero status after attempting the remaining candidates, so incomplete discovery cannot reach the batch auto-merge gate.
4. **Strict Acceptance Gate:** Evaluates each candidate via `scripts/nextflow_accept.sh`.
   - Nextflow must compile, resolve configurations, and validate schema with **strict exit code 0**.
   - A recognized remote-input staging failure is labelled `staging-unverified`; other failures
     and timeouts are `rejected`. Both verdicts fail the gate.
   - Rejected pipelines are pruned before committing.
5. **Batch Auto-Merge:** Validated additions that pass the tests (including the website parsing tests, which must not be skipped) and the drift gate are committed and merged.

---

## 4. The Schema Drift Gate (`librarian/check_drift.py`)

The drift gate guards against divergence between pinned code and documentation:

| Audit Check | Component Validated | Validation Mechanism |
|---|---|---|
| **Manifest Equivalence** | `sources.tsv`, `.gitmodules`, `pipelines/` | Asserts exact equality of pipeline inventory and git remote URLs. |
| **Context Parity** | `skill.md`, `reference.md`, `catalog.*` | Recompiles context in memory and verifies character-for-character equality against disk. |
| **Handoff Verification** | `handoffs/*.json` rules | Validates that parameter mappings and column transformations fit pinned upstream and downstream schemas. |
| **Agent Guidelines Parity** | `AGENTS.md` and `CLAUDE.md` | `tests/test_agent_docs.py` enforces 100% byte-for-byte identity. |

If any upstream pipeline is updated without regenerating context, or if a manual edit is introduced, `make check` fails immediately.

---

## 5. Manual Maintenance Commands

Developers can run maintenance tasks locally:

| Command | Action |
|---|---|
| `make update` | Queries remotes, bumps submodules to newest tags, and regenerates context files. |
| `make build` | Regenerates `skill.md`, `reference.md`, and `catalog.*` from current submodules. |
| `make check` | Runs the schema drift gate followed by the full pytest suite. |
| `make test` | Executes all unit, integration, and regression tests. |
