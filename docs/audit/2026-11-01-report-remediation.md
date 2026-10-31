# Remediation of the 31 October repository review

The supplied review identified five reproduced defects, eleven broader guarantee/coverage items,
fourteen pipeline-specific groups, and eight optional product areas. Work began from current main
`b9619ac21ca385a307b3da3758b0e1e4c03e69d1`, preserving the original review and its evidence.
The older checkout's missing merged work was brought in before making corrections.

This ledger distinguishes fixes from scientific evidence still needed. A passing software suite
does not close the remaining assay, executor or hardware coverage. Merge remains conditional on
the requested acceptance work; this document does not certify that every pipeline is scientifically
validated or that the optional roadmap has been implemented.

## Reproduced defects

| ID | Correction | Regression evidence |
|---|---|---|
| F01 | Shared CLI/MCP job views apply the provenance secret policy to commands and diagnostics. Raw command records, logs and snapshots are private. Redaction handles duplicate options, quoting, JSON escaping, multiline values and tail-window boundaries. | Submitted and polled jobs, check jobs, raw-file permissions, bounded-tail controls. |
| F02 | Foreground CLI calls have a separate supervisor; Linux adopts escaped helpers with a subreaper. Cancellation, EOF, timeout and parent death stop owned work. Uninspectable ancestry refuses foreground launch. Detached analysis jobs retain their separate lifecycle. | Real independently grouped/double-forked helpers; timeout/cancel/disconnect/success and killed-parent controls. Darwin ancestry tracking cannot certify an arbitrary unobserved double fork. |
| F03 | A child records its birth identity before exec. A surviving authenticated child remains running with `phase: orphaned`; recovery validates boot/namespace, owner and precise birth time. Linux uses pidfd for cancellation. Old records lacking identity remain unrecoverable automatically. | Kill only the supervisor, remove supervisor metadata, cancel the orphan; reject mismatched and unreadable identities. |
| F04 | Slow ordinary work, waits and immediate controls have separate capacity; work admission is bounded. Ping is handled directly. Deferred waits retain request cancellation context. | Saturate ordinary version/show/verify calls and long polls; verify ping/status/cancel response and overload refusal. |
| F05 | Listing retains the committed pin offline without adding an invented tag to the release-resolution inventory. Notes/evidence distinguish remote observations, cached tags and unverified pin fallback. | Tagless/uninitialized offline listing, v-prefix deduplication and observation-source controls. |

## Guarantee and coverage items

| ID | Disposition |
|---|---|
| G01 | Improved: flat JSON/YAML and CSV/TSV share supported required/scalar/relationship/uniqueness checks. Incomplete branch extraction cannot rule out an unrepresented valid alternative. General schema composition, nested constraints and arbitrary predicates remain with nf-schema; the preflight guide labels that boundary. |
| G02 | Open scientific work: 93 pins still lack independently reviewed assay contracts. Inventing expected results or tolerances would not establish scientific validity. |
| G03 | Open: CRAM/reference binding, additional H5AD components and inferred-result adapters need reviewed contracts and independent reference results. Existing adapters remain bounded as documented. |
| G04 | Open: comprehensive transitive dependency discovery/freezing is not implemented. Existing incomplete-environment refusal is retained; no stronger capture claim is added. |
| G05 | Open: validation-only remote sheets are not all consumed from a single authenticated staged copy. Exact corrected demos do not establish general remote-byte identity. |
| G06 | Open: ordinary source checks do not independently authenticate every mode, symlink and untracked/ignored runtime dependency. Corrected-copy guarantees do not strengthen historical ordinary bundles. |
| G07 | Open: before/after hashing does not prove continuous immutability. No such guarantee is claimed. |
| G08 | Fixed diagnostic defect: unreadable process identity reports unknown; unreadable container inventories report unconfirmed cleanup, including replay. Wider Podman/arm64/scheduler/cloud/GPU/crash assurance still requires those environments. |
| G09 | Improved tracking here: current acceptance evidence will be bound to the tested source. A uniform durable registry across all historical pins/platforms remains open. |
| G10 | Retained boundary: remote inventories, ambiguous/mixed layouts and Zstd first-read inspection need format-specific work. No inferred sample renaming or unsupported pairing is introduced. |
| G11 | Open optional extension: relocatable/offline whole-bundle export and repeat-replay do not follow from current guarded replay. External dependencies remain necessary. |

## Pipeline-specific acceptance still needed

| Group | Required evidence or prerequisite |
|---|---|
| taxprofiler | All-profiler zero-hit and downstream/MultiQC controls beyond restricted Kraken2/Kaiju routes. |
| funcscan/DRAMP | Missing-sequence exclusion/downloader controls, independent MMseqs2 indexing/validation, broader positive-hit controls. |
| createpanelrefs/proteinfamilies/stableexpression/multiplesequencealign | Task-dependent default-preview diagnosis; exact learnMSA image or independently validated replacement for the full MSA test. |
| marsseq | Reference-key meaning, separate build guidance, measured STAR headroom and count-accuracy truth controls. |
| rnafusion | Immutable working demo references, tutorial assumptions, and a complete GRCh38 build with sufficient storage. |
| cutandrun/hicar/mag | Reproduce and resolve the recorded ignored Preseq/CIRCOS_PREPARE/MaxBin2 failures with compatible engines. |
| sopa/macOS arm64 demo | Immutable real Sopa input plus replay; native/emulated image route and complete expected exports on arm64. |
| seqsubmit/proteinfold/lsmquant/circdna | Credentialed read/query validation, prediction databases/hardware, GPU nuclei quantification and the test_AA branch. Real ENA uploads still require separate explicit authorization. |
| rnasplice | LeafCutter/RegTools execution and statistical effects of MISO/Salmon variability. |
| genomeassembler | Independent explanation/control of Flye contig/base changes and graph/annotation effects. |
| ampliseq/rnaseq/bactmap | DADA2/QIIME2 variability, broader rnaseq truth fixtures, and Bactmap multicore/tree accuracy and support controls. |
| fastqrepair | Independently reordered/orphaned mate controls beyond matched pairs; preserve documented N-base normalization. |
| Tumourevo | CNAqc reference declaration and reviewed inferred-tree/signature/CNAqc expectations beyond existing count/VCF checks. |
| changing report names/exports | Per-format classifications for the seven named pipelines; no global filename/content ignore rule. |

## Optional areas, not closed by these corrections

The report explicitly classifies these as roadmap items: DAG composition/whole-chain replay;
additional CLI/MCP tools and artifact inspection; arbitrary source selection and standalone library
distribution; website execution; full-body search and broader URL state; heavyweight/manual
maintenance routes and scientific release gates; release/tag/publication decisions. Existing
features already merged on main are retained. No release or scientific coverage is inferred from
their presence.

## Acceptance state

- Local focused process/MCP/schema checks and repository drift checks have passed; denied local
  process-inspection runs are environment-limited and are not counted as passes.
- Initial server full software pass: 3,730 passed, 303 skipped (many source checkouts were absent).
  Exact clean sources for all 95 pins are now available for a final source-complete rerun.
- Real Nextflow tests and production website/browser checks are running separately. The initial
  website dependency symlink was outside Turbopack's workspace; an independent local dependency
  copy corrects that test setup.
- Server capacity at start: about 1.7 GB free on its data volume. Existing runs/evidence and shared
  engines were preserved. This cannot support the requested full reference/database/GPU sweep.
- Additional storage/hardware and independently reviewed truth data have been requested while
  code and software acceptance work continues. No real ENA submission, fresh 95-analysis sweep,
  or claim of complete scientific validation has been made.
