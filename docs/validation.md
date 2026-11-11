# End-to-end validation

Every pipeline pinned at the time of the validation was attempted through `nfclaw`.
Of 91 bundled tests, 90 reached success, including proteinfold's stub-only test;
seqsubmit could not complete without ENA credentials. nfclaw's own features were
tested on the same host: replay, verification, resume, chains, sample-sheet generation, stop handling,
versions and status reporting. This page records how the runs were done, what passed, and what each
result does and does not show.

The versions and observations below describe the validation of 2026-10-14 to 2026-10-16; they are
not repeated after every change to the repository. Since then:

- releases bumped and pipelines added, and run the same way, are listed under
  [Releases bumped or added after the sweep](#releases-bumped-or-added-after-the-sweep);
- the [final pin sweep](#final-pin-sweep) of 2026-11-05 to 2026-11-06 ran every pin again, with its
  replay;
- the [final-code sweep](#final-code-sweep) of 2026-11-07 to 2026-11-08 ran them once more on the
  audited code.

The automated updater itself publishes a release only after its preview, the tests, the drift checks
and a real run of its bundled test on a hosted runner pass ([publication policy](maintenance.md)).
For the current pin and its requirements, read `pipelines/<name>/skill.md`.

---

## Navigation

[Environment](#environment) • [Method](#method) • [Pipelines](#pipelines) • [Fresh single-attempt runs](#fresh-single-attempt-runs) • [Releases bumped or added after the sweep](#releases-bumped-or-added-after-the-sweep) • [Final pin sweep](#final-pin-sweep) • [Final-code sweep](#final-code-sweep) • [nfclaw features](#nfclaw-features) • [Chains](#chains) • [Provenance bundles](#provenance-bundles) • [Defects found and fixed](#defects-found-and-fixed) • [Test suites and CI](#test-suites-and-ci) • [Limits](#limits)

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
automated updater published itself (rnastructurome 1.1.0, genomeassembler 2.0.1 and those dated 2026-11-05), after it. This execution evidence is additional to
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
| createpanelrefs | 1.1.0 | 26.04.3 | success | 2 completed | 2026-11-03, bump from 1.0.0, default bridge network |
| ampliseq | 3.1.0 | 26.04.0 | success | 130 completed | 2026-11-05, bump from 3.0.0 published by the updater, host network |
| bacmodel | 1.0.1 | 25.10.4 | success | 2 completed | 2026-11-05, bump from 1.0.0 published by the updater, host network |
| detaxizer | 1.4.0 | 26.04.0 | success | 54 completed | 2026-11-05, bump from 1.3.0 published by the updater, host network |
| pixelator | 6.0.0 | 25.10.4 | success | 27 completed | 2026-11-05, bump from 5.0.3 published by the updater, host network |
| sarek | 3.11.0 | 25.10.4 | success | 22 completed | 2026-11-05, bump from 3.10.0 published by the updater, host network; replayed in the [final pin sweep](#final-pin-sweep) |
| sopa | 1.0.2 | 25.10.4 | success | 9 completed | 2026-11-05, bump from 1.0.1 published by the updater, host network; its replay in the [final pin sweep](#final-pin-sweep) is refused, as documented |
| bacass | 2.7.0 | 25.10.4 | success | 17 completed | 2026-11-05, bump from 2.6.1 published by the updater, host network; in the [final pin sweep](#final-pin-sweep) |
| variantbenchmarking | 1.6.0 | 25.10.4 | success | 68 completed | 2026-11-05, bump from 1.5.0 published by the updater, host network; in the [final pin sweep](#final-pin-sweep) |
| variantbenchmarking | 1.6.1 | 25.10.4 | success | 68 completed | 2026-11-05, bump from 1.6.0 published by the updater, host network; on a later head, in the [final pin sweep](#final-pin-sweep) |

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
- **createpanelrefs 1.1.0** (2026-11-03) was bumped by hand. The updater ran the same bump that day and refused it
  at its preview gate: like 1.0.0, the release's default preview prints "Pipeline completed successfully" and never
  exits ([known issues](known-issues.md#upstream-pipeline-bugs-documented-not-patched)). A preview of its commit
  `b9d0e44` on 26.04.0 reproduced that timeout with the documented evidence (`known-timeout`). The bundled test
  (CNVkit on two BAMs) completed: CNVKIT_BATCH and MultiQC. Its outputs matched the paths of the release's closest
  `-profile test` snapshot (`--cnvkit_method hybrid --cnvkit_targets`), apart from the reference BEDs named after
  their source (`genome.*.bed` instead of `multi_intervals.*.bed`), and the versions it records (cnvkit 0.9.14,
  samtools 1.24). As with 1.0.0, the antitarget coverage tables hold only their header. The replay from
  `provenance/commands.sh` succeeded with an identical environment: `nfclaw verify` reported 13 identical, 9
  changed, 0 missing, 0 extra, and the panel of normals, both target coverage tables and the reference BEDs were
  byte-identical. The changed files were run metadata and MultiQC reports.
- **The six releases of 2026-11-05** ran for the [final audit](audit/2026-11-05-final-audit.md), with
  `--limit-cpus 8 --limit-memory 24.GB`, and were not compared with their nf-test snapshots. The replays of
  ampliseq, bacmodel, detaxizer and pixelator succeeded with an identical execution environment, and `nfclaw verify`
  reported 0 missing and 0 extra: 1,288 identical and 322 changed, 15 and 5, 80 and 42, 21 and 97. The volume was too
  full to replay sarek and sopa then, and to finish bacass 2.7.0 and variantbenchmarking 1.6.0, which a disk
  watchdog stopped after 9 and 53 tasks. With room made, all four ran with their replays in the
  [final pin sweep](#final-pin-sweep).

## Final pin sweep

For the [final audit](audit/2026-11-05-final-audit.md), 90 of the 95 pins ran again from 2026-11-05 to
2026-11-06, at one commit of the runner (`a23a092`): the bundled test, its replay from
`provenance/commands.sh`, then `nfclaw verify`. coproid's last rerun ran on `85313d4` and marsseq's on `ebc2a96`, which has the runner of the last code change, and their rows say so. Three jobs ran at a time, each on the engine its `skill.md`
names and the host network, with `--limit-cpus 8 --limit-memory 20.GB` on every engine that applies them (77 of
the 91 jobs: marsseq has one job to build its references and one to analyse). funcscan and marsseq ran alone at
the end. The per-job record is [`audit/evidence/2026-11-05-pin-sweep.json`](audit/evidence/2026-11-05-pin-sweep.json).

This repeats execution and replay. It does not compare outputs with nf-test snapshots or assess their science,
except that the tumourevo and hgtseq demos also passed their [output contracts](scientific-output-contracts.md).
Runs that came after `a23a092` and what they cover are in the audit.

The other five pins: ampliseq, bacmodel, detaxizer and pixelator ran separately for the same audit, as
[listed above](#releases-bumped-or-added-after-the-sweep). oncoanalyser did not run: its references were deleted on
2026-10-16, and its `STAR_ALIGN` peaked just above the memory this host had available then. It ran on 2026-11-08,
[after the final-code sweep](#final-code-sweep). variantbenchmarking moved to 1.6.1 after the sweep began, so both versions have a row.

Of the 91 jobs, 90 runs succeeded; the other is seqsubmit. Of their replays, 88 succeeded, and the environment of 84 was identical to the recording. `nfclaw verify` exited 0 for 81 and 1 for 7. On their first attempt with no retry or rerun, 69 jobs ended with success, an identical environment and `nfclaw verify` 0, and 3 of those carry caveats. No job's final attempt left a container behind.

What did not come out clean, by kind:

- **The run did not finish.** seqsubmit needs ENA Webin credentials.
- **marsseq ran without STAR's index.** That index takes more memory than this host has: about 48 GiB before exit 137
  under a `48.GB` cap and 46.2 GiB on the retry that completed, in October, against about 30 GiB available. The sweep's guards
  stopped the build at 2.6 GB of memory and then at 2.8 GB of disk, and with more room a 26 GB cap killed STAR with exit 137.
  The bundled analysis reads that index only with `--velocity`, which its test profile leaves off, though it checks that the path exists, so
  [the build ran without `--velocity` and the analysis named an empty directory as `--star-index`](known-issues.md#upstream-pipeline-bugs-documented-not-patched).
  Both ran, replayed with an identical environment and exited 0 in `nfclaw verify`. The analysis has the 75 identical and
  67 changed files of [its earlier row](#provenance-bundles), where the index was real. The build with STAR's index,
  and the analysis with `--velocity`, ran on 2026-11-08, [after the final-code sweep](#final-code-sweep).
- **The replay did not complete.** sopa's test names a GitHub HTML page as its data, so the environment check
  [refuses the replay](known-issues.md#pipeline-specific-run-notes). reportho's tasks query live databases:
  [3 of 7 launches failed on Ensembl's answers](known-issues.md#pipeline-specific-run-notes). Two replays failed, one of
  them because two `DIAMOND_CLUSTER` tasks hit upstream's 3-minute limit. The traces suggest a first image download
  slowing the shared volume, but one pull on an idle host did not reproduce that, so the link is unproven. A third,
  from the kept bundle, passed: environment identical, 30 identical and 26 changed.
- **The environment check stays `unverified`.** mcmicro, circdna and raredisease run
  [tasks with no container](known-issues.md#a-process-cannot-be-pinned-to-an-image-digest),
  and genomeqc's test profile [leaves no task records](known-issues.md#a-run-has-no-task-records-nextflow-holds-no-task-records-for-this-run).
  Their replays succeeded and `nfclaw verify` exits 0. The [table of 2026-10-16](#provenance-bundles) shows `identical`
  for all four. That fits runs from before these checks existed, inferred from the code rather than from
  running the old code again.
- **`nfclaw verify` exits 1: a file exists on one side only.** All of these replays have an identical environment.
  [Their differences are listed](known-issues.md#pipeline-specific-run-notes): rnafusion, nanostring, longraredisease,
  mag, spatialaxe (9 and 10 cells), nanoseq and rnasplice. rnasplice's 20 missing and 20 extra files were not read,
  since the run directory was gone; the count matches 2.0.0's earlier row.
- **A first attempt failed and a rerun passed.** seqinspector, metatdenovo and drop stopped on a
  [remote file reported as missing](known-issues.md#a-samplesheets-remote-file-is-reported-as-missing-but-it-exists),
  and drop's left one container behind. coproid's failed downloading NCBI's taxonomy, and its rerun's replay, under
  load, lost 25 plot exports. A further rerun on an idle host, on `85313d4`, kept them all and `nfclaw verify` exited 0.
  That fits [MultiQC's 30-second limit on exports](known-issues.md#pipeline-specific-run-notes): the whole task took
  27.4 s there. The link is inferred, because the logs of the replay that lost them were not kept. funcscan's
  `RUNDBCAN_DATABASE` hit the test profile's one-hour limit on a slow download and took 11 minutes on `--resume`.
  hgtseq, rerun with the references its contract needs, stopped once with `Pipeline completed with errors` and
  passed on `--resume`. No cause was read for that stop or for coproid's. reportho's run also needed its resume.
- **Success with caveats.** proteinfold's test is a stub run, so it computes nothing. cutandrun, hicar and mag
  succeeded with failures their own configuration ignores. [The guide quotes the three failures](known-issues.md#a-successful-run-is-missing-samples): each tool stopped saying it had too little to work with.

Tasks in pathogensurveillance (`DOWNLOAD_ASSEMBLIES`, exit 1) and proteinfamilies (exit 137) failed and passed on
Nextflow's retry, so these runs carry no caveat.

| Run | Nextflow | Run outcome | Tasks | Images | Pinned / recorded processes | Remote inputs | Replay | Environment | `nfclaw verify` |
|---|---|---|---|---|---|---|---|---|---|
| airrflow 5.1.2 | 26.04.1 | success | 170 | 10 | 38/38 | 23 | success | identical | 175 identical, 355 changed |
| atacseq 2.1.2 | 23.04.0 | success | 265 | 26 | 75/75 | 11 | success | identical | 396 identical, 337 changed |
| bacass 2.7.0 | 25.10.4 | success | 17 | 8 | 10/10 | 7 | success | identical | 130 identical, 114 changed |
| bactmap 1.0.0 | 24.10.5 | success | 47 | 17 | 23/23 | 7 | success | identical | 53 identical, 60 changed |
| bamtofastq 2.2.1 | 25.10.4 | success | 32 | 5 | 17/17 | 6 | success | identical | 23 identical, 15 changed |
| callingcards 1.0.0 | 23.04.0 | success | 122 | 12 | 19/19 | 5 | success | identical | 273 identical, 180 changed |
| chipseq 2.1.0 | 23.04.0 | success | 215 | 26 | 50/50 | 15 | success | identical | 288 identical, 363 changed |
| circdna 1.1.0 | 23.04.0 | success | 89 | 15 | 31/33 | 8 | success | unverified | 106 identical, 75 changed |
| coproid 2.0.1, on `85313d4` | 25.04.0 | success | 47 | 15 | 25/25 | 13 | success | identical | 184 identical, 178 changed, 11 links changed |
| createpanelrefs 1.1.0 | 26.04.0 | success | 2 | 2 | 2/2 | 3 | success | identical | 13 identical, 9 changed |
| createtaxdb 3.1.0 | 25.10.4 | success | 28 | 16 | 22/22 | 17 | success | identical | 61 identical, 19 changed |
| crisprseq 2.3.0 | 24.04.2 | success | 44 | 15 | 17/17 | 6 | success | identical | 108 identical, 83 changed |
| cutandrun 3.2.2 | 23.04.0 | success, with caveats | 135 | 21 | 95/95 | 11 | success | identical | 160 identical, 116 changed |
| datasync 1.0.2 | 25.10.4 | success | 7 | 2 | 4/4 | 4 | success | identical | 22 identical, 11 changed |
| demo 1.2.0 | 25.10.4 | success | 8 | 4 | 4/4 | 5 | success | identical | 42 identical, 34 changed |
| demultiplex 1.8.0 | 25.10.4 | success | 7 | 6 | 7/7 | 2 | success | identical | 95 identical, 81 changed |
| denovotranscript 1.2.1 | 24.04.2 | success | 19 | 13 | 15/15 | 6 | success | identical | 118 identical, 2223 changed |
| differentialabundance 2.0.0 | 25.10.4 | success | 25 | 11 | 17/17 | 6 | success | identical | 65 identical, 15 changed |
| drop 1.0.0 | 25.10.0 | success | 134 | 18 | 52/52 | 34 | success | identical | 237 identical, 79 changed |
| drugresponseeval 1.3.0 | 26.04.0 | success | 34 | 2 | 16/16 | 3 | success | identical | 196 identical, 13 changed |
| epitopeprediction 3.2.0 | 25.10.4 | success | 21 | 9 | 17/17 | 4 | success | identical | 36 identical, 39 changed |
| fastqrepair 1.1.1 | 25.10.4 | success | 9 | 4 | 7/7 | 3 | success | identical | 33 identical, 38 changed |
| fastquorum 2.0.0 | 25.10.4 | success | 12 | 7 | 12/12 | 4 | success | identical | 29 identical, 18 changed |
| fetchngs 1.13.0 | 25.10.4 | success | 26 | 2 | 4/4 | 0 | success | identical | 45 identical, 5 changed |
| funcprofiler 1.0.0 | 25.10.4 | success | 13 | 7 | 8/8 | 11 | success | identical | 39 identical, 10 changed |
| funcscan 4.0.0 | 25.10.4 | success after `--resume` | 68 | 15 | 37/37 | 5 | success | identical | 81 identical, 33 changed |
| genomeassembler 2.0.1 | 25.10.4 | success | 88 | 14 | 30/30 | 7 | success | identical | 234 identical, 87 changed |
| genomeqc 1.0.1 | 25.10.4 | success | 88 | 0 | 0/0 | 10 | success | unverified | 687 identical, 330 changed |
| hadge 1.0.0 | 25.10.4 | success | 103 | 25 | 34/34 | 7 | success | identical | 461 identical, 58 changed |
| hgtseq 1.1.0 | 22.10.1 | success after `--resume` | 63 | 13 | 27/27 | 10 | success | identical | 210 identical, 94 changed |
| hic 2.1.0 | 22.10.1 | success | 38 | 14 | 26/26 | 3 | success | identical | 61 identical, 51 changed |
| hicar 1.0.0 | 21.10.3 | success, with caveats | 95 | 33 | 73/73 | 9 | success | identical | 86 identical, 53 changed |
| hlatyping 2.2.0 | 25.04.2 | success | 7 | 7 | 7/7 | 2 | success | identical | 49 identical, 37 changed |
| isoseq 3.0.1 | 25.10.4 | success | 45 | 10 | 13/13 | 6 | success | identical | 166 identical, 77 changed |
| longraredisease 1.0.0 | 25.04.0 | success | 46 | 22 | 46/46 | 7 | success | identical | 62 identical, 41 changed, 7 missing, 7 extra, 1/1 directories missing/extra |
| lsmquant 1.0.3 | 25.10.4 | success | 14 | 5 | 7/7 | 2 | success | identical | 223 identical, 33 changed |
| mag 5.5.0 | 26.04.0 | success, with caveats | 188 | 25 | 41/41 | 8 | success | identical | 857 identical, 507 changed, 15 missing, 15 extra |
| magmap 1.3.1 | 26.04.0 | success | 59 | 16 | 29/29 | 11 | success | identical | 82 identical, 55 changed |
| marsseq 1.0.3, on `ebc2a96` | 23.04.0 | success | 34 | 9 | 14/14 | 6 | success | identical | 75 identical, 67 changed |
| marsseq-refs 1.0.3, on `ebc2a96` | 23.04.0 | success | 8 | 6 | 8/8 | 0 | success | identical | 11 identical, 3 changed |
| mcmicro 2.0.0 | 25.04.0 | success | 11 | 6 | 10/11 | 1 | success | unverified | 18 identical, 13 changed |
| metaboigniter 2.0.1 | 23.04.0 | success | 13 | 3 | 7/7 | 3 | success | identical | 20 identical, 21 changed, 27 links changed |
| metapep 1.0.0 | 24.04.2 | success | 27 | 9 | 18/18 | 4 | success | identical | 25 identical, 21 changed |
| metatdenovo 2.0.0 | 25.10.4 | success | 86 | 24 | 41/41 | 14 | success | identical | 66 identical, 125 changed |
| methylong 2.0.0 | 25.04.0 | success | 25 | 15 | 25/25 | 3 | success | identical | 22 identical, 29 changed |
| methylseq 4.2.0 | 25.04.0 | success | 36 | 6 | 12/12 | 6 | success | identical | 104 identical, 112 changed |
| mhcquant 3.3.0 | 25.10.4 | success | 21 | 6 | 13/13 | 5 | success | identical | 23 identical, 44 changed |
| molkart 1.2.0 | 25.04.0 | success | 22 | 6 | 12/12 | 4 | success | identical | 28 identical, 14 changed, 8 links changed |
| multiplesequencealign 1.1.1 | 25.04.2 | success | 78 | 13 | 35/35 | 7 | success | identical | 41 identical, 25 changed |
| nanoseq 3.1.0 | 22.10.1 | success | 26 | 10 | 16/16 | 3 | success | identical | 27 identical, 39 changed, 1 missing, 45 extra |
| nanostring 1.3.3 | 25.10.2 | success | 7 | 4 | 5/5 | 5 | success | identical | 33 identical, 26 changed, 2 missing, 1 extra |
| nascent 2.3.0 | 24.04.2 | success | 149 | 19 | 37/37 | 8 | success | identical | 226 identical, 121 changed |
| pacvar 1.1.0 | 25.10.4 | success | 10 | 5 | 10/10 | 5 | success | identical | 15 identical, 10 changed |
| pairgenomealign 3.0.4 | 26.04.0 | success | 20 | 5 | 12/12 | 4 | success | identical | 37 identical, 19 changed |
| pangenome 1.1.3 | 24.04.2 | success | 22 | 7 | 20/20 | 1 | success | identical | 8 identical, 61 changed |
| pathogensurveillance 1.1.0 | 25.04.6 | success | 47 | 13 | 17/17 | 0 | success | identical | 758 identical, 146 changed, 326 links changed |
| phaseimpute 1.1.0 | 25.04.0 | success | 40 | 7 | 18/18 | 11 | success | identical | 13 identical, 55 changed |
| phyloplace 2.3.0 | 26.04.0 | success | 8 | 5 | 8/8 | 4 | success | identical | 22 identical, 11 changed |
| plasmodiumdrugres 1.0.0 | 25.10.4 | success | 6 | 3 | 6/6 | 4 | success | identical | 11 identical, 4 changed |
| proteinannotator 1.1.0 | 25.10.4 | success | 40 | 8 | 18/18 | 4 | success | identical | 65 identical, 33 changed |
| proteinfamilies 2.6.0 | 26.04.0 | success | 93 | 12 | 34/34 | 2 | success | identical | 68 identical, 33 changed |
| proteinfold 2.0.0 | 25.10.2 | success, with caveats | 5 | 3 | 3/3 | 1 | success | identical | 16 identical, 4 changed |
| provenancereport 1.0.0 | 25.10.4 | success | 5 | 3 | 5/5 | 2 | success | identical | 18 identical, 17 changed |
| rangeland 1.0.0 | 24.04.2 | success | 280 | 3 | 12/12 | 6 | success | identical | 1177 identical, 42 changed, 861 links changed |
| raredisease 3.1.2 | 25.10.4 | success | 876 | 43 | 186/188 | 42 | success | unverified | 217 identical, 182 changed |
| readsimulator 1.0.1 | 23.04.0 | success | 1 | 1 | 1/1 | 0 | success | identical | 5 identical, 7 changed |
| reportho 1.1.0 | 25.04.0 | success after `--resume` | 70 | 12 | 35/35 | 1 | failed twice, then success | identical | 30 identical, 26 changed |
| ribomsqc v1.0.0 | 25.04.0 | success | 4 | 3 | 4/4 | 3 | success | identical | 7 identical, 10 changed |
| riboseq 2.0.0 | 25.10.4 | success | 356 | 25 | 50/50 | 22 | success | identical | 504 identical, 597 changed |
| rnadnavar 1.0.0 | 25.10.4 | success | 120 | 17 | 34/34 | 9 | success | identical | 158 identical, 158 changed |
| rnafusion 4.1.3 | 25.10.4 | success | 23 | 16 | 23/23 | 7 | success | identical | 190 identical, 115 changed, 1 missing, 1 extra |
| rnaseq 3.27.0 | 25.10.4 | success | 234 | 26 | 65/65 | 19 | success | identical | 710 identical, 346 changed |
| rnasplice 2.0.0 | 26.04.0 | success | 139 | 28 | 62/62 | 12 | success | identical | 2702 identical, 1537 changed, 20 missing, 20 extra |
| rnastructurome 1.1.0 | 25.10.4 | success | 52 | 15 | 38/38 | 5 | success | identical | 73 identical, 15 changed |
| rnavar 1.3.0 | 25.10.4 | success | 43 | 11 | 35/35 | 10 | success | identical | 49 identical, 51 changed |
| sarek 3.11.0 | 25.10.4 | success | 22 | 12 | 20/20 | 10 | success | identical | 86 identical, 97 changed |
| scnanoseq 1.3.0 | 25.04.2 | success | 85 | 18 | 46/46 | 5 | success | identical | 94 identical, 95 changed |
| scrnaseq 4.2.0 | 25.10.4 | success | 19 | 7 | 8/8 | 9 | success | identical | 83 identical, 50 changed |
| seqinspector 1.1.2 | 25.10.4 | success | 48 | 11 | 13/13 | 11 | success | identical | 555 identical, 523 changed |
| seqsubmit 1.0.0 | 25.10.4 | failed | 16 | 11 | 12/12 | 6 | not run | — | — |
| smrnaseq 2.4.1 | 25.04.2 | success | 244 | 16 | 41/41 | 14 | success | identical | 222 identical, 147 changed |
| sopa 1.0.2 | 25.10.4 | success | 9 | 2 | 9/9 | 1 | failed | differs | — |
| spatialaxe 1.0.1 | 25.04.0 | success | 10 | 5 | 10/10 | 1 | success | identical | 490 identical, 140 changed, 1 missing, 26 extra, 0/26 directories missing/extra |
| stableexpression 1.1.0 | 26.04.4 | success | 246 | 13 | 31/31 | 1 | success | identical | 45 identical, 5 changed |
| taxprofiler 2.0.1 | 25.10.4 | success | 179 | 27 | 51/51 | 26 | success | identical | 341 identical, 381 changed |
| tumourevo 1.0.0 | 25.10.4 | success | 66 | 11 | 18/18 | 15 | success | identical | 133 identical, 83 changed |
| variantbenchmarking 1.6.0 | 25.10.4 | success | 68 | 7 | 24/24 | 7 | success | identical | 47 identical, 47 changed |
| variantprioritization 1.0.0 | 25.10.0 | success | 19 | 7 | 11/11 | 8 | success | identical | 476 identical, 32 changed |
| viralintegration 0.1.1 | 23.04.0 | success | 45 | 9 | 23/23 | 9 | success | identical | 157 identical, 74 changed |
| viralmetagenome 1.2.0 | 25.10.4 | success | 288 | 35 | 86/86 | 16 | success | identical | 391 identical, 184 changed |
| viralrecon 3.0.0 | 25.04.0 | success | 200 | 32 | 80/80 | 10 | success | identical | 453 identical, 238 changed |
| variantbenchmarking 1.6.1, on `aea5fa4` | 25.10.4 | success | 68 | 7 | 24/24 | 7 | success | identical | 45 identical, 49 changed |

## Final-code sweep

The final pin sweep ran on `a23a092`, before the audit's last runner changes. So the same harness ran every pin
but oncoanalyser again, from 2026-11-07 01:59 to 2026-11-08 01:40 UTC, on `8d8c8b8`, whose tree `main` has at
`bec857d`: 95 jobs, with marsseq's two. Engines, limits and host configuration were those above, with
`--limit-cpus 8 --limit-memory 20.GB` on the 81 jobs whose engine applies them. The per-job record is
[`audit/evidence/2026-11-07-final-code-sweep.json`](audit/evidence/2026-11-07-final-code-sweep.json). Every row's
version and commit match the pins at `8d8c8b8`.

- **Runs.** 93 of 95 succeeded. seqsubmit needs ENA Webin credentials. reportho's run and its `--resume` both
  failed in `FETCH_ENSEMBL_IDMAP` on an [answer from Ensembl that is not JSON](known-issues.md#pipeline-specific-run-notes).
  hgtseq and stableexpression passed on their `--resume`: hgtseq after its
  [intermittent Groovy exception](known-issues.md#intermittent-no-signature-of-method-javautillinkedhashmapsubmap-is-applicable),
  stableexpression after EBI's FTP server refused a connection.
- **Replays.** 91 of 93 succeeded. sopa's is refused, as before. funcscan's failed when the download of dbCAN's
  database from S3 timed out.
- **Environment.** Identical in 87, differs in sopa, and `unverified` in mcmicro, circdna, raredisease and genomeqc.
  Their bundles now record why, a process with no container or no task records, where at `a23a092` none did.
- **`nfclaw verify`.** It exited 0 for 82 replays and 1 for 9: the seven of the final pin sweep, hicar and hlatyping.
- **First attempts.** 73 jobs ended with success, an identical environment, `nfclaw verify` 0 and no container left at
  their first attempt; 2 of those carry caveats (cutandrun, proteinfold).
- **The disk guard** stopped five jobs when the volume fell below 4 GB free, and reran each alone at the end:
  hadge, differentialabundance and lsmquant then came out clean, genomeqc and mcmicro `unverified` as above.
- **No job left a container behind**, and tumourevo's and hgtseq's demos passed their
  [output contracts](scientific-output-contracts.md).
- **marsseq** built its references without `--velocity` in 3,395 s (8 tasks), and its analysis, with an empty
  `--star-index`, took 332 s (34 tasks). Both replayed with an identical environment and `nfclaw verify` 0, with the
  11 identical and 3 changed, and the 75 identical and 67 changed files of their rows on `ebc2a96`.

What came out differently from the final pin sweep:

| Job | `a23a092` | `8d8c8b8` | Why |
|---|---|---|---|
| funcscan 4.0.0 | run passed on `--resume`; replay identical, verify 0 | run passed; replay failed | `RUNDBCAN_DATABASE`: `Read timed out` from `dbcan.s3.us-west-2.amazonaws.com` |
| hicar 1.0.0 | verify 0 | verify 1: 8 missing, 1 extra | [MultiQC receives one of samtools' `stats`, `flagstat` and `idxstats`](known-issues.md#pipeline-specific-run-notes) |
| hlatyping 2.2.0 | verify 0 | verify 1: 8 missing | the replay's MultiQC exported 22 of 30 plots before its [30-second limit](known-issues.md#pipeline-specific-run-notes) |
| mag 5.5.0 | 15 missing, 15 extra | 9 missing, 9 extra | Prokka's temporary files are named by process ID |
| nanostring 1.3.3 | 2 missing, 1 extra | 5 extra | MultiQC exported 8 of 15 plots in the run and 13 in the replay |
| reportho 1.1.0 | run passed on `--resume`; replays failed twice | run failed on `--resume` too | `FETCH_ENSEMBL_IDMAP`, above |
| spatialaxe 1.0.1 | 1 missing, 26 extra | 26 missing, 1 extra | Proseg segmented 10 cells in the run and 9 in the replay this time |
| stableexpression 1.1.0 | passed at the first attempt | passed on `--resume` | EBI's FTP server refused a connection |

Logs of every MultiQC and failed task were kept this time. The plot-export timeout appears in three pipelines'
logs: hlatyping's replay, nanostring's run and replay, and stableexpression's run and replay, which exported 64 and
60 of 93 plots and still verified with exit 0, so its published files hold none of them. coproid's run and replay
logged none and verified with exit 0.

After the sweep, on 2026-11-08, three more jobs ran the same way on `8289263`, which differs from `8d8c8b8` only
in drugresponseeval's pin. They are under `later_head` and `retries` in the record; the sweep's rows stand.

| Run | Nextflow | Run outcome | Tasks | Replay | Environment | `nfclaw verify` |
|---|---|---|---|---|---|---|
| drugresponseeval 1.4.0, the updater's bump | 26.04.0 | success | 30 | success | identical | 196 identical, 13 changed |
| funcscan 4.0.0, again | 25.10.4 | success | 68 | success | identical | 84 identical, 30 changed |
| reportho 1.1.0, again | 25.04.0 | success after `--resume` | 2 cached + 67 completed | success | identical | 24 identical, 32 changed, 25 extra |

reportho's first attempt failed again in `FETCH_ENSEMBL_IDMAP` on a reply that was not JSON. The 25 extra files are BicD2's
`merge/`, `score/` and `report/` results: the run, though successful, had none,
[as reportho can drop a query](known-issues.md#pipeline-specific-run-notes).

Later on 2026-11-08, `/dev/shm` was cleared of leftovers from other work, and about 63 GB of the host's memory was
available instead of about 31 GB. The two jobs this sweep had left out then ran the same way: oncoanalyser through
the deployed nfclaw 1.0.0 (`5d14ed4`), and marsseq's reference build with `--velocity`, which builds STAR's index,
then its analysis with `--velocity`, on `453d68e`, whose runner is 1.0.0's. The per-job record is
[`audit/evidence/2026-11-08-oncoanalyser-and-marsseq.json`](audit/evidence/2026-11-08-oncoanalyser-and-marsseq.json).

| Run | Nextflow | Run outcome | Tasks | Replay | Environment | `nfclaw verify` |
|---|---|---|---|---|---|---|
| oncoanalyser 3.0.0 | 25.10.4 | success | 42 | success | identical | 253 identical, 177 changed |
| marsseq 1.0.3 reference build, `--velocity` | 23.04.0 | success | 9 | success | identical | 26 identical, 4 changed |
| marsseq 1.0.3 analysis, `--velocity` | 23.04.0 | success | 38 | success | identical | 112 identical, 85 changed |

- **oncoanalyser** ran its bundled test with references extracted once and passed through upstream's
  `tests/cached_refs.config`, [as its run note describes](known-issues.md#pipeline-specific-run-notes), in 40 minutes.
  Its `STAR_ALIGN` peaked at 29.7 GiB and each `BWAMEM2_ALIGN` at 17.4 GiB. `nfclaw verify --require-environment`
  exited 1 only because its samplesheet is a remote validation input, whose refetched bytes
  [do not establish the bytes the run read](replay.md#checking-a-replay-nfclaw-verify).
- **marsseq's build** ran with `--max-memory 48.GB --max-cpus 16`, [as its row documents](known-issues.md#upstream-pipeline-bugs-documented-not-patched).
  STAR peaked at 47.9 GiB in 27 minutes at its first attempt, and at 44.1 GiB in the replay. The run and its replay
  published the same bytes but for STAR's `Log.out` and nf-core's run metadata. The analysis ran the four tasks of
  `VELOCITY`; `VELOCITY_STARSOLO` peaked at 26.5 GiB.
- **Before `/dev/shm` was cleared,** the same pair ran on `dbd598d` with a sparse STAR index, every third suffix
  (`--genomeSAsparseD 3`), under a 26 GB cap. The analysis ran, replayed with an identical environment and verified
  with exit 0, but the build's replay was killed twice by the kernel: Nextflow counted the host's 62 GB and ran
  `STAR_GENOMEGENERATE` beside `BOWTIE2_BUILD`. With `executor.memory = 28.GB` the two ran in turn, and both jobs ran,
  replayed with an identical environment and verified with exit 0 (STAR 25.2 GiB, `VELOCITY_STARSOLO` 13 GiB). These
  rows are in the same record.

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
  defect listed below were run again.
- **genomeqc**: the table's `0`, `0/0` and `identical` mean no images were compared. Its `test` profile sets
  `cleanup = true`, which removes a successful run's task records ([known issue](known-issues.md#a-run-has-no-task-records-nextflow-holds-no-task-records-for-this-run)).
  The check now reports this as `unverified`. An earlier version of this page blamed one replay's
  Nextflow cache.

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
comparison. This describes the recorded comparison scope in [the architecture guide](architecture.md#27-verification-nfclaw-verify), not complete machine identity or proof of analytical agreement.

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
