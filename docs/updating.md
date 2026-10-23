# Automated Updating & Maintenance

nf-claw maintains synchronization with upstream nf-core pipeline releases through fully automated workflows and a strict, bidirectional schema drift gate. No context file (`skill.md`, `reference.md`, or `catalog.*`) is ever edited manually.

---

### Navigation

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
4. **Comprehensive In-Job Validation:**
   - Runs `scripts/nextflow_accept.sh` (`nextflow -preview`) to verify pipeline compilation, profile resolution, and parameter validation.
   - Requires one unique `accepted` verdict for every changed pipeline. A matching documented upstream exception can keep the nightly preview workflow green, but cannot authorize an automated release merge.
   - Executes the complete pytest suite.
   - Runs the website parsing tests, which check that the site reads every regenerated `skill.md`, with the site's own TypeScript. The step fails if they are skipped.
   - Runs Ruff, the website dependency audit, TypeScript checks and the static site build. These gates run in the maintenance job before it can publish anything.
   - Runs the drift gate (`python3 -m librarian.check_drift`).
5. **Automatic Publication:** After every validation gate passes, `scripts/publish_validated_update.sh` uses a separate Git index to stage only the generated pipeline files, catalogs and `.gitmodules` (plus `sources.tsv` for discovery). It creates one commit directly on the exact `main` the job validated and pushes it to a temporary branch named `maintenance-<kind>-<run-id>-<attempt>`.
   - **No organization change or extra token:** the bots use the built-in `GITHUB_TOKEN` and never create or approve a pull request. They report the completed core checks on the generated commit and fast-forward `main` under its existing rules. The ruleset still requires those checks, prevents force pushes and has no bypass actor. It permits checked direct updates; a future requirement to publish through PRs would prevent this route and be reported as a failure.
   - **Exact commit and source scope:** the publisher verifies the temporary branch's commit and parent before reporting checks. An isolated staging index keeps unrelated build files and existing staging out of the commit. Checkouts retain `persist-credentials: false`; only the final push authenticates, through a temporary Git credential helper.
   - **Concurrent changes:** if `main` moves during validation, the publisher preserves it and leaves a notice and the candidate branch. The next scheduled maintenance run starts from the new `main`, regenerates the update and repeats validation. It never rebases an unvalidated combination or force-pushes. Actual check-reporting, permission, network or rule failures fail the job.
   - **Follow-up workflows:** after publication, the temporary branch is removed and the job explicitly dispatches `tests.yml`, `smoke.yml`, `codeql.yml` and `deploy-pages.yml`. `GITHUB_TOKEN` pushes do not trigger ordinary push workflows. Every dispatch is attempted, and any dispatch failure is reported as a failed job so it cannot silently leave the website or checks stale.
   - **One at a time:** both maintenance workflows share the `nfclaw-maintenance` concurrency group and check out `main` as it is when the job starts, so a run queued behind the other validates and publishes on top of what the first one published.
6. **Error Reporting:** The maintenance scan attempts every source and returns failure after the scan if any remote could not be reached, rather than reporting that failure as "no new releases."

---

## 3. Automated Weekly Discovery (`discover-pipelines.yml`)

The `.github/workflows/discover-pipelines.yml` workflow runs weekly to onboard newly created nf-core pipelines:

1. **DSL2 Filtering:** Inspects the nf-core pipeline registry, excluding archived or disabled entries and entries explicitly marked `is_DSL2: false`. A missing marker alone does not exclude a candidate; the Nextflow acceptance gate must still pass before onboarding. Legacy DSL1 workflows are unsupported.
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
   - A recognized remote-input staging failure is labelled `staging-unverified`; any other
     failure, including a preview that exceeds its time limit, is labelled `rejected`. Neither
     authorizes an automated merge.
   - `rejected` and `staging-unverified` additions are pruned before committing, and are
     considered again by the next run. An incomplete result or unrecognized verdict fails the
     batch instead of merging it.
5. **Batch Publication:** Validated additions must pass the tests (including non-skipped website parsing), Ruff, the drift gate, website dependency audit, type check and build. The same publisher commits the complete generated inventory, including new gitlinks and `sources.tsv`, reports the completed checks and fast-forwards `main` as for daily updates, then dispatches tests, smoke checks, CodeQL and Pages deployment.

---

## 4. The Schema Drift Gate (`librarian/check_drift.py`)

The drift gate guards against divergence between pinned code and documentation:

| Audit Check | Component Validated | Validation Mechanism |
|---|---|---|
| **Manifest Equivalence** | `sources.tsv`, `.gitmodules`, `pipelines/` | Asserts exact equality of pipeline inventory and git remote URLs. |
| **Context Parity** | `skill.md`, `reference.md`, `catalog.*` | Recompiles context in memory and verifies character-for-character equality against disk. |
| **Handoff Verification** | `handoffs/*.json` rules | Validates parameter mappings and downstream column compatibility against pinned schemas. Published file existence and identity are checked at runtime. |
| **Agent Guidelines Parity** | `AGENTS.md` and `CLAUDE.md` | A separate pytest check (`tests/test_agent_docs.py`), run by `make check`, enforces 100% byte-for-byte identity. |

If any upstream pipeline is updated without regenerating context, or if a manual edit is introduced, `make check` fails immediately.

---

## 5. Manual Maintenance Commands

Developers can run maintenance tasks locally from the repository root with Python 3.11+
and initialized submodules. Install test dependencies with `pip install -e ".[dev,yaml]"`.
Change generators rather than editing generated context, then run `make build` and
`make check`. `make update` fetches tags, changes submodule checkouts and stages their
gitlinks; review those changes before committing. It does not run the CI acceptance gate:

| Command | Action |
|---|---|
| `make update` | Queries remotes, bumps submodules to newest tags, and regenerates context files. |
| `make build` | Regenerates `skill.md`, `reference.md`, and `catalog.*` from current submodules. |
| `make check` | Runs the schema drift gate followed by the full pytest suite. |
| `make test` | Executes all unit, integration, and regression tests. |
