# End-to-End Validation

Every pinned pipeline in this library was run end to end through `nfclaw`. nfclaw's own features were
tested on the same host: replay, verification, resume, chains, sample-sheet generation, stop handling,
versions and status reporting. This page records how the runs were done, what passed, and what each
result does and does not show.

---

### Navigation

[Environment](#environment) • [Method](#method) • [Pipelines](#pipelines) • [nfclaw features](#nfclaw-features) • [Chains](#chains) • [Defects found and fixed](#defects-found-and-fixed) • [Test suites and CI](#test-suites-and-ci) • [Limits](#limits)

---

## Environment

| | |
|---|---|
| Host | de.NBI cloud VM, Linux amd64, 28 CPUs, 62 GB RAM, IPv6-only network (DNS64/NAT64) |
| Containers | Docker 29.1.3 (`-profile docker`) |
| Java | OpenJDK 17.0.20 |
| Nextflow | each release's documented engine (`--nxf-ver` from its `skill.md`), 21.10.3 to 26.04.1 |
| Dates | 2026-10-14 to 2026-10-15 |

## Method

Each pipeline ran its bundled `test` profile with `nfclaw run <name> --demo`. The engine was pinned to
the version its `skill.md` names, and provenance was written as usual. A run counted only when
`nfclaw status` reported `success`. Its last execution trace was then checked for failed or ignored
tasks, and its completion caveats were read.

Some bundled tests could not run as shipped. For each one, the cause was found first: an upstream
defect, test data that changed after the release, or a property of this host. The run was then repeated
with the smallest documented change. The table lists every such change, and
[known-issues](known-issues.md) explains it. This host is IPv6-only, so the later part of the sweep used
the documented host-network config (`--config host-net.config`). That came after containers on the
default bridge failed to reach IPv4-only servers.

A resumed run (`--resume`) continued an attempt that had stopped. The sweep's disk guard stopped some
attempts; others stopped on a failure the table explains. The trace of a resumed run counts both cached
and newly completed tasks.

## Pipelines

90 of the 91 pinned pipelines completed end to end. seqsubmit could not: its test queries ENA with a
Webin account. "Attempts" counts every launch, including runs the sweep stopped and resumed. The notes
give the reason for each extra attempt and every setting beyond `--demo`. "Host network" means the
documented [host-network config](known-issues.md#docker-bridge-network-has-no-dns-ipv6-only-host). Three
releases needed more than one run each: marsseq (a reference build, then the analysis on those
references), oncoanalyser (references prepared as upstream's CI prepares them) and rnafusion (the test
analysis on upstream's hosted references, and STAR-Fusion checked on its tutorial data).

Two runs were also checked against independent expectations. oncoanalyser's outputs matched every path
and checksum in the release's own nf-test snapshot. STAR-Fusion reproduced the fusions and breakpoints
that its tutorial documents for the tutorial reads.

| Pipeline | Version | Nextflow | Outcome | Tasks in the last trace | Attempts | Notes |
|---|---|---|---|---|---|---|
| airrflow | 5.1.2 | 26.04.1 | success | 129 cached + 41 completed | 2 | stopped by the sweep's disk guard, then resumed |
| ampliseq | 3.0.0 | 26.04.0 | success | 130 completed | 1 |  |
| atacseq | 2.1.2 | 23.04.0 | success | 265 completed | 1 |  |
| bacass | 2.6.1 | 25.04.0 | success | 17 completed | 1 |  |
| bactmap | 1.0.0 | 24.10.5 | success | 47 completed | 2 | pinned test-data snapshot and module options ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)); Nextflow 24.10.5 instead of the declared 21.04.0 ([Java 17](known-issues.md#an-engine-older-than-21100-fails-on-java-17-unsupported-class-file-major-version-61)) |
| bamtofastq | 2.2.1 | 25.10.4 | success | 32 completed | 2 | `--fasta` for the reference the test omits ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) |
| callingcards | 1.0.0 | 23.04.0 | success | 122 completed | 1 |  |
| chipseq | 2.1.0 | 23.04.0 | success | 215 completed | 1 |  |
| circdna | 1.1.0 | 23.04.0 | success | 89 completed | 1 |  |
| coproid | 2.0.1 | 25.04.0 | success | 33 cached + 14 completed | 3 | host network and an FTP relay ([IPv6 host](known-issues.md#python-tools-cannot-download-ftp-urls-ipv6-only-host)) |
| createpanelrefs | 1.0.0 | 26.04.0 | success | 2 completed | 1 |  |
| createtaxdb | 3.1.0 | 25.10.4 | success | 28 completed | 2 | sourmash off ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) |
| crisprseq | 2.3.0 | 24.04.2 | success | 44 completed | 1 |  |
| cutandrun | 3.2.2 | 23.04.0 | success, with caveats | 133 completed + 2 failed | 1 | success with caveats: 2 Preseq tasks failed and were ignored by the pipeline |
| datasync | 1.0.2 | 25.10.4 | success | 7 completed | 1 |  |
| demo | 1.2.0 | 25.10.4 | success | 8 completed | 1 |  |
| demultiplex | 1.8.0 | 25.10.4 | success | 7 completed | 1 |  |
| denovotranscript | 1.2.1 | 24.04.2 | success | 16 cached + 3 completed | 2 | stopped by the sweep's disk guard, then resumed |
| detaxizer | 1.3.0 | 25.04.8 | success | 54 completed | 1 |  |
| differentialabundance | 2.0.0 | 25.10.4 | success | 25 completed | 1 |  |
| drop | 1.0.0 | 25.10.0 | success | 33 cached + 101 completed | 2 | stopped by the sweep's disk guard, then resumed |
| drugresponseeval | 1.3.0 | 26.04.0 | success | 3 cached + 29 completed | 2 | stopped by the sweep's disk guard, then resumed |
| epitopeprediction | 3.1.1 | 25.04.0 | success | 32 cached + 206 completed | 3 | stopped by the sweep's disk guard, then resumed; then a transient Ensembl BioMart reply failed a task, and `--resume` completed it ([run note](known-issues.md#pipeline-specific-run-notes)) |
| fastqrepair | 1.1.1 | 25.10.4 | success | 9 completed | 1 |  |
| fastquorum | 2.0.0 | 25.10.4 | success | 12 completed | 1 |  |
| fetchngs | 1.13.0 | 25.10.4 | success | 26 completed | 2 | the test accessions that have ENA FastQ files ([run note](known-issues.md#pipeline-specific-run-notes)) |
| funcprofiler | 1.0.0 | 25.10.4 | success | 13 completed | 1 |  |
| funcscan | 4.0.0 | 25.10.4 | success | 55 cached + 13 completed | 4 | stopped with the sweep to repair Docker, then stopped when the shared disk filled; deepARG's download stalled on the Docker bridge and completed with host networking ([IPv6 host](known-issues.md#docker-bridge-network-has-no-dns-ipv6-only-host)) |
| genomeassembler | 2.0.0 | 25.10.4 | success | 88 completed | 1 |  |
| genomeqc | 1.0.1 | 25.10.4 | success | 61 cached + 27 completed | 4 | host network for the Dfam download ([IPv6 host](known-issues.md#docker-bridge-network-has-no-dns-ipv6-only-host)); stopped by the sweep's disk guard, then resumed |
| hadge | 1.0.0 | 25.10.4 | success | 65 cached + 38 completed | 3 | host network; stopped by the sweep's disk guard, then resumed |
| hgtseq | 1.1.0 | 22.10.1 | success | 58 cached + 5 completed | 3 | pinned test-data snapshot ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)); stopped by the sweep's disk guard, then resumed |
| hic | 2.1.0 | 22.10.1 | success | 36 cached + 2 completed | 2 | host network; stopped by the sweep's disk guard, then resumed |
| hicar | 1.0.0 | 21.10.3 | success, with caveats | 33 cached + 61 completed + 1 failed | 2 | host network; stopped by the sweep's disk guard, then resumed; success with caveats: `CIRCOS_PREPARE` failed and was ignored by the pipeline |
| hlatyping | 2.2.0 | 25.04.2 | success | 7 completed | 1 | host network |
| isoseq | 3.0.1 | 25.10.4 | success | 45 completed | 1 | host network |
| longraredisease | 1.0.0 | 25.04.0 | success | 46 completed | 1 |  |
| lsmquant | 1.0.3 | 25.10.4 | success | 13 cached + 1 completed | 3 | host network; `--nuclei-quantification false`: the skipped step needs an NVIDIA GPU ([run note](known-issues.md#pipeline-specific-run-notes)); stopped by the sweep's disk guard, then resumed |
| mag | 5.5.0 | 26.04.0 | success, with caveats | 117 cached + 70 completed + 1 failed | 4 | a Docker image pull failed (`lease does not exist`) while the sweep pruned images, then stopped when the shared disk filled; BUSCO hung after finishing and was opted out by config ([IPv6 host](known-issues.md#busco-finishes-then-the-task-hangs-until-its-time-limit-ipv6-only-host)); success with caveats: MaxBin2 failed and was ignored by the pipeline |
| magmap | 1.3.0 | 26.04.0 | success | 59 completed | 1 | host network |
| marsseq | 1.0.3 | 23.04.0 | success | references: 9 completed + 1 retried; analysis: 34 completed | 3 | host network; the test needs prebuilt references: built with `--build-references true --velocity true`, then the analysis ran with `--genomes-base` on them ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)); STAR's first attempt reached the container memory limit and Nextflow's retry completed |
| mcmicro | 2.0.0 | 25.04.0 | success | 11 completed | 1 | host network |
| metaboigniter | 2.0.1 | 23.04.0 | success | 13 completed | 1 | host network |
| metapep | 1.0.0 | 24.04.2 | success | 16 cached + 11 completed | 2 | host network; stopped by the sweep's disk guard, then resumed |
| metatdenovo | 2.0.0 | 25.10.4 | success | 86 completed | 1 | host network |
| methylong | 2.0.0 | 25.04.0 | success | 25 completed | 1 | host network |
| methylseq | 4.2.0 | 25.04.0 | success | 36 completed | 1 |  |
| mhcquant | 3.3.0 | 25.10.4 | success | 21 completed | 1 | host network |
| molkart | 1.2.0 | 25.04.0 | success | 22 completed | 1 | host network |
| multiplesequencealign | 1.1.1 | 25.04.2 | success | 78 completed | 2 | host network; the release's `test_tiny` profile ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) |
| nanoseq | 3.1.0 | 22.10.1 | success | 26 completed | 1 |  |
| nanostring | 1.3.3 | 25.10.2 | success | 7 completed | 1 | host network |
| nascent | 2.3.0 | 24.04.2 | success | 13 cached + 136 completed | 2 | host network; a Docker image layer went missing (`parent snapshot … does not exist`) while the sweep pruned images, then resumed |
| oncoanalyser | 3.0.0 | 25.10.4 | success | 26 cached + 16 completed | 3 | host network; references extracted once and passed through upstream's `tests/cached_refs.config` ([run note](known-issues.md#pipeline-specific-run-notes)); stopped by the sweep's disk guard, then resumed; all 473 paths and 151 checksums of the release's nf-test snapshot matched |
| pacvar | 1.1.0 | 25.10.4 | success | 10 completed | 1 | host network |
| pairgenomealign | 3.0.4 | 26.04.0 | success | 20 completed | 1 | host network |
| pangenome | 1.1.3 | 24.04.2 | success | 22 completed | 1 | host network |
| pathogensurveillance | 1.1.0 | 25.04.6 | success | 20 cached + 7 completed | 7 | local ENA copies of the test reads, JVM IPv6 preference and a SPAdes quality-offset config ([run note](known-issues.md#pipeline-specific-run-notes), [IPv6 host](known-issues.md#java-tools-in-containers-prefer-ipv4-ipv6-only-host)) |
| phaseimpute | 1.1.0 | 25.04.0 | success | 40 completed | 1 | host network |
| phyloplace | 2.3.0 | 26.04.0 | success | 8 completed | 1 | host network |
| pixelator | 5.0.3 | 25.10.4 | success | 27 completed | 1 | host network |
| proteinannotator | 1.1.0 | 25.10.4 | success | 40 completed | 1 | host network |
| proteinfamilies | 2.6.0 | 26.04.0 | success | 89 cached + 1 completed | 2 | host network; `MULTIQC` ended once without an exit code (`process hasn't exited`), then resumed |
| proteinfold | 2.0.0 | 25.10.2 | success | 5 completed | 1 |  |
| rangeland | 1.0.0 | 24.04.2 | success | 280 completed | 1 | host network |
| raredisease | 3.1.2 | 25.10.4 | success | 876 completed | 3 | a Docker image pull failed (`lease does not exist`) while the sweep pruned images, then stopped when the shared disk filled; a fresh run completed |
| readsimulator | 1.0.1 | 23.04.0 | success | 1 completed | 1 | host network |
| reportho | 1.1.0 | 25.04.0 | success | 232 completed | 1 | host network |
| ribomsqc | v1.0.0 | 25.04.0 | success | 4 completed | 1 | host network |
| riboseq | 2.0.0 | 25.10.4 | success | 356 completed | 1 | host network |
| rnadnavar | 1.0.0 | 25.10.4 | success | 120 completed | 1 |  |
| rnafusion | 4.1.3 | 25.10.4 | success | 15 completed | 16 | host network; the `test` analysis on upstream's hosted GRCh38 references with Arriba, Salmon and fusion-report; STAR-Fusion and FusionInspector checked on the tutorial minigenome against its documented fusions ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) |
| rnaseq | 3.27.0 | 25.10.4 | success | 234 completed | 3 | stopped with the sweep to repair Docker, then stopped when the shared disk filled; a fresh run completed |
| rnasplice | 1.0.4 | 23.04.0 | success | 128 completed | 1 | host network |
| rnastructurome | 1.0.0 | 25.10.4 | success | 52 completed | 1 | host network |
| rnavar | 1.3.0 | 25.10.4 | success | 43 completed | 1 |  |
| sarek | 3.10.0 | 25.10.4 | success | 9 cached + 14 completed | 2 | a Docker image pull failed (`lease does not exist`) while the sweep pruned images, then resumed |
| scnanoseq | 1.3.0 | 25.04.2 | success | 85 completed | 1 | host network |
| scrnaseq | 4.2.0 | 25.10.4 | success | 19 completed | 1 |  |
| seqinspector | 1.1.2 | 25.10.4 | success | 48 completed | 1 | host network |
| seqsubmit | 1.0.0 | 25.10.4 | failed (exit status 1) |  | 1 | host network; needs an ENA Webin account ([run note](known-issues.md#pipeline-specific-run-notes)) |
| smrnaseq | 2.4.1 | 25.04.2 | success | 244 completed | 1 | host network |
| sopa | 1.0.1 | 25.10.4 | success | 9 completed | 1 | host network |
| spatialaxe | 1.0.1 | 25.04.0 | success | 10 completed | 1 | host network |
| taxprofiler | 2.0.1 | 25.10.4 | success | 179 completed | 1 |  |
| tumourevo | 1.0.0 | 25.10.4 | success | 65 cached + 1 completed | 2 | host network; `--sparsesignatures-k 2:3`, the value its test profile misnames ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) |
| variantbenchmarking | 1.5.0 | 25.04.0 | success | 73 completed | 1 |  |
| variantprioritization | 1.0.0 | 25.10.0 | success | 19 completed | 1 | host network |
| viralintegration | 0.1.1 | 23.04.0 | success | 45 completed | 1 | host network |
| viralmetagenome | 1.2.0 | 25.10.4 | success | 288 completed | 1 | host network |
| viralrecon | 3.0.0 | 25.04.0 | success | 200 completed | 1 |  |


## nfclaw features

These checks ran on the same host, apart from the pipeline sweep:

| Feature | What was run | Result |
|---|---|---|
| Replay | `provenance/commands.sh` of a `demo` run, run again into a fresh directory, then `nfclaw verify --against` the original | 42 files identical, 34 changed, 0 missing, 0 extra, 1 renamed (run metadata named by launch time). All FastQC outputs were byte-identical, and the MultiQC general statistics were equal. The changed files are MultiQC plots, logs and data files that embed timestamps, plus Nextflow's execution reports. `--strict` exits 1 on those changes, as documented |
| Replay of a stub run | proteinfold 2.0.0 `--demo` (its test profile sets `stubRun = true`) and its replay | Both reported success with a `stub run:` caveat. The replay carries the caveat in its header, and `nfclaw verify` passes |
| Known-answer cell | fastqrepair 1.1.1 on a paired fixture with a known repair; run, `--check`, replay and the replay's `--check` | All passed. The replay verified with 0 missing and 0 extra files |
| Other engines and revisions | `demo` 1.0.0 on Nextflow 23.04.0, and `demo` at `dev` | Both succeeded |
| Sample-sheet generation | `--input` as a directory, a quoted glob, and repeated `--input`; a data file without a mate | The sheets were generated and the runs succeeded. The orphan file was refused before launch |
| Parameters | a YAML `--params-file`; an unknown parameter; `--no-provenance` | The runs with a params file and without provenance succeeded. The unknown parameter was refused before launch, and no outdir was created |
| Stops | SIGTERM, SIGKILL of nfclaw, `--timeout 40`, a failing task, a second run into an outdir in use, a non-empty outdir without `--resume` | `nfclaw status` reported each outcome: `terminated by SIGTERM` (exit 143); `stopped without an outcome`, with no Nextflow process left behind; `timed out after 40 s`; `failed (exit status 1)`, quoting the task's `.command.err`; the second run refused with `another nfclaw run is active`; the non-empty outdir refused before launch |
| Resume after a stop | `--resume` after SIGTERM and after SIGKILL | Both resumed runs succeeded. Before the [fix](#defects-found-and-fixed), a run resumed after SIGTERM recomputed every task. After it, runs resumed after SIGTERM reused 7 cached tasks (remote inputs) and 5 (local inputs), and the dependency check reported their inputs unchanged |
| Preview | `nfclaw run <name> --demo --check` for all 91 pipelines | All 91 passed, and none wrote into `--outdir` |
| Engine acceptance | `scripts/nextflow_accept.sh` on demo, rnaseq, createpanelrefs, bactmap and marsseq | Each result matched the documented outcome |
| Library | `librarian.write_skill --all`, `librarian.write_catalog`, `librarian.check_drift`, `discover_pipelines --dry-run` | The generated files reproduced the committed ones and drift was zero |
| Read-only commands | `nfclaw list`, `nfclaw show`, `nfclaw versions` | The output was correct |

## Chains

Each chain ran with `nfclaw chain run` and ended with `nfclaw chain status`. Its lineage check verified
every handoff against the checksums the upstream stage recorded.

| Chain | Settings beyond the stages' `demo: true` | Lineage |
|---|---|---|
| createtaxdb → taxprofiler | sourmash off ([createtaxdb 3.1.0 sort race](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) | verified |
| rnaseq → differentialabundance | `deseq2_vst_nsub 50` for the small test matrix; resumed after an edit to the spec | verified |
| demultiplex → seqinspector | none | verified |
| bamtofastq → rnaseq | the bamtofastq test BAMs' chr22 reference (`--fasta`, `--gtf`), `min_trimmed_reads 1000`, `skip_dupradar`, `skip_deseq2_qc` | verified |
| detaxizer → taxprofiler | a restricted profiler set | verified |
| fetchngs → taxprofiler | the test accessions that have ENA FastQ files (except `SRR9984183`), `perform_shortread_redundancyestimation false` | verified |

[chaining.md](chaining.md) and the chain notes in [known-issues](known-issues.md) explain these settings.

The createtaxdb stage's outputs were deleted after its lineage had verified, to free disk for the sweep. From then on, `nfclaw chain status` reported the chain's lineage as `BROKEN`. It named the missing checksum record, the missing Bracken database, and each database file taxprofiler had consumed. This is the behaviour the lineage check is designed to have.

## Defects found and fixed

These nfclaw changes came out of the validation. Each is covered by tests, and the runs that showed the
problem were repeated:

- **`--resume` after Ctrl-C or `kill` recomputed every task.** On a stop, nfclaw skipped the
  dependency-stability check that records which inputs a run may reuse, so the next `--resume` treated
  the whole cache as stale. The check now runs on a stop too, and a resumed run reuses the cache.
- **Stub-run test profiles reported an unqualified success.** proteinfold's `test` profile sets
  `stubRun = true`, so its demo computes nothing. `nfclaw run` now says so before launch, `nfclaw status`
  reports a `stub run:` caveat, and the run manifest, replay header and `skill.md` record it.
- **Nextflow engines older than 21.10.0 failed on Java 17.** They cannot compile a pipeline config there
  (`Unsupported class file major version 61`). nfclaw now refuses such an engine before launch, and
  `skill.md` recommends Nextflow 24.10.5 for the releases that declare one (bactmap).
- **A failed run's error was misquoted when the nf-co2footprint plugin relayed the console.** The plugin
  relays log records without line breaks, so `nfclaw status` quoted a stray `Tip:` line. It now splits
  those records and quotes Nextflow's error report.
- **"Stopped without an outcome" did not mention a full disk,** although a full disk stopped runs here.
  The message now names it among the causes.
- **`skill.md` did not say which Nextflow secrets a release reads.** It now lists them, and where they are
  read (seqsubmit, metapep, sarek, raredisease, rnaseq, pathogensurveillance).
- **A hidden directory beside the pipelines was taken for a pipeline.** A Nextflow launched from
  `pipelines/` leaves `pipelines/.nextflow/`; `nfclaw list` showed it, and `write_skill --all` crashed.
  Hidden entries are now skipped.
- **createtaxdb 3.1.0's sourmash sort race** is an upstream defect. nfclaw now warns about it before
  launch.

Upstream defects and host limits found along the way are documented in [known-issues](known-issues.md),
with the narrowest workaround that ran.

## Test suites and CI

- `pytest`: 2728 passed and 2 skipped on the Linux validation host. On macOS 2562 passed and 168 were skipped:
  167 need the pipeline submodules, which that checkout did not initialize, and one reads Linux's `/proc`.
- Website: `npm audit` found 0 vulnerabilities; type check and build passed.
- GitHub Actions on the pull request: every check passed.

## Limits

- A bundled test profile shows that a release runs end to end on small data. It does not show that the
  results are scientifically valid for real data. Where a stronger check was possible, it was done: the
  replay comparisons, the fastqrepair known-answer cell, oncoanalyser's snapshot and the STAR-Fusion tutorial.
- Every run used Docker on Linux amd64. Singularity, Conda, other executors and arm64 were not part of
  this sweep; known-issues records the arm64 MultiQC export failure.
- rnafusion's FusionCatcher step did not run: the release ships no small FusionCatcher reference. Its
  STAR-Fusion and FusionInspector steps ran on the STAR-Fusion tutorial's minigenome, not on GRCh38: their
  62 GB GRCh38 library did not fit the shared disk next to the other references.
- seqsubmit was not run to completion: its test queries ENA with a Webin account, which this validation
  did not have. The tasks before that query completed ([details](known-issues.md#pipeline-specific-run-notes)).
- The host's IPv6-only network shaped several runs: host networking, a local FTP relay, and local copies
  of ENA reads. A host with IPv4 connectivity should need none of these.
