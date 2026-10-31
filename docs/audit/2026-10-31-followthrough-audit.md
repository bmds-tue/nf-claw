# Current-product follow-through audit, 2026-10-31

Baseline: `45df56a48441bb459221c9e4fea3c6fe133bd33f` (`main`, including merged #237, #238 and #246).
Scope confirmed by the user: fix and validate the current product; proposed new products are not
required repairs. Docker work is excluded. This checklist was written before implementation.

The initial audit verified 14 new defects: **2 high, 10 medium, 2 low**. No critical finding or
separate exploitable security vulnerability was established. The issues below concern current
promised behavior, with reproducible controls rather than conjectural product expansion.

## Prioritized checklist

Locations refer to the baseline above. Each item remains open until its regression, implementation
and relevant verification pass. Later audit/review findings will be added before they are fixed.

| ID | Severity | Location | Verified behavior and impact | Required change and regression | State |
|---|---|---|---|---|---|
| F01 | High | `runner/execution.py:168–188` | SIGTERM delivered while recording the newly created child PID escapes cleanup; a real sleeping child remains alive after the stopped call returns. Thread-start failures expose the same ownership gap. | Own the child safely across spawn, PID logging, reader startup and wait; defer stop delivery until ownership is established; clean up partially started readers. Exercise real signals immediately after spawn and first/second reader startup failures, including descendants. | Open |
| F07 | High | `runner/chain.py:177,357` | Frozen-stage fingerprints use redacted serialization. Different effective sensitive environment values, including ordinary JVM options sharing a redacted string, have the same fingerprint and a completed stage is silently reused. | Separate private effective-value identity from public redaction using a versioned per-chain keyed digest. Keep keys private, compare before reuse, and explicitly refuse legacy sensitive records whose identity cannot be recovered. Cover identical/changed values, missing/wrong keys, secret exclusion and compatible legacy nonsensitive chains. | Open |
| F02 | Medium | `runner/orchestration.py:936` | A completion caveat emitted only to stderr appears in `status` but disappears from returned warnings and the manifest. | Extract caveats from both console tails with stable deduplication; preserve engine-log and stub evidence. Parameterize stdout/stderr controls and check warnings, callbacks, manifest and status agree. | Open |
| F03 | Medium | `runner/environment_record.py:305–348` | If the current engine log is missing, the first surviving rotation is treated as current; explicitly foreign-session runtime, build and plugins are retained before session rejection. | Identify current files by path, validate attribution before merging facts, retain only permitted same-session historical staging, and mark missing/unreadable/mismatched current evidence unknown. Cover missing current, foreign current, matching/foreign rotations and read failures. | Open |
| F04 | Medium | `runner/environment_record.py:417–418` | A continually progressing HTTP response defeats the recording deadline: a 0.06-second budget returned a successful digest after about 0.47 seconds. | Bound the entire open/redirect/read operation by the absolute deadline, stop its I/O on expiry, and retain an unresolved evidence gap. Use a slow local HTTP control and verify the helper/socket is cleaned up; preserve normal digests. | Open |
| F05 | Medium | `runner/scientific_hts.py:205` | VCF QUAL values NaN and either infinity pass `assess`, contrary to the documented finite-number guarantee. Finite values and the missing marker are valid controls. | Reject present nonfinite QUAL with a contextual assessment error; retain missing QUAL. Cover all three nonfinite values, finite/missing values, and comparative assessment. | Open |
| F06 | Medium | `runner/handoff.py:803–809`; `runner/consumption.py` | Supported `path` and `file-path-pattern` upstream references remain relative, are resolved under the downstream caller's directory, and lose producer-consumption evidence. Actual wildcard members need separate handling. | Normalize every supported local format against the producer; verify exact historical files/pattern members and downstream consumption identity. Cover archives, directories, wildcard patterns, wrong-cwd lookalikes, changed/missing/extra members and unchanged lineage. | Open |
| F08 | Medium | `website/src/components/pipeline/pipeline-index.tsx:20–34` | Same-route footer navigation changes the URL but leaves query/domain/results unchanged; Back restores a URL while retaining the later input. | Subscribe to navigation/search changes and synchronize absent as well as present filters without overwriting a new URL. Browser-test footer navigation, controls/results, Back/Forward and base-path behavior. | Open |
| F09 | Medium | `website/src/lib/data/pipelines.ts:295–298` | The website drops generated Mandatory arguments guidance; scrnaseq's explicit warning about rejected defaults and its protocol table disappear beside the run command. | Render that existing guidance while preserving its distinction from schema-required fields. Verify the parsed data and built scrnaseq page retain the warning and protocol information. | Open |
| F10 | Medium | `librarian/check_drift.py:24–40,78–86` | First-match parsing accepts duplicate URL/path fields even when Git uses a different effective value. The independent maintenance publisher already rejects duplicates; no publication exploit is established. | Parse the registration structure strictly, rejecting duplicate/conflicting fields and malformed blocks; retain deterministic offline checking. Differential-test valid/duplicate/malformed fixtures against Git's effective values. | Open |
| F13 | Medium | `runner/mcp_server.py:215–216` | An escaped unpaired-surrogate string accepted in a request ID causes response encoding to raise in the worker; the request receives no answer while the following ping succeeds. | Make every protocol response UTF-8 encodable without losing request identity or Unicode text. Test malformed Unicode in IDs/error text and later valid requests through the real transport. | Open |
| F14 | Medium | `runner/jobs.py:129–134` | Deeply nested damaged persisted JSON raises `RecursionError`; one job record crashes `jobs list --json` instead of being isolated. | Treat decoder nesting failures as malformed durable records consistently across job/supervisor/frozen reports. Verify good jobs remain visible and status/cancel preserve their JSON error contract. | Open |
| F11 | Low | `website/src/components/ui/counter.tsx:12–33` | The static homepage visibly renders all four statistics as zero without JavaScript; correct values exist only in hidden accessibility text. | Server-render actual values and make count animation a post-hydration enhancement. Check visible source-derived values with JavaScript disabled and correct accessible/reduced-motion behavior. | Open |
| F12 | Low | `website/README.md:9` | The stack guide names Next.js 15, but the manifest, lockfile and build use 16.4.3. | Correct the framework version reference. Documentation-only review; no implementation-mirroring test. | Open |

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
  The baseline full Python run is in progress; the newly exposed controls are absent from its
  existing assertions. Domain controls already passed (runtime 919 with two Linux-only skips;
  data 920). Final numbers and exact reports will replace this provisional evidence.
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

## Current disposition

Initial checklist published locally before production/test edits. All 14 findings remain open.
Implementation, final test evidence and merge status will be appended as the work proceeds.
