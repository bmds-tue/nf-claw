The repository already implements execution, validation, replay, provenance, verification, linear chains, version selection, MCP jobs, automatic maintenance, and the website. The remaining work is mainly **correctness, stronger guarantees, incomplete pipeline coverage, and interface details**.

The audit covered **95 pipelines and 19 handoffs** at commit `a1ff7fb`. Below are all **88 tracked items**, grouped compactly. Optional extensions are separate from necessary fixes.

**1. Confirmed defects — 19**

The five highest-priority fixes:

| ID | Problem | Required change |
|---|---|---|
| B01 | Replay can inherit `NXF_LOG_FILE` pointing at an input and overwrite it **before** detecting damage. Confirmed with real Nextflow. | Validate effective log/work/cache destinations before launching, including symlink and hard-link aliases. |
| B02 | MCP changes precise numeric parameters: large decimals round, tiny values can become zero. | Preserve exact numbers through JSON decoding, flags and inline chain specifications. |
| B03 | Chain records contain unredacted tokens/password-bearing environment values. | Apply consistent secret redaction, restrict permissions and require secrets to be supplied again for resume. |
| B04 | Preview cleanup uses forced submodule deinitialization and deletes pre-existing untracked files. | Preserve existing checkouts; clean only disposable directories created by that invocation. |
| B13 | Website pages omit critical operating guidance, including ProteinFold’s warning that its demo produces placeholders. | Display authoritative input, reference, secrets, engine, resource and demo-caveat instructions beside relevant commands. |

Other confirmed fixes:

| ID | Problem → required change |
|---|---|
| B05 | A failed samplesheet regeneration can make chain resume overlook newly added samples → treat unverifiable changed input as a refusal. |
| B06 | Optional handoffs silently discard ambiguous matches, malformed tables and rejected values → omit only genuinely absent optional data. |
| B07 | A crash during job submission can leave a running MCP job uncancellable → recover supervisor identity from durable records. |
| B08 | Old job IDs display a newer retry’s status/caveats → bind each job to its own launch and outcome. |
| B09 | Eight long-poll requests exhaust MCP workers and block ping/status/cancellation → reserve control capacity or make waits nonblocking. |
| B10 | Preflight rejects valid Java selected through `JAVA_HOME`/`NXF_JAVA_HOME` when PATH lacks Java → check the executable Nextflow actually selects. |
| B11 | Explicitly selecting an already-present pinned release can fail offline → recognize the verified local pin before requesting tags. |
| B12 | One malformed job record breaks global listing and unrelated submissions → validate records and isolate damaged entries. |
| B14 | Copied parameter snippets split strings containing spaces or leading dashes; unresolved expressions can reach the shell → quote concrete values and clearly mark placeholders. |
| B15 | Parameter search stays unavailable after its first network failure → provide retry/recovery without requiring reload. |
| B16 | Bacmodel’s example-file link resolves to a missing portal asset → resolve relative links against the pinned source. |
| B17 | Documentation starts at opacity zero and remains invisible without JavaScript → render core content visibly before animation/hydration. |
| B18 | Mobile-menu keyboard focus escapes into covered page content → contain focus, make the background inert and restore focus on close. |
| B19 | Website documentation claims Releases API functionality that is absent; “live” activity is a build snapshot → correct the claims and show an update timestamp. |

**2. Missing or partial capabilities — 24**

These are documented limitations or incomplete guarantees, rather than 24 additional undisclosed bugs.

