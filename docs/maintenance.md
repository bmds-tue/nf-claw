# Publication policy for the maintenance workflows

What the daily update and the weekly discovery must show before they change `main`. Both prepare one
candidate commit and hand it to the same gate and publisher (`maintenance-gate.yml`). A candidate
may change only generated files (skills, references, catalogs), the registrations of its pipelines
and their pinned gitlinks. Deletions, type changes, executable documents, symlinks and redirected
repositories are refused. The candidate is built in a private Git index, so unrelated staged
changes and build output are left alone.

---

## Navigation

[The candidate](#the-candidate) • [What must pass](#what-must-pass) • [The publisher](#the-publisher) • [What this does not show](#what-this-does-not-show)

---

## The candidate

The candidate commit is stored as a Git bundle, together with its metadata, in one immutable
artifact. Every job that uses it receives the artifact's ID and the exact base and candidate SHAs,
also when a failed job is rerun. Before it checks out source or initialises submodules, each job
verifies that the candidate has a single parent and the expected changed paths, file modes and
gitlinks. Artifact IDs belong to the workflow run that produced them; see GitHub's
[download-by-ID contract](https://github.com/actions/download-artifact/tree/9000827ccba6bdab643e8b6fd33ac0654aef8333#download-artifacts-by-id).

## What must pass

All of these must pass on the same candidate:

- All ten test lanes (Ubuntu and macOS, Python 3.11–3.15) run the complete suite with the pinned
  sources, Nextflow, the website dependencies, YAML support and the scientific format libraries.
  macOS lanes install GNU checksum and timeout tools before Nextflow. macOS with Python 3.15 skips
  the H5AD tests, as declared, while h5py has no wheel for it. Apart from that, only the tests of
  known obsolete audited revisions and the two Linux-only process tests on macOS may be skipped;
  any other skip for a missing dependency or source fails the gate. A report with fewer than 3,000
  executed tests is refused as incomplete; the workflow's unfiltered pytest command defines what
  the suite is.
- The website's dependency audit, its parser tests (no skips), typecheck, build and Chromium tests;
  the Nextflow integration tests; Ruff; and the drift gate.
- For every changed pin, a fresh run of the pipeline's bundled test on Linux amd64 with Docker. Each
  run gets 90 minutes and at most 2 CPUs, 6 GB of memory and 30 minutes per task. It must record a
  successful manifest at the expected pin, unchanged dependencies, no stub profiles or configs, no
  completion caveats, and exactly one trace with real completed tasks. Empty traces, cached tasks,
  non-zero exits, failures, duplicate task IDs and incomplete rows are refused.

The preview is an earlier, cheaper filter: discovery drops additions that fail it before freezing
the candidate. A frozen candidate whose real run needs a GPU, credentials, references, images or
more resources than the runner has is not published. Its evidence stays available for
investigation, and a failure on a small runner does not mean the release is scientifically wrong.

All of a day's bumps form one candidate, so a release that cannot pass holds back the others every
day until it does. To let the rest through, set that pipeline's policy in `sources.tsv` to
something other than `latest-release`, such as `hold`: the updater then leaves it at its current
pin and the next run publishes the others. Set `latest-release` again once the release can pass, or
adopt it on purpose with its own evidence. A candidate that changes metadata only still needs the
full matrix, website, integration and drift checks; it skips the real runs only when the verified
list of changed pins is empty.

## The publisher

The publisher runs in a fresh job started from the trusted base and never runs candidate or upstream
code. It is the only job with write permission. It parses every lane's raw pytest report and each
changed pipeline's raw manifest and trace itself, checks their candidate and pin identities and
hashes, and requires the actual results of the jobs before it. A green job label cannot stand in for
missing or invalid raw evidence. Candidate, report and diagnostic artifacts are kept for 90 days.
Successful artifacts are immutable, and failed diagnostics get separate names. Rerunning failed jobs
can reuse the original candidate and the lanes that completed; to rerun a producer that succeeded,
rerun the whole maintenance workflow so it prepares a fresh candidate.

After verification, the publisher pushes the candidate to a temporary branch and reports the checks
that ran. It updates `main` only if `main` is still at the expected commit. Because the candidate's
single parent is that commit, an accepted update is a fast-forward; if `main` changed, including
when someone else already put the candidate there, publication is deferred. An "up to date" reply
from Git is not counted as a publication by this job. When `main` already equals the fully validated
candidate, the publisher only retries the follow-up workflow dispatches, which recovers a
publication whose test or deployment dispatch failed. It never rebases or adds a commit after
validation. A successful publication starts the tests, smoke, CodeQL and Pages workflows; network,
permission, ruleset and dispatch errors are reported as failures.

## What this does not show

These gates show that the runner behaves as tested and that each changed pipeline's bundled test
really ran. They do not show that files stayed unchanged at every moment, that upstream code does
what it claims, that every scientific branch of a pipeline works, or that its results are correct.
Output contracts and known-answer controls are separate checks. GitHub-hosted runs are proven only
by their own workflow evidence: tests of this policy on a Linux server say nothing about the macOS
lanes.
