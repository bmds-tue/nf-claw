# Pasted review follow-up — 30 October 2026

The supplied review examined the local working tree based on `f33b36a`. GitHub main had
advanced to `bcc40d5` before this work started. The original working tree and an initial
implementation are preserved locally at `8f70360` on `br/review-hardening`. This change
is based on current main and retains its newer pipeline releases, source corrections,
environment records, scientific contracts, MCP support and website checks.

## Corrective findings

| Finding | Disposition against current main |
| --- | --- |
| R1 | Already addressed: the current Next.js 16 lockfile passes the dependency audit. |
| R2 | Fixed: refuse nonempty incomplete version caches and directory aliases; never recursively delete local work or force checkout over it. |
| R3 | Already addressed: acceptance retains source checkouts and removes only its private preview scratch. |
| R4 | Current main redacts chain/stage records, uses private permissions and requires redacted secrets again on resume. This change also redacts the option serialization used for fingerprints. |
| R5 | Already addressed: the complete input inventory, including standalone selections and link metadata, gates resume archiving. |
| R6 | Already addressed: strict verification uses the full byte/link predicate. |
| R7 | Fixed: replay removes unrecorded `NXF_*` variables, restores recorded values and requires externally supplied redacted secrets. Destination validation and replay log inspection use that same effective environment. |
| R8 | Fixed: drift checks source identity and tracked modifications before rendering; Git failures do not establish a clean pin. |
| R9 | Current main has a shared opt-in deadline across planning, locks, probes, handoffs, hashing, execution and finalization, with dedicated deadline/setup/shutdown regression suites. Retain those safeguards. |
| R10 | Fixed: share the Git mutation lock, verify ownership and clean affected paths, supervise noninteractive bounded Git operations, and restore checkout, gitlink and generated context on failure or interruption. Other pipelines are still attempted after an ordinary failure. |
| R11 | Already addressed: maintenance publication depends on the reusable full test matrix and real-task gate; the shared test workflow includes website audit, parsing, type, build and browser checks. |
| R12 | Already addressed: concrete examples use shell-quoted equals-form values; unresolved expressions are noncopyable templates. |
| R13 | Already addressed: parameter search exposes a retry action and distinguishes unavailable results. |
| R14 | Fixed: writers record an optional seek cursor for the latest attempt; status reads its bounded header/tail. Legacy or invalid cursors fall back to backward block search. Cursors are private, optional and replaceable without changing the log's authority. |
| R15 | Fixed: reject malformed/falsy option types before parsing units or environment assignments, with normal field-specific errors. JSON and YAML regressions cover chain and stage levels through the CLI. |
| R16 | Fixed: sanitize both `--nxf-env KEY=VALUE` and `--nxf-env=KEY=VALUE` in refused commands and their diagnostics using the existing provenance secret policy. |
| R17 | Fixed: production source records carry an identity version; missing identity/checksum fields fail closed. Historical source checksum/archive evidence also requires complete identity metadata. |
| R18 | Already addressed: both false and throwing copy fallbacks report failure; success is shown only when copying succeeds. |

Real browser checks also reproduced a separate keyboard issue: skills arrows followed the
selected row even when another row had focus. They now navigate from the focused row, with
desktop and phone-width regression checks.

## Enhancement scope and limits

G1–G6 in the supplied report explicitly describe capabilities and optional extensions rather
than additional reproduced defects. Current main already provides stronger source/config/image
recording, scientific assessment contracts, supervised MCP replays, machine-readable status,
version reporting and browser/accessibility checks. Its documented limits remain applicable:
standalone replay does not create another full replay bundle; transitive/undeclared dependencies
are not universally frozen; biological correctness is established only by the relevant fixture
and scientific oracle; editable checkout installation and linear chains remain the supported
design. A portable whole-chain bundle, arbitrary DAG scheduling and unaudited new handoffs are
outside this corrective change. See [replay](../replay.md), [chaining](../chaining.md),
[preflight](../preflight.md) and [known issues](../known-issues.md).

The original review's pinned-upstream limitations must be checked against current releases and
the existing source-correction/evidence records. Do not restore old pins or remove validated
FastQRepair, HGTseq, Bactmap, Createtaxdb or Funcscan controls to reproduce an obsolete symptom.

## Validation

Focused local regression checks, lint, the 95-pipeline drift gate, the website dependency audit
and production build pass. The existing 155-check browser/accessibility suite passes locally;
two focused-row navigation cases are added. Complete local and isolated `denbi_instance` test
results are recorded after final validation. The server checkout and logs are under
`/mnt/volume/nfclaw-review-hardening-20261030.65E7ia/`; earlier `repo/` logs concern the old
review snapshot, while `current/` and `current-*` records concern the current-main candidate.