| ID | What still needs adding or clarifying |
|---|---|
| G01 | Report which preflight checks ran, were deferred, or are unsupported—especially conditional/config/profile/remote-input checks. |
| G02 | Complete or explicitly document the supported schema subset: nested JSON/YAML, alternatives, uniqueness and cross-column rules differ. |
| G03 | Check expected versus processed samples and required outputs; exit zero currently cannot detect every silent omission. |
| G04 | Add scientific, format-aware comparisons for counts, variants, alignments and assemblies, with justified tolerances. |
| G05 | Offer a stronger verification mode that requires complete environment evidence instead of accepting missing/unverified observations. |
| G06 | Capture transitive dependencies: included configs, implicit references/indexes, plugins, Conda environments and task-managed downloads. |
| G07 | Distinguish hashes of bytes actually consumed from remote files fetched again afterward; current refetches are limited to 100 MiB. |
| G08 | Rehash the **extracted replay source** after execution, as already done for checkout-based source. |
| G09 | Define source integrity beyond tracked bytes: executable modes, link identity and runtime-significant untracked files. |
| G10 | Clarify that before/after snapshots do not prove continuous input immutability; stronger guarantees need immutable/read-only staging. |
| G11 | Let MCP accept structured parameter arrays/objects directly; currently they require a pre-existing params file. |
| G12 | Add supervised replay execution through MCP; currently clients need a separate shell. |
| G13 | Provide bounded samplesheet/log/result previews or artifact-reading resources through MCP. |
| G14 | Store validation evidence as machine-readable, commit-bound records: date, profile, engine, platform, caveats and evidence links. |
| G15 | Decide whether automatic release publication must execute actual tasks; current gates primarily use previews and wrapper checks. |
| G16 | Broaden real platform/executor coverage beyond Linux amd64/Docker; Apptainer has demo coverage, Podman mainly tests. |
| G17 | Align Python support claims with testing: declared `>=3.11`, CI currently 3.11–3.13. Decide whether the broader matrix must pass before automated publication. |
| G18 | Preserve scientific evidence beyond the current 14-day CI artifact retention. |
| G19 | Add scientific output contracts: actual matrices/BAM/VCF/FASTA/H5AD outputs, formats, coordinates and conditional branches. Catalog outputs are currently generic. |
| G20 | Correct “stray files are refused”: some unmatched files are deliberately ignored with warnings and records. |
| G21 | Publish the generation support matrix: remote inventories, mixed layouts, unfamiliar naming and some schemas need manual sheets; Zstd read-name inspection is absent; pairing inspects the first read. |
| G22 | Explain cancellation/recovery limits for detached containers, scheduler jobs and host crashes; add executor-aware reconciliation if required. |
| G23 | Automate browser, copy-command, retry, accessibility, no-JavaScript and exported-link regression checks. |
| G24 | Make institutional-config lookups respect the active budget and supervise helpers; the documented separate lookup can currently exceed a shorter requested timeout. |

Samplesheet generation currently supports **71 schemas directly**, **3 with explicit column-group selection**, while **12 require manual input** and **9 have no samplesheet schema**.

**3. Pipeline-specific work — 30 tracked items, consolidated below**

Several entries concern different branches or guarantees of the same pipeline.

| Pipeline / IDs | Remaining work and existing coverage |
|---|---|
| **bamtofastq — U01** | Bare demo lacks its required reference. Supply the matched chr22 reference or adopt an upstream fix. Reference-supplied execution and read-conservation checks already passed. |
| **createtaxdb — U02** | Sourmash mutates a shared genome list, creating races/order instability. Successful validation disabled it; adopt and validate a released fix. |
| **hgtseq — U03** | Moving demo data now uses columns intended for newer code. Pin compatible historical data/GFF. The wrapper’s corrected input contract already works. |
| **funcscan — U04** | DRAMP downloading fails on NaN sequence fields. Fix the downloader or supply a cleaned database; APD is unaffected. |
| **taxprofiler — U05** | Empty MetaPhlAn/other zero-hit outputs can break downstream steps or MultiQC. Restricted configurations work, but do not establish all-profiler zero-hit support. |
| **bactmap — U06** | Demo reference/data mismatch, overwritten module defaults and preview completion hang remain. A historical matched-data configuration completed 47 tasks. |
| **createpanelrefs / proteinfamilies / stableexpression — U07** | Default previews hang waiting for task-produced values. Actual analyses—including publishing—passed; reduced-output previews provide narrower evidence. |
| **multiplesequencealign — U08, U18** | Preview hangs; full test also needs unavailable `learnmsa:2.0.9`. Restore that image or validate an explicit replacement. Tiny FAMSA/MAFFT coverage passed 78 tasks. |
| **marsseq — U09** | Requires separate reference building with velocity enabled. Its `mm10` key actually selects **GRCm39/GENCODE M27**, not GRCm38. Address STAR memory headroom; reference build and analysis already passed after configuration/retry. |
| **rnafusion — U10, U20** | Fix placeholder/broken references, downloads, build resources and tutorial filtering assumptions. Full GRCh38 reference building remains unverified. Analysis tools ran using hosted references; supply complete indexes to prevent reference-directory writes. |
| **tumourevo — U11** | Correct `sparsesignatures_K` to `sparsesignatures_k`; intended `2:3` works where default `3:10` fails on tiny data. An undeclared CNAqc cross-reference also needs upstream clarification. |
| **cutandrun — U12, U21** | Retain an engine compatible with deprecated syntax and resolve two ignored Preseq failures. |
| **hicar / mag — U21** | Resolve ignored `CIRCOS_PREPARE` and MaxBin2 failures respectively; successful exit codes do not establish completion of these branches. |
| **demo on macOS arm64 — U13** | MultiQC can exit zero while all **36 plot exports fail** under emulation. Establish a compatible platform/image route and verify exports. |
| **sopa — U14** | Demo “data” points to mutable GitHub HTML. Replace it with immutable genuine data and rerun/replay. |
| **seqsubmit — U15** | Credentialed ENA queries/manifests/submission remain incomplete. Stubs covered 17 tasks, but the actual submission path was not exercised. Actual uploads need separate authorization. |
| **proteinfold — U16** | Run real prediction with appropriate databases/resources; bundled demo and replay are currently placeholders. |
| **lsmquant — U17** | Validate GPU nuclei quantification on NVIDIA hardware. The documented successful run explicitly skipped it. |
| **rnasplice — U19, U28** | Execute LeafCutter/RegTools separately. Characterize MISO/Salmon variation and downstream statistical changes; 111 selected snapshot checksums matched, but full scientific outputs did not. |
| **createpanelrefs — U22** | Add a nonempty antitarget fixture. Existing checks establish target metrics and empty antitarget inventory only. |
| **fastqrepair — U23** | Make the standard demo exercise paired repair; it currently drops that sample. Separate paired known-answer/run/replay controls already passed, and wrapper corrections exist. |
| **circdna — U24** | Its nondefault `test_AA` is stub-only; execute that branch. The default test did run. |
| **rnaseq — U25, U29** | Broaden scientific benchmarks beyond five samples/125 transcripts. Compare duplicate-tie choices, sixth-decimal StringTie changes and row ordering appropriately; recorded count tables matched byte-for-byte. |
| **ampliseq — U26** | Address or characterize unseeded DADA2 taxonomy tie-breaking and QIIME2 diversity/rarefaction randomness. R’s seed and single threading do not control all affected RNGs. |
| **genomeassembler — U27** | Investigate Flye replay differences: **4→3 contigs; 2,083,676→2,068,682 bp**, with graph/annotation changes excluded from selected snapshot checks. |
| **Several pipelines — U30** | Explicitly classify changing report paths, random library names, timestamps, missing exports and PID filenames in longraredisease, createtaxdb, hicar, nanoseq, nanostring, mag and rnafusion. Avoid broadly ignoring renamed files. |

