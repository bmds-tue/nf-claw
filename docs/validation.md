# End-to-End Validation

Every pipeline pinned at the time of the validation was attempted through `nfclaw`.
Of 91 bundled tests, 90 reached success, including proteinfold's stub-only test;
seqsubmit could not complete without ENA credentials. nfclaw's own features were
tested on the same host: replay, verification, resume, chains, sample-sheet generation, stop handling,
versions and status reporting. This page records how the runs were done, what passed, and what each
result does and does not show.

The versions and observations below describe the 2026-10-14 to 2026-10-15 validation,
not a fresh execution after every repository change. Releases bumped and pipelines added since then
that were run the same way are listed under [Releases bumped or added after the sweep](#releases-bumped-or-added-after-the-sweep);
the automated updater itself gates a release on its preview, tests, drift checks and one bundled analysis
on a hosted runner ([publication evidence policy](maintenance.md)).
For the current pin and its requirements, read `pipelines/<name>/skill.md`.

---

## Navigation

[Environment](#environment) • [Method](#method) • [Pipelines](#pipelines) • [Fresh single-attempt runs](#fresh-single-attempt-runs) • [Releases bumped or added after the sweep](#releases-bumped-or-added-after-the-sweep) • [nfclaw features](#nfclaw-features) • [Chains](#chains) • [Provenance bundles](#provenance-bundles) • [Defects found and fixed](#defects-found-and-fixed) • [Test suites and CI](#test-suites-and-ci) • [Limits](#limits)

---

## Environment

| Setting | Value |
|---|---|
| Host | de.NBI cloud VM, Linux amd64, 28 CPUs, 62 GB RAM, IPv6-only network (DNS64/NAT64) |
| Containers | Docker 29.1.3 (`-profile docker`) |
| Java | OpenJDK 17.0.20 |
| Nextflow | each release's documented engine (`--nxf-ver` from its `skill.md`), 21.10.3 to 26.04.1 |
| Dates | 2026-10-14 to 2026-10-16 |

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

90 of the 91 bundled tests reached success; proteinfold executed only stubs, not
protein prediction. seqsubmit could not complete: its test queries ENA with a
Webin account. "Attempts" counts every launch, including runs the sweep stopped and resumed. The notes
give the reason for each extra attempt and every setting beyond `--demo`. "Host network" means the
documented [host-network config](known-issues.md#docker-bridge-network-has-no-dns-ipv6-only-host). Three
releases needed more than one run each: marsseq (a reference build, then the analysis on those
references), oncoanalyser (references prepared as upstream's CI prepares them) and rnafusion (the test
analysis on upstream's hosted references, split over three runs that together cover every tool).

The 21 releases that passed only on a `--resume` here were also run again from scratch, each in one uninterrupted run; see
[Fresh single-attempt runs](#fresh-single-attempt-runs). Some runs were also checked against independent expectations. oncoanalyser's outputs matched every path
and checksum in the release's own nf-test snapshot. STAR-Fusion reproduced the fusions and breakpoints
that its tutorial documents for the tutorial reads. rnafusion's three fusion callers called 12 fusions in
common on the test reads; FusionCatcher called all 14 of Arriba's.

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
| epitopeprediction | 3.1.1 | 25.04.0 | success | 32 cached + 206 completed | 3 | stopped by the sweep's disk guard, then resumed; then a transient Ensembl BioMart reply failed a task, and `--resume` completed it ([run note](known-issues.md#pipeline-specific-run-notes)); now pinned at 3.2.0, validated [after the sweep](#releases-bumped-or-added-after-the-sweep) |
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
| mag | 5.5.0 | 26.04.0 | success, with caveats | 117 cached + 70 completed + 1 failed | 4 | a Docker image pull failed (`lease does not exist`) while the sweep pruned images, then stopped when the shared disk filled; BUSCO hung after finishing and was opted out by config ([known issue](known-issues.md#busco-finishes-then-the-task-hangs-until-its-time-limit)); success with caveats: MaxBin2 failed and was ignored by the pipeline |
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
| proteinfamilies | 2.6.0 | 26.04.0 | success | 89 cached + 1 completed | 2 | host network; `MULTIQC` ran past its 2-minute test limit once, which Nextflow 26.04.0 reports as `process hasn't exited` ([known issue](known-issues.md#a-run-aborts-with-process-hasnt-exited)), then resumed |
| proteinfold | 2.0.0 | 25.10.2 | success, with caveats | 5 stub tasks completed | 1 | `test` sets `stubRun = true`; placeholder outputs, no protein prediction ([run note](known-issues.md#pipeline-specific-run-notes)) |
| rangeland | 1.0.0 | 24.04.2 | success | 280 completed | 1 | host network |
| raredisease | 3.1.2 | 25.10.4 | success | 876 completed | 3 | a Docker image pull failed (`lease does not exist`) while the sweep pruned images, then stopped when the shared disk filled; a fresh run completed |
| readsimulator | 1.0.1 | 23.04.0 | success | 1 completed | 1 | host network |
| reportho | 1.1.0 | 25.04.0 | success | 232 completed | 1 | host network |
| ribomsqc | v1.0.0 | 25.04.0 | success | 4 completed | 1 | host network |
| riboseq | 2.0.0 | 25.10.4 | success | 356 completed | 1 | host network |
| rnadnavar | 1.0.0 | 25.10.4 | success | 120 completed | 1 |  |
| rnafusion | 4.1.3 | 25.10.4 | success | 15, 4 and 24 completed in three runs | 20 | host network; the `test` analysis on upstream's hosted GRCh38 references, in three runs that together ran every tool (Arriba, CTAT-Splicing, fastp, FusionCatcher, FusionInspector, fusion-report, Salmon, STAR-Fusion, StringTie); the three fusion callers agreed on 12 fusions; STAR-Fusion also reproduced its tutorial's documented fusions on the minigenome ([upstream](known-issues.md#upstream-pipeline-bugs-documented-not-patched)) |
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


## Fresh single-attempt runs

In the sweep above, 21 releases reached `success` only on a `--resume`. The sweep's disk guard, a shared-disk outage or a
transient failure had stopped an earlier attempt. Each of the 21 was run again from scratch into a new outdir, with the
same settings and no `--resume`, so that one uninterrupted run covers the whole test. All of them succeeded.
"Launches" counts the fresh launches it took. Extra launches were stopped by a full shared disk or by the guard, or
needed the change in the notes; each started over in a new outdir.

| Pipeline | Tasks in that run | Launches | Notes |
|---|---|---|---|
| airrflow | 170 completed | 1 |  |
| coproid | 47 completed | 1 |  |
| denovotranscript | 19 completed | 1 |  |
| drop | 134 completed | 1 |  |
| drugresponseeval | 34 completed | 1 |  |
| epitopeprediction (3.1.1) | 198 completed + 16 retried | 2 | 16 `EPYTOPE_VARIANT_PREDICTION` attempts hit BioMart's outage page and passed on retry ([run note](known-issues.md#pipeline-specific-run-notes)) |
| funcscan | 68 completed | 3 | the first launch died when the shared disk filled; the second was stopped by the disk guard |
| genomeqc | 87 completed | 4 | `--famdb-library` with a local Dfam partition. Of the earlier launches, one was stopped while the shared disk was full, one by the disk guard, and one failed when `www.dfam.org` did not resolve |
| hadge | 103 completed | 3 | the first launch died when the shared disk filled; the second was stopped by the disk guard |
| hgtseq | 63 completed | 1 |  |
| hic | 38 completed | 1 |  |
| hicar | 94 completed + 1 failed | 1 | success with caveats: `CIRCOS_PREPARE` failed and was ignored by the pipeline, as in the sweep |
| lsmquant | 14 completed | 1 |  |
| mag | 187 completed + 1 failed | 1 | success with caveats: MaxBin2 failed and was ignored by the pipeline, as in the sweep |
| metapep | 27 completed | 1 |  |
| nascent | 149 completed | 1 |  |
| oncoanalyser | 42 completed | 2 | the 42 tasks upstream expects with cached references; all 473 paths and 151 checksums of its nf-test snapshot matched; the first launch died when the shared disk filled |
| pathogensurveillance | 46 completed | 1 |  |
| proteinfamilies | 90 completed | 4 | container images pulled before the run ([known issue](known-issues.md#a-run-aborts-with-process-hasnt-exited)); earlier launches hit its 2-minute limits during image pulls, or the full disk |
| sarek | 23 completed | 1 |  |
| tumourevo | 66 completed | 1 |  |

Two of these needed a setting the first sweep had not:

- epitopeprediction: a retry for `EPYTOPE_VARIANT_PREDICTION`, whose BioMart lookups failed 16 times on Ensembl's
  HTTP-200 outage page ([run note](known-issues.md#pipeline-specific-run-notes)).
- genomeqc: its own `--famdb-library` offline option, once `www.dfam.org` stopped resolving on this host
  ([IPv6 host](known-issues.md#docker-bridge-network-has-no-dns-ipv6-only-host)).

proteinfamilies ran as shipped once its container images were present. Its 2–3 minute test limits include the image
pull ([known issue](known-issues.md#a-run-aborts-with-process-hasnt-exited)).

## Releases bumped or added after the sweep

Each release below was validated separately on the same host, in one uninterrupted `nfclaw run <name> --demo`
on the engine its `skill.md` names: before its pin was updated or its pipeline was added, or, for a release the
automated updater published itself (rnastructurome 1.1.0 and genomeassembler 2.0.1), right after. This execution evidence is additional to
the automated updater's gates.

| Pipeline | Version | Nextflow | Outcome | Tasks | Notes |
|---|---|---|---|---|---|
| epitopeprediction | 3.2.0 | 25.10.4 | success | 21 completed | 2026-10-16, default bridge network |
| magmap | 1.3.1 | 26.04.0 | success | 59 completed | 2026-10-22, bump from 1.3.0, host network |
| rnasplice | 2.0.0 | 26.04.0 | success | 139 completed | 2026-10-22, bump from 1.0.4, host network |
| bacmodel | 1.0.0 | 25.10.4 | success | 2 completed | 2026-10-22, added, host network |
| plasmodiumdrugres | 1.0.0 | 25.10.4 | success | 6 completed | 2026-10-22, added, host network |
| provenancereport | 1.0.0 | 25.10.4 | success | 5 completed | 2026-10-22, added, host network |
| rnastructurome | 1.1.0 | 25.10.4 | success | 52 completed | 2026-10-23, bump from 1.0.0 published by the updater, host network |
| genomeassembler | 2.0.1 | 25.10.4 | success | 88 completed | 2026-10-23, bump from 2.0.0 published by the updater, host network |
| stableexpression | 1.1.0 | 26.04.4 | success | 246 completed | 2026-10-25, added, host network |

epitopeprediction 3.2.0 replaced 3.1.1's epytope and Ensembl BioMart variant path with `bcftools`, Ensembl VEP and
pVACtools, and its test annotates with a bundled VEP cache subset, so the BioMart failures above no longer apply
([run note](known-issues.md#pipeline-specific-run-notes)). It ran twice, on the bump and again once the
[provenance bundles](#provenance-bundles) change had merged. Both runs matched the release's own `-profile test`
nf-test: 21 succeeded tasks, every software version, all 78 stable output paths, all 17 checksummed files, and the
missense, in-frame deletion and frameshift peptides its assertions require. The second run's bundle pinned all 17
containerized processes to the digests of their 9 images and recorded 4 remote inputs by SHA-256. Its replay from
`provenance/commands.sh` succeeded with an identical execution environment. `nfclaw verify` exited 0: 36 files
identical, 39 changed only in MultiQC and `pipeline_info` reports, 1 launch-time-named file paired, 0 missing and
0 extra. Every analytical output (`variant_peptides/`, `variant_fasta/`, `mhcnuggets/` and `predictions/`) was
byte-identical across both runs and the replay.

The five releases of 2026-10-22 were checked the same way: each run against its release's own `-profile test`
nf-test snapshot (`tests/default.nf.test.snap`), then a replay from `provenance/commands.sh` and `nfclaw verify`.
Every run reported every software version its snapshot records, produced every stable output path it lists,
and matched all of its checksummed files: 15 for magmap, 111 for rnasplice, 1 for bacmodel, 9 for
plasmodiumdrugres and the 7 of provenancereport's 8 that its `tests/.nftignore` does not exclude. Every containerized process was pinned to its image digest, and every replay succeeded with an
identical execution environment and again matched all of those checksums.

| Run | Images | Pinned / containerized processes | Remote inputs | `nfclaw verify` |
|---|---|---|---|---|
| magmap 1.3.1 | 16 | 29/29 | 11 | 84 identical, 53 changed |
| rnasplice 2.0.0 | 28 | 62/62 | 12 | 2700 identical, 1539 changed, 20 missing, 20 extra |
| bacmodel 1.0.0 | 2 | 2/2 | 2 | 15 identical, 5 changed |
| plasmodiumdrugres 1.0.0 | 3 | 6/6 | 4 | 11 identical, 4 changed |
| provenancereport 1.0.0 | 3 | 5/5 | 2 | 18 identical, 17 changed |
| rnastructurome 1.1.0 | 15 | 38/38 | 5 | 73 identical, 15 changed |
| genomeassembler 2.0.1 | 14 | 30/30 | 7 | 243 identical, 78 changed |
| stableexpression 1.1.0 | 13 | 31/31 | 1 | 45 identical, 5 changed |

- **magmap:** 48 of the changed files are MultiQC and `pipeline_info` reports, 2 are gzip files whose
  decompressed content is identical, and 3 are BBMap logs that differ only in their timings.
- **bacmodel and plasmodiumdrugres:** only reports changed, apart from bacmodel's Prokka log.
- **provenancereport:** besides reports, the files that changed are the ones its own `tests/.nftignore` marks as
  unstable: the published resolved `nextflow.config`, `artifacts.csv`, `notebook.csv`, `reports.csv` and
  `ro-crate-metadata.json`, which record the output path and launch time. The eighth snapshot checksum is that
  `nextflow.config`; it also differs under upstream's nf-test, whose two tests passed on the same host.
- **rnastructurome 1.1.0** (2026-10-23) was checked the same way. Its run and its replay matched all 56 checksummed
  files and every one of the 108 stable paths of its `-profile test` snapshot, and every software version but
  R2DT's, which upstream's test leaves out because R2DT runs only with containers. The 15 changed files are ones
  its `tests/.nftignore` marks as unstable: reports, FastQC archives, STAR logs and R2DT's log.
- **genomeassembler 2.0.1** (2026-10-23) was checked the same way. Its run and its replay matched all 113 checksummed
  files, all 427 stable paths and every software version of its `-profile test` snapshot, which also records the
  88 succeeded tasks. Of the 78 changed files, 25 are reports and metadata and 8 are gzip files whose decompressed
  content is identical. The other 45 are all files its `tests/.nftignore` excludes from that comparison: hifiasm's
  binary indexes and logs, LongStitch's scaffolds, Flye's logs, read-trimming and Hi-C logs and metrics, the
  genomeqc samplesheet (it records absolute output paths) and the `test_ont_flye` sample's assembly. Flye assembled
  that sample's ONT test reads into 4 contigs (2,083,676 bp) in the run and 3 (2,068,682 bp) in the replay, so its
  graph, assembly info and Liftoff annotation differ too.
- **stableexpression 1.1.0** (2026-10-25) was added by hand: the weekly discovery rejects it because its default
  preview never exits ([known issues](known-issues.md#upstream-pipeline-bugs-documented-not-patched)). Its run and
  its replay matched all 27 checksummed files and all 72 stable paths of its `-profile test` snapshot, and the
  known answers that test asserts: `reporting/all_genes_summary.csv` holds 27,849 genes in 35 columns, with the
  expected stability scores for `ENSRNA050004025`, `PRUPE_1G169400` and `PRUPE_1G195800`. The 5 changed files are
  the launch-time `pipeline_info` reports and the MultiQC report, which its `tests/.nftignore` excludes.
- **rnasplice:** as with 1.0.4, MISO names its logs by the clock (the 20 missing and 20 extra files, so `nfclaw verify`
  exits 1) and samples by MCMC, so 1,223 of the changed files are MISO's data. Salmon's multi-threaded
  quantification also differs slightly between runs (948 of 5,895 transcripts of ERR188383, by at most 4.4 of
  46,570 reads), in both its `salmon` and `star_salmon` routes, and so do the SUPPA, tximport, DEXSeq DTU and
  IsoformSwitchAnalyzeR results computed from it. The other changed files are reports, PDFs, FastQC archives and
  logs that embed dates or timings. The snapshot's 111 checksummed files, its stable outputs, were identical in
  both runs. 2.0.0's new LeafCutter and RegTools steps belong to upstream's separate `leafcutter` test, not to
  `-profile test`, and were not run.

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
Run again on 2026-10-29 with exactly these settings, bamtofastq → rnaseq failed in rnaseq's Salmon
pseudo-alignment: its test profile's prebuilt yeast index quantified the human reads. With
`skip_pseudo_alignment` added, as the chain notes now say, it completed with verified lineage
([deep audit](audit/2026-10-29-deep-audit.md), B09).

The createtaxdb stage's outputs were deleted after its lineage had verified, to free disk for the sweep. From then on, `nfclaw chain status` reported the chain's lineage as `BROKEN`. It named the missing checksum record, the missing Bracken database, and each database file taxprofiler had consumed. This is the behaviour the lineage check is designed to have.

## Provenance bundles

A second sweep on the same host (2026-10-15 to 2026-10-16) checked the bundle of every pipeline by
replaying it. Each pipeline ran with the settings the pipeline sweep needed. Its
`provenance/commands.sh` then replayed it into a fresh directory, and `nfclaw verify` compared the
replay's outputs with the original's.

Since this sweep, a bundle records the run's execution environment in `environment.json`:

- each process's container image, by registry digest and image ID;
- the Nextflow plugins and Java runtime;
- the SHA-256 of every remote file Nextflow staged.

For these Docker runs, `containers.config` pins eligible processes to their digests. The bundle
holds the pipeline source as an archive, and copies of the external configs. A replay records its own environment and compares it
with the recording (`environment_check.json`). Detected mismatches fail standalone replay;
`unverified` comparisons are reported without failing it. The successful comparisons in the
table below were recorded as `identical`, rather than merely passing with unverified entries.

92 runs of 91 pipelines were replayed. 90 replays reported an `identical` execution-environment comparison. 2,496 of the 2,496 containerized processes were pinned to the registry digest of the image they ran, no image was left without an identity, and 673 remote inputs were recorded by SHA-256. The replays that did not pass are explained below.

| Run | Nextflow | Run outcome | Images | Pinned / containerized processes | Remote inputs | Replay | Environment | `nfclaw verify` |
|---|---|---|---|---|---|---|---|---|
| airrflow | 26.04.1 | success | 10 | 38/38 | 23 | success | identical | 175 identical, 355 changed |
| ampliseq | 26.04.0 | success | 21 | 79/79 | 14 | success | identical | 1289 identical, 321 changed |
| atacseq | 23.04.0 | success | 26 | 75/75 | 11 | success | identical | 375 identical, 358 changed |
| bacass | 25.04.0 | success | 8 | 10/10 | 6 | success | identical | 785 identical, 370 changed |
| bactmap | 24.10.5 | success | 17 | 23/23 | 7 | success | identical | 40 identical, 73 changed |
| bamtofastq | 25.10.4 | success | 5 | 17/17 | 6 | success | identical | 23 identical, 15 changed |
| callingcards | 23.04.0 | success | 12 | 19/19 | 5 | success | identical | 273 identical, 180 changed |
| chipseq | 23.04.0 | success | 26 | 50/50 | 15 | success | identical | 288 identical, 363 changed |
| circdna | 23.04.0 | success | 15 | 31/31 | 8 | success | identical | 94 identical, 87 changed |
| coproid | 25.04.0 | success | 15 | 25/25 | 12 | success | identical | 194 identical, 168 changed |
| createpanelrefs | 26.04.0 | success | 2 | 2/2 | 3 | success | identical | 13 identical, 9 changed |
| createtaxdb | 25.10.4 | success | 16 | 22/22 | 16 | success | identical | 55 identical, 19 changed, 6 missing, 6 extra |
| crisprseq | 24.04.2 | success | 15 | 17/17 | 5 | success | identical | 107 identical, 84 changed |
| cutandrun | 23.04.0 | success, with caveats | 21 | 95/95 | 11 | success | identical | 160 identical, 116 changed |
| datasync | 25.10.4 | success | 2 | 4/4 | 4 | success | identical | 22 identical, 11 changed |
| demo | 25.10.4 | success | 4 | 4/4 | 5 | success | identical | 42 identical, 34 changed |
| demultiplex | 25.10.4 | success | 6 | 7/7 | 1 | success | identical | 95 identical, 81 changed |
| denovotranscript | 24.04.2 | success | 13 | 15/15 | 5 | success | identical | 115 identical, 2226 changed |
| detaxizer | 25.04.8 | success | 11 | 14/14 | 7 | success | identical | 36 identical, 35 changed |
| differentialabundance | 25.10.4 | success | 11 | 17/17 | 6 | success | identical | 66 identical, 14 changed |
| drop | 25.10.0 | success | 18 | 52/52 | 34 | success | identical | 234 identical, 82 changed |
| drugresponseeval | 26.04.0 | success | 2 | 16/16 | 3 | success | identical | 196 identical, 13 changed |
| epitopeprediction 3.1.1 (BioMart retry config) | 25.04.0 | success | 8 | 10/10 | 2 | success | identical | 74 identical, 85 changed |
| fastqrepair | 25.10.4 | success | 4 | 7/7 | 3 | success | identical | 33 identical, 38 changed |
| fastquorum | 25.10.4 | success | 7 | 12/12 | 3 | success | identical | 30 identical, 17 changed |
| fetchngs | 25.10.4 | success | 2 | 4/4 | 0 | success | identical | 44 identical, 6 changed |
| funcprofiler | 25.10.4 | success | 7 | 8/8 | 9 | success | identical | 39 identical, 10 changed |
| funcscan | 25.10.4 | success | 15 | 37/37 | 4 | success | identical | 84 identical, 30 changed |
| genomeassembler | 25.10.4 | success | 14 | 30/30 | 6 | success | identical | 232 identical, 89 changed |
| genomeqc | 25.10.4 | success | 0 | 0/0 | 9 | success | identical | 684 identical, 333 changed |
| hadge | 25.10.4 | success | 25 | 34/34 | 6 | success | identical | 461 identical, 58 changed |
| hgtseq | 22.10.1 | success | 13 | 27/27 | 10 | success | identical | 215 identical, 89 changed |
| hic | 22.10.1 | success | 14 | 26/26 | 3 | success | identical | 58 identical, 54 changed |
| hicar | 21.10.3 | success, with caveats | 33 | 73/73 | 9 | success | identical | 78 identical, 48 changed, 1 missing, 8 extra |
| hlatyping | 25.04.2 | success | 7 | 7/7 | 1 | success | identical | 48 identical, 38 changed |
| isoseq | 25.10.4 | success | 10 | 13/13 | 5 | success | identical | 166 identical, 76 changed, 6 missing, 1 extra |
| longraredisease | 25.04.0 | success | 22 | 46/46 | 6 | success | identical | 68 identical, 35 changed, 7 missing, 7 extra, 1 missing directories, 1 extra directories |
| lsmquant | 25.10.4 | success | 5 | 7/7 | 2 | success | identical | 223 identical, 33 changed |
| mag | 26.04.0 | success, with caveats | 25 | 41/41 | 7 | success | identical | 865 identical, 502 changed, 12 missing, 12 extra |
| magmap | 26.04.0 | success | 15 | 29/29 | 9 | success | identical | 84 identical, 53 changed |
| marsseq | 23.04.0 | success | 9 | 14/14 | 6 | success | identical | 75 identical, 67 changed |
| marsseq (reference build) | 23.04.0 | success | 7 | 9/9 | 0 | success | identical | 26 identical, 4 changed |
| mcmicro | 25.04.0 | success | 6 | 10/10 | 1 | success | identical | 18 identical, 13 changed |
| metaboigniter | 23.04.0 | success | 3 | 7/7 | 3 | success | identical | 20 identical, 21 changed |
| metapep | 24.04.2 | success | 9 | 18/18 | 4 | success | identical | 25 identical, 21 changed |
| metatdenovo | 25.10.4 | success | 24 | 41/41 | 13 | success | identical | 50 identical, 141 changed |
| methylong | 25.04.0 | success | 15 | 25/25 | 2 | success | identical | 22 identical, 29 changed |
| methylseq | 25.04.0 | success | 6 | 12/12 | 6 | success | identical | 126 identical, 90 changed |
| mhcquant | 25.10.4 | success | 6 | 13/13 | 4 | success | identical | 23 identical, 44 changed |
| molkart | 25.04.0 | success | 6 | 12/12 | 3 | success | identical | 28 identical, 14 changed |
| multiplesequencealign | 25.04.2 | success | 13 | 35/35 | 5 | success | identical | 43 identical, 23 changed |
| nanoseq | 22.10.1 | success | 10 | 16/16 | 3 | success | identical | 27 identical, 39 changed, 1 missing, 1 extra |
| nanostring | 25.10.2 | success | 4 | 5/5 | 5 | success | identical | 32 identical, 24 changed, 4 missing |
| nascent | 24.04.2 | success | 19 | 37/37 | 8 | success | identical | 227 identical, 120 changed |
| oncoanalyser | 25.10.4 | success | 28 | 38/38 | 6 | success | identical | 271 identical, 159 changed |
| pacvar | 25.10.4 | success | 5 | 10/10 | 4 | success | identical | 16 identical, 9 changed |
| pairgenomealign | 26.04.0 | success | 5 | 12/12 | 3 | success | identical | 37 identical, 19 changed |
| pangenome | 24.04.2 | success | 7 | 20/20 | 1 | success | identical | 11 identical, 58 changed |
| pathogensurveillance | 25.04.6 | success | 13 | 17/17 | 0 | success | identical | 758 identical, 146 changed |
| phaseimpute | 25.04.0 | success | 7 | 18/18 | 11 | success | identical | 14 identical, 54 changed |
| phyloplace | 26.04.0 | success | 5 | 8/8 | 4 | success | identical | 22 identical, 11 changed |
| pixelator | 25.10.4 | success | 3 | 12/12 | 7 | success | identical | 20 identical, 98 changed |
| proteinannotator | 25.10.4 | success | 8 | 18/18 | 3 | success | identical | 65 identical, 33 changed |
| proteinfamilies | 26.04.0 | success | 12 | 34/34 | 1 | success | identical | 68 identical, 33 changed |
| proteinfold | 25.10.2 | success, with caveats | 3 | 3/3 | 0 | success | identical | 16 identical, 4 changed |
| rangeland | 24.04.2 | success | 3 | 12/12 | 6 | success | identical | 1179 identical, 40 changed |
| raredisease | 25.10.4 | success | 43 | 186/186 | 38 | success | identical | 223 identical, 175 changed, 6 missing, 1 extra |
| readsimulator | 23.04.0 | success | 1 | 1/1 | 0 | success | identical | 5 identical, 7 changed |
| reportho | 25.04.0 | success | 12 | 35/35 | 0 | success | identical | 24 identical, 57 changed |
| ribomsqc | 25.04.0 | success | 3 | 4/4 | 2 | success | identical | 7 identical, 10 changed |
| riboseq | 25.10.4 | success | 25 | 50/50 | 22 | success | identical | 502 identical, 599 changed |
| rnadnavar | 25.10.4 | success | 17 | 34/34 | 9 | success | identical | 153 identical, 163 changed |
| rnafusion | 25.10.4 | success | 16 | 23/23 | 7 | success | identical | 190 identical, 115 changed, 1 missing, 1 extra |
| rnaseq | 25.10.4 | success | 26 | 65/65 | 19 | success | identical | 715 identical, 341 changed |
| rnasplice | 23.04.0 | success | 26 | 70/70 | 12 | success | identical | 2787 identical, 1555 changed, 30 missing, 30 extra |
| rnastructurome | 25.10.4 | success | 15 | 38/38 | 4 | success | identical | 70 identical, 18 changed |
| rnavar | 25.10.4 | success | 11 | 35/35 | 10 | success | identical | 49 identical, 51 changed |
| sarek | 25.10.4 | success | 12 | 21/21 | 10 | success | identical | 87 identical, 96 changed |
| scnanoseq | 25.04.2 | success | 18 | 46/46 | 4 | success | identical | 94 identical, 95 changed |
| scrnaseq | 25.10.4 | success | 7 | 8/8 | 9 | success | identical | 83 identical, 50 changed |
| seqinspector | 25.10.4 | success | 11 | 13/13 | 10 | success | identical | 555 identical, 523 changed |
| seqsubmit | 25.10.4 | failed (exit status 1) | 11 | 12/12 | 6 | failed (exit status 1) | — | 7 identical, 7 changed |
| smrnaseq | 25.04.2 | success | 16 | 41/41 | 13 | success | identical | 221 identical, 148 changed |
| sopa | 25.10.4 | success | 2 | 9/9 | 1 | failed after Nextflow succeeded (execution environment differs from the recording) | differs | — |
| spatialaxe | 25.04.0 | success | 5 | 10/10 | 1 | success | identical | 491 identical, 140 changed |
| taxprofiler | 25.10.4 | success | 27 | 51/51 | 24 | success | identical | 341 identical, 381 changed |
| tumourevo | 25.10.4 | success | 11 | 18/18 | 15 | success | identical | 131 identical, 85 changed |
| variantbenchmarking | 25.04.0 | success | 11 | 27/27 | 7 | success | identical | 48 identical, 32 changed |
| variantprioritization | 25.10.0 | success | 7 | 11/11 | 7 | success | identical | 476 identical, 32 changed |
| viralintegration | 23.04.0 | success | 9 | 23/23 | 9 | success | identical | 150 identical, 81 changed |
| viralmetagenome | 25.10.4 | success | 35 | 86/86 | 15 | success | identical | 396 identical, 179 changed |
| viralrecon | 25.04.0 | success | 32 | 80/80 | 9 | success | identical | 413 identical, 278 changed |

"Pinned / containerized processes" counts the processes `containers.config` pins to the digest of
the image they ran. Every replay ran those digests, not the tags. "Remote inputs" counts the remote
files Nextflow staged, recorded by SHA-256. `nfclaw verify` compares outputs by path. Its "changed"
files are reports, logs and plots that embed timestamps or paths. Notes on the remaining rows:

- **sopa**: the replay failed its environment check, correctly. The release's test samplesheet names a
  GitHub HTML page as the sample's data file, and the page's bytes change on every download
  ([known issue](known-issues.md#pipeline-specific-run-notes)).
- **seqsubmit**: needs an ENA Webin account. The run failed where its test queries ENA, and its replay
  failed the same way.
  On 2026-10-23 its bundled test also ran in stub mode (`--demo` with a `--config` setting
  `stubRun = true`, Nextflow 25.10.4), which needs no ENA access. All 17 tasks completed, among them every
  step up to and including the manifests (`CREATE_MANIFESTS`). `nfclaw status` reported the success with its
  `stub run:` caveat. The replay ran with an identical execution environment (13 processes, 12 images), and
  `nfclaw verify` exited 0 (20 identical, 4 changed reports). Stub mode cannot reach the submission
  (`SUBMIT`): the stub manifest's name matches no genome, so nothing is handed on. The ENA query and
  submission themselves remain unverified without a Webin account.
- **epitopeprediction** 3.1.1: the plain run's replay met a malformed Ensembl BioMart reply, the
  [upstream run note](known-issues.md#pipeline-specific-run-notes), and failed. With the retry config
  passed as `--config`, which the bundle copies and the replay passes on, the run and its replay
  succeeded, and the environments were identical.
- **Different file sets**: these were the only differences `nfclaw verify` reported. Tools named
  outputs by the clock or by a process ID:
  - kraken2-build in createtaxdb
  - Prokka in mag
  - FusionInspector in rnafusion
  - MISO in rnasplice
  - NanoPlot in nanoseq

  longraredisease names its MultiQC report after the output directory. hicar's MultiQC report and
  nanostring's plot exports varied between runs. The isoseq and raredisease originals were resumed
  after an attempt stopped by the shared host, so their outdirs also hold the first attempt's
  launch-stamped reports ([known issue](known-issues.md#pipeline-specific-run-notes)).
- **Reruns**: the table shows each pipeline's last run. The shared host's full disk and image
  removals stopped some first attempts, and pipelines whose bundles came from an nfclaw version with a
  defect listed below were run again. genomeqc's first replay was reported unverified: the Nextflow
  cache of that replay returned no task records, although its tasks had run. A fresh run and its
  replay were identical.

The nfclaw feature paths were replayed the same way:

- a generated samplesheet
- a YAML params file
- a failed run, whose replay failed the same way
- a resumed run
- an older release (`demo` 1.0.2) and `dev`
- a bundle moved to another directory
- both stages of a demultiplex → seqinspector chain, with the lineage verified
- `--no-provenance`, which writes no bundle

Every replay reported as successful in these final results had an `identical` environment
comparison. This describes the recorded comparison scope in [the architecture guide](architecture.md#27-verification-engine-nfclaw-verify), not complete machine identity or proof of analytical agreement.

On GitHub Actions, the `demo-validation` workflow replays the demo with Docker twice: in place, and
from the bundle's source archive with the checkout moved away. It also runs the demo with Apptainer,
which records image files by SHA-256.

The sweep found these defects in the new recording. Each is fixed and covered by tests:

- **Engines before Nextflow 23 recorded no remote inputs.** They stage remote files in a shared
  `work/stage/` directory, not `work/stage-<session>/`. The recorder now selects Nextflow's logs by
  the session each one names.
- **Images were missed on a busy host.** The watcher inspected every container started on the host
  to find the run's own, and short tasks exited before their turn. It now inspects each image
  reference once, when the first task container starts from it.
- **An nfclaw upgrade during a long run left a bundle that could not replay.** The bundled scripts
  were read from disk when the run ended, but `commands.sh` came from the code loaded at the start.
  The scripts are now read with that code.
- **Replaying from the source archive changed `${projectDir}` paths.** A replay now runs the
  recorded checkout while it still holds exactly the recorded source. It extracts the archive only
  when the checkout has changed or is gone.
- **An official Docker Hub image named with its registry (`docker.io/ubuntu`) was not pinned.**
- **`nfclaw verify` did not pair the nf-co2footprint plugin's launch-stamped reports.**
- **A samplesheet the pipeline read from a URL itself was not recorded.** nf-schema reads such a file
  without Nextflow staging it. The bundle now reads each file that nf-schema validated again, right
  after the run, and records its SHA-256. This was added at the end of the sweep and checked on demo,
  bamtofastq, datasync and fastqrepair, whose rows show the final runs. Their test samplesheets sit on
  moving test-datasets branches.

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
- **A run that aborted with `process hasn't exited` gave no cause.** That is what Nextflow before 26.10.0 prints when a
  local task is killed at its time limit (nextflow-io/nextflow#7569). `nfclaw status` now names the time-limit kill and the
  remedies in its `fix:` line.
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

These are results recorded during that validation, not current test counts:

- `pytest`: 2730 passed and 2 skipped on the Linux validation host. On macOS 2564 passed and 168 were skipped:
  167 need the pipeline submodules, which that checkout did not initialize, and one reads Linux's `/proc`.
- Website: `npm audit` found 0 vulnerabilities; type check and build passed.
- GitHub Actions on the pull request: every check passed.

For the [provenance bundle sweep](#provenance-bundles):

- `pytest`: 2898 passed and 2 skipped on the Linux validation host, with every pipeline submodule. On macOS
  2730 passed and 170 were skipped: they need the pipeline submodules, which that checkout did not
  initialize, or Linux's `/proc`.
- The `demo-validation` workflow on GitHub Actions also checks the recorded execution environment. Its Docker
  job checks the digest pins, an in-place replay and a replay from the source archive. Its Apptainer job checks
  that image files are recorded by SHA-256.

## Limits

- A bundled test profile shows that a release runs end to end on small data. It does not show that the
  results are scientifically valid for real data. Where a stronger check was possible, it was done: the
  replay comparisons, the fastqrepair known-answer cell, oncoanalyser's snapshot, the STAR-Fusion tutorial
  and the agreement of rnafusion's three fusion callers.
- Every run used Docker on Linux amd64. Singularity, Conda, other executors and arm64 were not part of
  this sweep; known-issues records the arm64 MultiQC export failure.
- rnafusion ran on upstream's hosted GRCh38 references instead of building them, as its `test` profile
  would. The reference build itself ran only on the STAR-Fusion tutorial's minigenome (upstream's
  `test_build` profile).
- seqsubmit was not run to completion: its test queries ENA with a Webin account, which this validation
  did not have. The tasks before that query completed ([details](known-issues.md#pipeline-specific-run-notes)),
  and a stub run covered its workflow up to the ENA submission ([above](#provenance-bundles)).
- The host's IPv6-only network shaped several runs: host networking, a local FTP relay, and local copies
  of ENA reads. A host with IPv4 connectivity should need none of these.
- A bundle records the images Nextflow runs and the remote files Nextflow stages. It does not record
  files a task downloads by itself: genomeqc's Dfam database, epitopeprediction 3.1.1's BioMart replies, or
  databases fetched inside a task. A replay can therefore meet other bytes there. Conda environments
  are not recorded either.
- Singularity and Apptainer image hashing ran only in CI, on the demo pipeline. Podman ran only in
  tests.
