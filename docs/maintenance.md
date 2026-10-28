# Automatic-publication evidence policy

Daily release updates and weekly discovery prepare one candidate commit before final validation.
Only generated regular context/catalog files, canonical source registrations and pinned gitlinks
may change. Unsupported deletions, type changes, executable documents, symlinks and redirected
repositories are refused. A private index preserves unrelated staging and build output.

---

### Navigation

[Overview](#overview) • [Gating Criteria](#publication-gating-criteria) • [Trusted-Base Publisher](#fresh-trusted-base-publisher) • [Verification Boundaries](#verification-boundaries)

---

## Overview

The candidate Git bundle and metadata are uploaded as one immutable artifact. Consumers receive
its producing artifact ID and exact base/candidate SHAs, including on failed-job reruns. Every
consumer verifies the candidate's single parent, changed paths, modes and gitlink inventory before
checking out source or initializing submodules. Artifact IDs refer to the current workflow run;
see GitHub's [artifact-ID download contract](https://github.com/actions/download-artifact/tree/018cc2cf5baa6db3ef3c5f8a56943fffe632ef53#download-artifacts-by-id).

## Publication gating criteria

Publication requires all of these checks on that same candidate:

- All ten Ubuntu/macOS Python 3.11–3.15 lanes run the complete suite with initialized pinned
  sources, Nextflow, Node/site dependencies, YAML and declared scientific adapters. macOS also
  provisions GNU checksum/timeout tools before Nextflow setup. macOS 3.15
  retains the documented H5AD exception while h5py has no matching wheel. Known obsolete audited
  revision tests and the two Linux-only process tests on macOS may skip. Other missing-dependency
  or source skips fail the evidence gate. Reports with fewer than 3,000 executed cases are refused;
  this is a partial-report guard, while the workflow's unfiltered pytest command defines scope.
- Website dependency audit, parser tests without skips, typecheck, build and Chromium browser
  checks; actual Nextflow integration checks; Ruff; and generated-source drift.
- For every changed pipeline pin, a fresh bundled analysis on Linux amd64/Docker. Each run has a
  30-minute execution budget and ceilings of 2 CPUs, 6 GB memory and 30 minutes per task. It must
  record a successful manifest at the expected pin, unchanged discovered dependencies, no stub
  profiles/configs or completion caveats, and exactly one trace with real completed tasks. Empty
  traces, cached tasks, nonzero exits, failures, duplicate IDs and incomplete rows are refused.

Preview remains an early compatibility filter. Discovery may remove additions that fail that
filter before freezing the candidate. A frozen candidate whose real analysis needs unavailable
GPU hardware, credentials, references, images or greater resources does not publish. Its evidence
remains available for manual investigation; a bounded-host failure is not proof that a release is
scientifically invalid. Metadata-only candidates require the complete matrix/site/integration/drift
checks and skip native execution only when the verified changed-gitlink inventory is empty.

## Fresh trusted-base publisher

The publisher runs in a fresh job from the trusted base, with no candidate or upstream code
execution. It alone has write permissions. It independently parses every lane's raw pytest report
and each changed pipeline's raw manifest/trace, checks their candidate/pin identities and hashes,
and requires the actual upstream job results. Invalid or missing raw evidence cannot be replaced
by a successful job label. All candidate, report and diagnostic artifacts have 90-day retention.
Successful artifacts are immutable; failed diagnostics have separate names. A failed-job rerun
can reuse the original candidate and completed lanes. To rerun a previously successful producer,
rerun the complete maintenance workflow to prepare a fresh candidate.

After verification, the publisher pushes the exact candidate to a temporary branch and reports
only the checks that ran. Main updates use an explicit expected-old-commit lease. The candidate's
verified single parent makes an accepted update a fast-forward; a concurrent main change causes
deferral, including when another actor has already put the candidate on main. An up-to-date Git
response is not recorded as publication by this job. When main already equals the fully validated
candidate, the publisher retries all required follow-up workflow dispatches without another main
update. This recovers a prior publication whose deployment/test dispatch failed. The publisher never rebases or creates a
post-validation commit. Successful publication dispatches tests, smoke checks, CodeQL and Pages;
network, permission, ruleset or dispatch errors remain visible failures.

## Verification boundaries

These gates establish tested wrapper behavior and actual bundled-task execution. They do not
prove continuous filesystem immutability, honesty of arbitrary upstream executable code,
complete biological branch coverage, or scientific accuracy. Format-aware output contracts and
known-answer controls retain their separate scope. GitHub-hosted matrix execution is only proven
by the resulting workflow evidence; Linux server tests of this policy do not establish macOS runs.
