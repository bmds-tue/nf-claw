# Boundary validation and evidence integrity audit, 2026-10-30

Audited base: `9cec9c81c33b88d61e34e997a0e22d86ea6ded90` on `main`.
This follow-up reviews the contracts remaining after the earlier
[repository audits](2026-10-30-exhaustive-audit.md), rather than treating their findings as new.
The scope includes runner input validation, MCP transport and jobs, chaining and handoffs,
provenance/replay/verification, scientific assessment, maintenance gates, generated context,
and the static website. All 95 pinned upstream checkouts were initialized for validation;
no upstream sources or generated catalog/skill/reference files were changed.

## Findings and corrections

| ID | Finding and reproduction | Correction |
|---|---|---|
| D01 | MCP tool and prompt calls silently converted supplied `null`, `false`, `0`, empty string and empty list arguments to `{}`. | Only omitted arguments default to an object; supplied nonobjects receive `-32602` without dispatch. |
| D02 | MCP accepted boolean, object and list request IDs, and malformed messages without IDs could receive no error. | Invalid IDs receive `-32600` with a null ID; malformed id-less messages receive errors while real notifications remain unanswered. |
| D03 | A `ping` with extra tool-shaped parameters could enter the long-wait pool and stall behind eight pending tools. | Only `tools/call` participates in tool-wait routing; the real-pipe responsiveness regression exercises the saturated pool. |
| D04 | Python's JSON parser accepted `NaN` and infinities, and MCP echoed them as request IDs in invalid JSON responses. | Transport parsing rejects nonfinite JSON constants; direct handling refuses nonfinite IDs. Finite exact Decimal IDs remain supported. |
| D05 | Empty, unsupported-version and malformed environment objects could compare `identical` or produce attribute/type errors. Missing task, image, plugin and engine observations could be mistaken for agreement. | Supplied structures and counters are validated; absent immutable identities produce `unverified`. Valid legacy optional fields remain optional, and known mismatches remain distinguishable from missing observations. |
| D06 | `verify --strict` treated existing unreadable/nonobject environment records like absent legacy records, bypassing environment checks. A damaged consumed image could also be hidden by a missing counterpart. | Existing damaged evidence is reported `unverified`, including broken links, invalid encoding and unusable consumed image identities. Strict verification fails; default structural comparison still reports its scope. Genuinely absent legacy records with usable remaining evidence retain compatibility. |
| D07 | Standalone replay could traceback while reading corrupt environment evidence. | Replay writes and reports an `unverified` comparison. Its existing exit policy remains: undecidable evidence is reported, while established differences fail. Use `verify --require-environment` for completeness. |
| D08 | Two original image aliases resolving to digest A could both match one replay A, hiding another replay image B. | Image coverage is checked in both directions; alias overlap cannot hide an additional distinct image. |
| D09 | Chain `nxf_env` values such as `1`, `[1]`, `false` or empty strings could crash or silently become defaults. Falsy engine versions were silently discarded. | Chain and stage options require the documented environment object and validate every non-null engine version before preparation. Null options preserve their defaults. |
| D10 | Numeric/list/boolean memory and time limits could raise tracebacks; the resource parser accepted boolean/fractional CPU values. Empty config paths resolved to the current directory. | Resource values are type-checked with actionable parameter errors, CPU limits require positive integers, and config entries must be nonblank paths. CLI tests prove invalid chain options leave the output directory untouched. |

Each code defect has behavioral regressions observed failing before its correction. An independent
read-only review identified additional damaged-evidence, process-counter and nonfinite-ID cases;
those were reproduced and corrected in the review fix pass. Native replay tests now require
`unverified` with the containerless explanation when no executable/container identity is available,
while retaining successful replay and output checks.

## Verification

The [machine-readable verification record](evidence/2026-10-30-boundary-integrity.json) includes
source-file hashes, commands and the JUnit digest. Runtime: macOS arm64, Python 3.13.5,
Node 24.19.0; native Nextflow fixtures use 25.10.4 and 26.04.0.

| Gate | Final result |
|---|---|
| Full pytest suite, all extras and pinned sources available | **3,673 passed, 3 skipped**, zero failures/errors; 3,676 collected, 1,137.11 seconds. |
| Skip-policy check on the JUnit report | Passed: two Linux-only process tests and the declared obsolete rnasplice source fixture. |
| Native execution integration | All 55 Nextflow integration cases, 20 Git-path identity cases and 2 timeout integration cases passed within the full suite. |
| Pinned context drift | Passed with all 95 pinned source trees initialized; no generated context changes. |
| Ruff, compilation and diff whitespace | Passed. |
| Website dependency audit | Zero reported vulnerabilities. |
| Website typecheck and static production export | Passed; the exported llms.txt matches the repository copy. |
| Website operational/accessibility browser tests | **155 passed** after the documentation changes. |

The initial focused suites and failing regressions are supporting evidence; the final full-suite
result above is authoritative for the combined code. The independent review's four findings were
addressed with regression failures and passing verification; no actionable review finding remains.

The initial environment was missing Nextflow and browser binaries, and its system Node executable
could not load a Homebrew library. The audit installed the repository's checksum-verified Nextflow
launcher into its isolated virtual environment, used the app's bundled Node runtime, and installed
the matching Playwright Chromium. The initial incomplete-checkout run had 3,219 passes, 302 skips,
and one failure due to missing Nextflow; that specific test passed after setup. It is not the final
validation result.

## Feature gaps and limits

The earlier audit already records optional product work: DAG chains, additional handoff rules,
chain-wide replay packages, CLI job management, custom source registration, offline bundles,
distribution beyond editable checkouts, browser run configuration, and skill export. These need
product requirements; this PR does not invent their execution or scientific contracts. The current
linear-chain, MCP-job and editable-install workflows remain supported.

Scientific output contracts cover two pinned demos. Extending them to the remaining pipelines
requires explicit sample/output expectations and scientific reference data; parser success or a
passing wrapper suite cannot supply those. Native executable attestation and comprehensive
remote-input capture likewise require additional evidence collection. Ordinary environment
comparison keeps its existing process-inventory scope; `--require-environment` is the stronger gate.

This local Docker daemon was unavailable, so this audit does not claim a fresh containerized
execution of all 95 workflows, scheduler cleanup validation, a multi-OS/Python CI matrix, or
biological correctness. Previous audit evidence is linked for context, not represented as rerun
here. The PR runs the repository's configured CI gates; their results are reported separately.
