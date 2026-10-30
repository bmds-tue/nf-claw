# Automated Updating & Maintenance

nf-claw maintains synchronization with upstream nf-core pipeline releases through fully automated workflows and a strict, bidirectional schema drift gate. No context file (`skill.md`, `reference.md`, or `catalog.*`) is ever edited manually.

---

## Navigation

[Version Policy](#1-version-policy--upstream-tracking) • [Daily Updates](#2-automated-daily-updates-auto-updateyml) • [Weekly Discovery](#3-automated-weekly-discovery-discover-pipelinesyml) • [Schema Drift Gate](#4-the-schema-drift-gate-librariancheck_driftpy) • [Maintenance Commands](#5-manual-maintenance-commands)

---

## 1. Version Policy & Upstream Tracking

Tracking policies are declared in `sources.tsv`:
- Each row contains `name<TAB>url<TAB>version-policy`.
- The primary policy is `latest-release`, directing automation to select the highest numeric
  `X.Y.Z` release tag (optional `v` prefix); prereleases and two-component tags are excluded
  from automated bumping. Other policies are skipped by the updater. Explicit runtime
  version selection also supports older `X.Y` tags.
- Submodules pin exact commits resolved from release tags. Tags can be moved upstream, but a
  committed gitlink remains tied to its recorded commit until deliberately updated.

---

## 2. Automated Daily Updates (`auto-update.yml`)

The `.github/workflows/auto-update.yml` workflow executes daily:

```
┌───────────────────────────┐     ┌───────────────────────────┐     ┌───────────────────────────┐
│ 1. Git Tag Discovery      │ ──► │ 2. Submodule Checkout     │ ──► │ 3. Context Generation     │
│ git ls-remote --tags      │     │ Pinned to latest tag      │     │ make build                │
└───────────────────────────┘     └───────────────────────────┘     └───────────────────────────┘
                                                                                  │
                                  ┌───────────────────────────┐                   ▼
                                  │ 5. Publish Validated Code │ ◄── ┌───────────────────────────┐
                                  │ Fast-forward into main    │     │ 4. Validation Gate        │
                                  └───────────────────────────┘     │ Nextflow + Tests + Drift  │
                                                                    └───────────────────────────┘
```

1. **Tag Discovery:** Queries upstream remotes via `git ls-remote --tags` (using standard git protocol to bypass GitHub REST API rate limits).
2. **Deterministic Bumping:** When a newer release tag is discovered for a `latest-release` pipeline, the workflow checks out that tag in `pipelines/<name>/upstream`.
3. **Context Regeneration:** Invokes `librarian/write_skill.py` and `librarian/write_catalog.py` to regenerate all parameter tables, input schemas, tool lists, and catalog manifests.
4. **Freeze and validate one candidate:** After unique completed preview acceptance, a read-only
   preparation job creates a generated-path-only commit and immutable Git-bundle artifact. Its
   exact commit is checked by the complete Ubuntu/macOS Python 3.11–3.15 matrix, site/browser/parser
   tests, real Nextflow integration, Ruff and generated drift. Every changed pipeline must also
   complete actual bundled tasks; stub-only, incomplete or failed runs cannot authorize publication.
5. **Automatic publication:** A fresh trusted-base job independently checks raw matrix/native
   evidence before publishing that exact prevalidated commit. It alone has write permissions.
   Main is updated atomically against the expected validated parent, with no unchecked rebase or
   post-validation commit. A moved main defers publication; permission, rule, network or
   follow-up dispatch failures remain failures. Both bots share one concurrency group and bind
   preparation to their event commit; a queued stale run defers rather than changing main.
   The [publication evidence policy](maintenance.md) defines resources, artifact identities,
   supported skips, retention, reruns and the limits of actual-task evidence. The bots retain the
   existing checked fast-forward route and dispatch tests, smoke, CodeQL and Pages after publication.
6. **Error Reporting:** The maintenance scan attempts every source and returns failure after the scan if any remote could not be reached, rather than reporting that failure as "no new releases."

---

## 3. Automated Weekly Discovery (`discover-pipelines.yml`)

The `.github/workflows/discover-pipelines.yml` workflow runs weekly to onboard newly created nf-core pipelines:

1. **DSL2 Filtering:** Inspects the nf-core pipeline registry, excluding archived or disabled entries and entries explicitly marked `is_DSL2: false`. A missing marker alone does not exclude a candidate; the Nextflow acceptance gate must still pass before onboarding. Legacy DSL1 workflows are unsupported.
2. **Name Sanitization & Security:**
   - Every candidate pipeline name must satisfy the [pipeline-name rule](../CONTRIBUTING.md#step-1-validate-the-pipeline-name).
   - Remotes are deterministically constructed as `https://github.com/nf-core/<validated-name>.git`. Mutable catalog metadata cannot redirect automation to external repositories.
3. **Scaffolding:** Adds the submodule, pins its newest release tag, and generates initial context files.
   - Discovery shares the runner's submodule writer lock and checks ownership before mutation. Existing pipeline entries, Git index entries, registrations and cached object stores are preserved, including caches in linked worktrees. Reinitializing an existing pipeline is a separate `git submodule update --init pipelines/<name>/upstream` operation.
   - Git commands cannot wait for credential prompts. Clone and tag-fetch operations have a 300-second bound; other discovery Git commands have a 60-second bound. Timeout and handled interruption stop the command's process group before failure cleanup.
   - A failed owned addition restores the original `.gitmodules` working bytes and permission bits, its staged blob and its assume-unchanged, skip-worktree and intent-to-add state. Unmerged or nonregular metadata is refused before adding a pipeline. Cleanup removes only the newly reserved pipeline entry and its new cache; explicit `--rollback NAME` remains a request to remove that pipeline.
   - Partial addition failures return a nonzero status after attempting the remaining candidates, so incomplete discovery cannot reach the batch publication gate.
4. **Strict Acceptance Gate:** Evaluates each candidate via `scripts/nextflow_accept.sh`.
   - Nextflow must compile, resolve configurations, and validate schema with **strict exit code 0**.
   - A recognized remote-input staging failure is labelled `staging-unverified`; any other
     failure, including a preview that exceeds its time limit, is labelled `rejected`. Neither
     authorizes an automated merge.
   - `rejected` and `staging-unverified` additions are pruned before committing, and are
     considered again by the next run. An incomplete result or unrecognized verdict fails the
     batch instead of merging it.
5. **Batch publication:** Surviving additions are frozen as one candidate and pass the same
   full matrix, site, integration, drift and actual-task gates as daily updates. A failure in
   real execution blocks the frozen candidate rather than silently dropping that pipeline.
   The isolated publisher verifies raw evidence and updates main only from its validated parent.


---

## 4. The Schema Drift Gate (`librarian/check_drift.py`)

The drift gate guards against divergence between pinned code and documentation:

| Audit Check | Component Validated | Validation Mechanism |
|---|---|---|
| **Manifest Equivalence** | `sources.tsv`, `.gitmodules`, `pipelines/` | Asserts exact equality of pipeline inventory and git remote URLs. |
| **Context Parity** | `skill.md`, `reference.md`, `catalog.*` | Recompiles context in memory and verifies character-for-character equality against disk. |
| **Handoff Verification** | `handoffs/*.json` rules | Validates parameter mappings and downstream column compatibility against pinned schemas. Published file existence and identity are checked at runtime. |

If any upstream pipeline is updated without regenerating context, or if a manual edit is introduced, `make check` fails immediately.

---

## 5. Manual Maintenance Commands

Developers can run maintenance tasks locally from the repository root with Python 3.11+
and initialized submodules. Install test dependencies with `pip install -e ".[dev,yaml]"`.
Change generators rather than editing generated context, then run `make build` and
`make check`. `make update` fetches tags, changes submodule checkouts and stages their
gitlinks; review those changes before committing. It does not run the CI acceptance gate.
[CONTRIBUTING.md](../CONTRIBUTING.md#makefile-targets-summary) lists every target.
