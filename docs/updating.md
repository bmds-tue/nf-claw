# Updating and discovery

How nf-claw follows nf-core releases. Two scheduled workflows bump the pins to new releases and add
new pipelines, and a drift gate checks that the generated files match the pinned code. Generated
files (`skill.md`, `reference.md`, `catalog.*`) are never edited by hand.

---

## Navigation

[Update policy](#update-policy) • [Daily updates](#daily-updates-auto-updateyml) • [Weekly discovery](#weekly-discovery-discover-pipelinesyml) • [Drift gate](#drift-gate-librariancheck_driftpy) • [Running maintenance locally](#running-maintenance-locally)

---

## Update policy

`sources.tsv` has one row per pipeline: `name<TAB>url<TAB>policy`.

- `latest-release` lets the updater move the pin to the highest `X.Y.Z` release tag (with or
  without a `v` prefix). Prereleases and two-part tags are never picked automatically, though
  `--pipeline-version` can still run older `X.Y` tags.
- Any other policy makes the updater skip the pipeline. `hold` keeps it at its current pin, for a
  release that cannot pass the publication gate and would otherwise hold back every other bump
  ([publication policy](maintenance.md)).
- A submodule pins the commit a tag pointed to. If the tag is later moved upstream, the committed
  pin stays on its recorded commit until it is updated on purpose.

---

## Daily updates (`auto-update.yml`)

`.github/workflows/auto-update.yml` runs every day at 06:00 UTC:

1. It lists each pipeline's tags with `git ls-remote --tags`, which avoids GitHub API rate limits.
2. For a `latest-release` pipeline with a newer release, it checks out that tag in
   `pipelines/<name>/upstream`.
3. It regenerates the skills, references and catalogs (`librarian/write_skill.py`,
   `librarian/write_catalog.py`).
4. Each bumped release must pass a Nextflow preview ([preview acceptance](compatibility.md#preview-acceptance)).
   A read-only job then commits only the generated paths and the pins, and stores that commit as an
   immutable Git bundle. That exact commit must pass the full test matrix (Ubuntu and macOS,
   Python 3.11–3.15), the website, parser and browser tests, the Nextflow integration tests, Ruff and
   the drift gate. Every changed pipeline must also complete a real run of its bundled test;
   stub-only, incomplete or failed runs block publication.
5. A separate publisher job, started from the trusted base and the only job with write permission,
   checks the raw test and run evidence and then fast-forwards `main` to that exact commit. Nothing
   is rebased or committed after validation. If `main` moved in the meantime, publication is
   deferred to the next run; permission, ruleset, network and dispatch failures are reported as
   failures. Both bots share one concurrency group and start from the commit that triggered them,
   so a stale queued run defers instead of changing `main`. After publishing, the bots start the
   tests, smoke, CodeQL and Pages workflows. The [publication policy](maintenance.md) gives the
   resources, artifacts, allowed skips, retention, reruns and the limits of this evidence.
6. The scan tries every source. If any remote could not be reached, the run fails after the scan
   instead of reporting "no new releases".

---

## Weekly discovery (`discover-pipelines.yml`)

`.github/workflows/discover-pipelines.yml` runs every Monday at 07:00 UTC to add pipelines nf-core
has released since the last run:

1. It reads the nf-core pipeline list and skips archived and disabled pipelines and those marked
   `is_DSL2: false`. A pipeline without a DSL2 marker is not skipped for that reason, but it must
   still pass the acceptance gate. DSL1 pipelines are not supported.
2. Every name must pass the [pipeline name rule](../CONTRIBUTING.md#1-check-the-name), and the
   remote is always built as `https://github.com/nf-core/<name>.git`, so catalog metadata cannot
   point the workflow at another repository.
3. It adds the submodule, pins the newest release tag and generates the pipeline's files.
   - Discovery uses the runner's submodule lock and checks ownership before it changes anything.
     Existing pipelines, index entries, registrations and cached object stores are kept, including
     caches in linked worktrees. Re-initialising an existing pipeline is done separately with
     `git submodule update --init pipelines/<name>/upstream`.
   - Git never waits for a credential prompt. Clones and tag fetches time out after 300 seconds,
     other Git commands after 60; a timeout or interruption stops the command's process group before
     cleanup.
   - If an addition fails, discovery restores `.gitmodules` (bytes and permissions), its staged
     blob and its assume-unchanged, skip-worktree and intent-to-add flags. Unmerged or unusual
     metadata is refused before anything is added. Cleanup removes only the entry and cache it
     created; `--rollback NAME` asks to remove that pipeline.
   - If some additions fail, discovery still tries the rest and then exits non-zero, so an
     incomplete batch never reaches publication.
4. Each candidate runs through `scripts/nextflow_accept.sh`. Its preview must exit 0. A recognised
   remote staging failure is labelled `staging-unverified`; any other failure, a timeout included,
   is `rejected`. Neither can be published. Rejected and staging-unverified additions are dropped
   before the commit and tried again next week. An incomplete result or an unknown verdict fails
   the whole batch.
5. The remaining additions become one candidate and go through the same gate and publisher as the
   daily updates (`maintenance-gate.yml`). A failed real run blocks the whole candidate instead of
   quietly dropping that pipeline.

---

## Drift gate (`librarian/check_drift.py`)

| Check | Files | How |
|---|---|---|
| Registrations | `sources.tsv`, `.gitmodules`, `pipelines/` | The pipeline lists and remote URLs must be identical. |
| Generated files | `skill.md`, `reference.md`, `catalog.*` | Regenerated in memory and compared character for character with the committed files. |
| Handoff rules | `handoffs/*.json` | Parameter mappings and downstream columns are checked against the pinned schemas. Whether published files exist is checked when a chain runs. |

A pin changed without regenerating the files, or a hand edit to a generated file, makes
`make check` fail.

---

## Running maintenance locally

The bots change only generated paths and pins, never the hand-written guides, so a new pin leaves
[`docs/validation.md`](validation.md) and the [generation matrix](preflight.md#support-matrix) as
they were on their stated dates. `skill.md` is always current.

You can run the same tasks from the repository root with Python 3.11+ and initialised submodules;
install the test dependencies with `pip install -e ".[dev,yaml]"`. Change the generators rather
than the generated files, then run `make build` and `make check`. `make update` fetches tags,
changes submodule checkouts and stages the new pins; review them before committing. It does not run
the CI acceptance gate. [CONTRIBUTING.md](../CONTRIBUTING.md#make-targets) lists every target.
