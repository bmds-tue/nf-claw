# Current-product follow-through audit, 2026-10-31

Baseline: `45df56a48441bb459221c9e4fea3c6fe133bd33f` (`main`, including merged #237, #238 and #246).
Scope confirmed by the user: fix and validate the current product; proposed new products are not
required repairs. Docker work is excluded. This checklist was written before implementation.

The initial audit verified 14 new defects: **2 high, 10 medium, 2 low**. No critical finding or
separate exploitable security vulnerability was established. The issues below concern current
promised behavior, with reproducible controls rather than conjectural product expansion.

## Prioritized checklist

Locations refer to the baseline above unless a later candidate is named. All 23 findings below
are resolved. Locations identify the original defects; focused regressions, combined review and the final complete test run verify their repairs. New findings were added before
implementation, including those discovered during independent review and the first combined run.

| ID | Severity | Location | Verified behavior and impact | Required change and regression | State |
|---|---|---|---|---|---|
| F01 | High | `runner/execution.py:168–188` | SIGTERM delivered while recording the newly created child PID escapes cleanup; a real sleeping child remains alive after the stopped call returns. Thread-start failures and metadata-helper spawn handovers expose the same ownership gap. | Own the child safely across spawn, PID logging, reader startup and wait; defer stop delivery until ownership is established; clean up partially started readers. Exercise real signals immediately after spawn and first/second reader startup failures, including descendants. | Resolved |
| F07 | High | `runner/chain.py:177,357` | Frozen-stage fingerprints use redacted serialization. Different effective sensitive environment values, including ordinary JVM options sharing a redacted string, have the same fingerprint and a completed stage is silently reused. | Separate private effective-value identity from public redaction using a versioned per-chain keyed digest. Keep keys private, compare before reuse, and explicitly refuse legacy sensitive records whose identity cannot be recovered. Cover identical/changed values, missing/wrong keys, secret exclusion and compatible legacy nonsensitive chains. | Resolved |
| F02 | Medium | `runner/orchestration.py:936` | A completion caveat emitted only to stderr appears in `status` but disappears from returned warnings and the manifest. | Extract caveats from both console tails with stable deduplication; preserve engine-log and stub evidence. Parameterize stdout/stderr controls and check warnings, callbacks, manifest and status agree. | Resolved |
| F03 | Medium | `runner/environment_record.py:305–348` | If the current engine log is missing, the first surviving rotation is treated as current; explicitly foreign-session runtime, build and plugins are retained before session rejection. | Identify current files by path, validate attribution before merging facts, retain only permitted same-session historical staging, and mark missing/unreadable/mismatched current evidence unknown. Cover missing current, foreign current, matching/foreign rotations and read failures. | Resolved |
| F04 | Medium | `runner/environment_record.py:417–418` | A continually progressing HTTP response defeats the recording deadline: a 0.06-second budget returned a successful digest after about 0.47 seconds. | Bound the entire open/redirect/read operation by the absolute deadline, stop its I/O on expiry, and retain an unresolved evidence gap. Use a slow local HTTP control and verify the helper/socket is cleaned up even across signal delivery during spawn; preserve normal digests. | Resolved |
| F05 | Medium | `runner/scientific_hts.py:205` | VCF QUAL values NaN and either infinity pass `assess`, contrary to the documented finite-number guarantee. Finite values and the missing marker are valid controls. | Reject present nonfinite QUAL with a contextual assessment error; retain missing QUAL. Cover all three nonfinite values, finite/missing values, and comparative assessment. | Resolved |
| F06 | Medium | `runner/handoff.py:803–809`; `runner/consumption.py` | Supported `path` and `file-path-pattern` upstream references remain relative, are resolved under the downstream caller's directory, and lose producer-consumption evidence. Actual wildcard members need separate handling. | Normalize every supported local format against the producer; verify exact historical files/pattern members and downstream consumption identity. Cover archives, directories, wildcard patterns, wrong-cwd lookalikes, changed/missing/extra members and unchanged lineage. | Resolved |
| F08 | Medium | `website/src/components/pipeline/pipeline-index.tsx:20–34` | Same-route footer navigation changes the URL but leaves query/domain/results unchanged; Back restores a URL while retaining the later input. | Subscribe to navigation/search changes and synchronize absent as well as present filters without overwriting a new URL. Browser-test footer navigation, controls/results, Back/Forward and base-path behavior. | Resolved |
| F09 | Medium | `website/src/lib/data/pipelines.ts:295–298` | The website drops generated Mandatory arguments guidance; scrnaseq's explicit warning about rejected defaults and its protocol table disappear beside the run command. | Render that existing guidance while preserving its distinction from schema-required fields. Verify the parsed data and built scrnaseq page retain the warning and protocol information. | Resolved |
| F10 | Medium | `librarian/check_drift.py:24–40,78–86` | First-match parsing accepts duplicate URL/path fields even when Git uses a different effective value. The independent maintenance publisher already rejects duplicates; no publication exploit is established. | Parse the registration structure strictly, rejecting duplicate/conflicting fields and malformed blocks; retain deterministic offline checking. Differential-test valid/duplicate/malformed fixtures against Git's effective values. | Resolved |
| F13 | Medium | `runner/mcp_server.py:215–216` | An escaped unpaired-surrogate string accepted in a request ID causes response encoding to raise in the worker; the request receives no answer while the following ping succeeds. | Make every protocol response UTF-8 encodable without losing request identity or Unicode text. Test malformed Unicode in IDs/error text and later valid requests through the real transport. | Resolved |
| F14 | Medium | `runner/jobs.py:129–134` | Deeply nested damaged persisted JSON raises `RecursionError`; one job record crashes `jobs list --json` instead of being isolated. | Treat decoder nesting failures as malformed durable records consistently across job/supervisor/frozen reports. Verify good jobs remain visible and status/cancel preserve their JSON error contract. | Resolved |
| F11 | Low | `website/src/components/ui/counter.tsx:12–33` | The static homepage visibly renders all four statistics as zero without JavaScript; correct values exist only in hidden accessibility text. | Server-render actual values and make count animation a post-hydration enhancement. Check visible source-derived values with JavaScript disabled and correct accessible/reduced-motion behavior. | Resolved |
| F12 | Low | `website/README.md:9` | The stack guide names Next.js 15, but the manifest, lockfile and build use 16.4.3. | Correct the framework version reference. Documentation-only review; no implementation-mirroring test. | Resolved |
| F15 | Low | `tests/test_audit_fixes.py:74` | The test named “launcher is not tracked” instead rejects any local launcher, including the explicitly supported Git-ignored `/nextflow` installation. A temporary ignored launcher reproduces the false failure. | Check Git tracking rather than file existence. Verify the guard with an ignored untracked launcher present and retain the ordinary clean-checkout control. | Resolved |
| F16 | Low | `docs/architecture.md:78`; `README.md:206`; `docs/compatibility.md:48` | Three phrases promise that checks never start Nextflow/processes, although supported preparation executes version/configuration probes. The actual guarantee is no pipeline/scientific tasks and no output writes. | Correct the overbroad phrases while preserving the accurate preflight/AGENTS contract. Existing configuration-probe tests establish behavior; validate the edited documentation in the site build. | Resolved |
| F17 | Low | `tests/test_mcp_server.py:93–101,250–262` | The request helper discards replies with another ID, so a forbidden cancelled-call reply arriving before a ping is silently hidden and the cancellation test falsely passes. A real-pipe injected-response control reproduced that false pass. | Preserve unmatched messages for the caller, test notification/reply retention, and rerun the forbidden-response injection to prove the cancellation test rejects it. | Resolved |
| F18 | Low | `docs/known-issues.md:612` | A release-scoped AmpliSeq 3.0.0 investigation calls its historical commit “the pinned” although the manifest/generated skill now pin 3.1.0. | Label the old commit as historical release evidence without expanding its scientific claims to the current pin. | Resolved |
| F19 | Low | `CONTRIBUTING.md:151–152` | Contributor guidance says every nested docs artifact becomes a website page, but the data loader enumerates only top-level Markdown guides. | State the actual nonrecursive page/a11y scope so contributors do not mistake archived audit/evidence artifacts for built pages. | Resolved |
| F20 | Medium | `runner/chain.py:427–431` | Independent review reproduced deeply nested chain state/spec JSON escaping the durable reader as `RecursionError`; `chain status --json` prints no envelope and a traceback, while ordinary malformed JSON correctly refuses. | Treat decoder nesting failures as malformed chain records. Cover normal/quick JSON status, resume and recorded-spec/private-identity readers, preserving existing data and versioned diagnostics. | Resolved |
| F21 | Low | `tests/test_orchestration.py:1923` | The non-stub-demo test rejects any warning containing the substring `stub`, including a legitimate missing-log diagnostic whose temporary directory contains the test name `non_stub`. The first combined run reproduced this false failure. | Assert the semantic completion-caveat warning category and recorded manifest caveats instead of unrelated path substrings; retain the positive stub-demo controls. | Resolved |
| F22 | Low | `tests/test_chain.py:1077–1104` (candidate `f2471da`) | The F20 regression assumes 10,000 nested JSON arrays always exceed the decoder limit. Python 3.14 and 3.15 accept them, so two status controls falsely reject the valid structured status response. | Test native nested input under each interpreter and deterministically exercise a decoder `RecursionError`; preserve the JSON/error contract and unchanged recorded bytes without assuming an interpreter-specific limit. | Resolved |
| F23 | Low | `tests/test_runtime_followthrough.py:96–123` (candidate `f2471da`) | The partial-reader control captures every `Popen`, including Linux libc-discovery probes. Linux libc discovery invokes `ldconfig` with no stderr pipe, so two controls fail while checking a helper as though it were the analysis child. | Track the unique launched analysis command, preserve all child/thread/pipe cleanup assertions, and inject an unrelated real discovery probe to verify portability without masking an analysis leak. | Resolved |

The initial 14-item audit was committed before implementation. Supplemental test/guide review
added F15–F19, independent final review added F20, and the first combined run added F21 before
its repair. Cross-platform CI then exposed F22–F23, both recorded before repair. The current
checklist contains **23 items: 2 high, 11 medium, 10 low**.

## Coverage and verification policy

The baseline has **832 tracked entries**: 367 owned text files, 192 generated context files,
170 historical evidence files, 8 binary artifacts and 95 vendor gitlinks. The accompanying
[coverage inventory](evidence/2026-10-31-followthrough-coverage.json) records paths, baseline blob
identities, text sizes and review methods. It distinguishes manual source review, test execution,
structural artifact checks and deterministic regeneration; it does not pretend that generated
hashes, image pixels or every upstream implementation received a human line-by-line review.

- Read-only domain reviews read the owned runtime, data/schema/scientific/chain, website,
  librarian, workflow and script sources. CLI, jobs and MCP were reviewed separately. Relevant
  tests and documentation were cross-checked against current behavior and prior fixed findings.
- All 95 initialized vendor gitlinks are checked against the manifest and generated context.
  Vendored nf-core code remains unmodified. Upstream scientific correctness and the internal
  implementation of every external tool are outside a wrapper-repository repair claim.
- Generated skills/references/catalogs are checked by byte-for-byte regeneration. Historical
  audit evidence is retained as dated evidence, not rewritten as a claim about this baseline.
  All 112 historical JSON artifacts parsed successfully; binary/lockfile methods are explicit.
- Tests run with the checked-out dependency set, bundled Node 24 and the project's Python extras.
  The complete baseline Python suite passed **3,896 tests with two expected skips**. The newly
  exposed controls were absent from its existing assertions. Domain controls also passed (runtime
  919 with two Linux-only skips; data 920). Final candidate results are recorded below.
- Baseline site build passed. npm's installed/lockfile audit returned zero advisories; Python's
  installed dependency audit returned zero advisories across 40 public dependencies. The local
  nfclaw package is not on PyPI and was inspected as source instead. Advisory scans do not prove
  absence of undisclosed vulnerabilities.
- No Docker setup, Docker task execution or Docker-specific changes are part of this work.
  Existing automatically triggered GitHub checks may include their established lanes; their
  results will be recorded distinctly from local execution.

## Implementation and merge gates

Fix every open finding with focused regressions (RED then GREEN), review the combined diff, add
new verified review findings here, and run the complete Python suite, lint, context drift, website
build/typecheck, browser/accessibility and native integration gates. Keep any genuine suspected
security vulnerability private under `SECURITY.md`; none is established by this checklist.

Target: `main`. Its active ruleset requires `pytest (ubuntu-latest, 3.11)`, `website`,
`nextflow-integration` and `drift`. Review all checks, not only the required subset. Commit and push
through a pull request; merge only with the required checks green and no known important unresolved
finding. Never use an administrative bypass, force push or force merge. If the target advances,
reconcile it and verify the resulting candidate before merging.

## Completed verification

All **23 findings are resolved**: 2 high, 11 medium and 10 low. The implementation preserves the
current product and leaves proposed roadmap products outside this repair. There are no known
unresolved critical or important findings within the audited repository-owned scope.

| Gate | Verified result |
|---|---|
| Complete final Python suite | **4,001 passed, 2 skipped**, 330.87 seconds; Python 3.13.5, four workers |
| Website typecheck and static build | Passed on Node 24.19.0 |
| Complete browser/accessibility suite | **162 passed**, including URL history, mandatory guidance and no-JavaScript counters |
| Additional base-path controls | Three audit browser controls passed both at `/` and `/nf-claw` |
| Ruff, whitespace and deterministic context drift | Passed; all 95 initialized pins and generated artifacts agree |
| Dependency consistency/advisories | Dependency consistency passed; npm audit: zero advisories; pip-audit: zero advisories across 40 public dependencies |
| Copied standalone compatibility | Recorder HTTP fetch and guard hashing passed with isolated Python 3.9.6; this is not a full application test matrix |
| Independent final review | One important finding, F20, added before repair; its eight decoder controls and 161 related tests passed after correction |

The first combined candidate run exposed two failures (3,985 passed, 2 failed, 2 skipped).
F03's missing-session diagnostic order was restored, and F21 narrowed an overbroad warning
assertion. Both failures reproduced before repair; 131 related tests passed afterward, followed
by the complete green run above. No failing assertion or required check was disabled.

Cross-platform CI of implementation commit `f2471da` exposed two test-portability assumptions,
not further production defects. F22 assumed a native decoder nesting limit that changed in Python
3.14/3.15; F23 confused Linux's libc-discovery helper with the launched analysis child. Both were
reproduced locally before repair. All 165 related chain tests passed on Python 3.13 and 3.14;
removing the production recursion fix made the four deterministic decoder controls fail. Runtime
controls passed 73 tests with two Linux-only skips, including an injected unrelated discovery
subprocess. Cleanup assertions still require the actual analysis child, its readers and pipes to
be stopped/closed. Production cleanup/error guarantees remain asserted; no gate was disabled.
A complete intermediate run passed 3,999 tests with two skips after F22, and the final complete run above includes both corrections.

The two local skips are Linux process-state and parent-death-signal controls in
`tests/test_execution.py`; Ubuntu CI runs those platform-specific controls. Website source did
not change after its successful full run. The final Python run covered the final source and test
bytes recorded in the [verification record](evidence/2026-10-31-followthrough-verification.json).
Only audit metadata was finalized afterward.

### Regression and review traceability

- F01–F04: `tests/test_runtime_followthrough.py` covers real spawn-time signals, partial reader
  startup, descendant teardown, both output streams, log attribution, absolute HTTP deadlines,
  helper reaping and private-stdin URL transfer. Existing execution/environment/orchestration
  tests also pass. F03 preserves the primary no-session diagnostic for a launch that never began.
- F05: `tests/test_scientific_hts.py` covers missing, finite and all three nonfinite VCF QUAL
  values in single and comparative assessment.
- F06: `tests/test_handoff_consumption.py` covers producer-relative paths and wildcard patterns,
  wrong working directories and changed/missing/extra consumed members.
- F07: `tests/test_chain_environment_identity.py` covers sensitive effective-value changes,
  inherited values, private key creation/permissions/damage, legacy compatibility and check-only
  behavior. Public records do not contain effective secrets or the private key.
- F08, F09 and F11: `website/tests/audit-regressions.spec.ts` exercises navigation/history,
  generated mandatory guidance and visible homepage statistics without JavaScript.
- F10: `tests/test_check_drift.py` covers duplicate, conflicting and malformed registrations
  against Git's interpretation, while real context drift still passes.
- F13, F14 and F20: real MCP transport and durable job/chain tests cover unpaired surrogates
  and deeply nested malformed JSON while preserving valid replies and existing recorded data.
- F15 and F17: isolated Git controls prove ignored launchers are permitted but tracked launchers
  rejected; the MCP helper retains unmatched replies, and injected forbidden cancellation output
  now makes the cancellation assertion fail as intended.
- F12, F16, F18 and F19: reviewed documentation corrections match the current manifest, probe
  behavior, historical release evidence and nonrecursive website guide loader.
- F21: the non-stub test checks the completion-caveat category and manifest evidence; existing
  positive stub controls remain in place.
- F22: real nested JSON input remains covered, with assertions matching each interpreter's
  native parsing capability; four controlled decoder failures guarantee F20's error path is
  tested on every supported version.
- F23: the partial-reader test tracks its unique analysis command and includes a real unrelated
  discovery probe with no stderr pipe, preserving all process/thread/pipe cleanup requirements.

An independent reviewer inspected the combined production/test/documentation diff, all three
new test files and adjacent callers, and verified baseline inventory identities. Its sole important
finding F20 was repaired with demonstrated regressions. The coordinator reviewed the small final
F20, F03 and F21 changes plus the F22/F23 test-portability corrections, and verified the complete
candidate. No Docker or vendored pipeline source was modified. Historical evidence remains historical; neither passing tests nor advisory scans
establish the scientific correctness of every external pipeline/tool or absence of unknown bugs.

## Integration record

The checklist was committed as `2db34dc966a99668b73fb2983247f517209c1fda` before fixes.
[Pull request #247](https://github.com/bmds-tue/nf-claw/pull/247) carries the completed repairs,
final review and checks. Its GitHub merge record is authoritative for the resulting merge commit
and final check URLs. Merge is permitted only after the current candidate's required and other
applicable checks pass, under the existing `main` protections; no administrative bypass is used.