Additional operational details remain important: BUSCO uploads can hang on affected networks; short cold-cache task limits can fail; some legacy releases require compatible engines; SRA/FTP access can need IPv6 workarounds; metapep needs `NCBI_EMAIL`; oncoanalyser needs substantial reference space; and tiny chain fixtures require deliberate reference/statistical settings. These are documented prerequisites, not missing implementations.

**4. Optional extensions — 15**

These require a product decision:

1. **O01:** DAG chains with parallel branches and joins.
2. **O02:** More scientifically validated handoff mappings beyond the existing 19.
3. **O03:** One portable replay package for an entire chain.
4. **O04:** CLI job management and stable JSON output.
5. **O05:** Explicit custom-source support for commits, branches and prereleases.
6. **O06:** Managed offline export/import bundles containing dependencies.
7. **O07:** Standalone distribution beyond editable checkout, plus release history/changelog.
8. **O08:** Browser run configuration, uploads, job dashboard and execution controls.
9. **O09:** Native Windows supervision/locking, or an explicit WSL policy.
10. **O10:** Export/install packaging for agents requiring `SKILL.md`.
11. **O11:** Mobile documentation table of contents.
12. **O12:** Full-text documentation search.
13. **O13:** Consistent canonical URLs and social metadata.
14. **O14:** Shareable filters, parameter groups, sort and comparison state.
15. **O15:** Correct the pagination claim or implement pagination when scale warrants it.

**What the checks established**

- **3,006 passing test cases after affected-case reruns; three explained skips.**
- All **95 pinned sources** and generated documentation/catalog/handoffs passed consistency checks.
- Lint, website typecheck and build passed; dependency audit found **zero vulnerabilities**.
- Website crawl checked **5,205 links**: one missing target, zero broken fragments.
- Historical validation records cover all 95 pins: **93 configured non-stub successes**, ProteinFold stubs, and incomplete credentialed seqsubmit coverage.
- No fresh biological execution sweep was performed. Already-fixed issues and obsolete-version faults were excluded from the required-fix list.

The implementation order should start with **B01–B04 and B13**, then job/chain correctness, remaining website defects, stronger verification guarantees, and pipeline-specific validation.