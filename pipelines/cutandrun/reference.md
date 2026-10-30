---
name: cutandrun
version: 3.2.2
commit: 6e1125d4fee4ea7c8b70ed836bb0e92a89e3305f
---

# cutandrun — full parameter reference

nf-core/cutandrun pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## flow_switching_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--only-alignment` | boolean |  |  |  |  |  | Run pipeline up to alignment |
| `--only-filtering` | boolean |  |  |  |  |  | Run pipeline up to q-filtering |
| `--only-genome` | boolean |  |  |  |  |  | Run pipeline up to reference preparation |
| `--only-input` | boolean |  |  |  |  |  | Run pipeline up to input checking |
| `--only-peak-calling` | boolean |  |  |  |  |  | Run pipeline up to peak calling |
| `--only-preqc` | boolean |  |  |  |  |  | Run pipeline up to pre-alignment |
| `--skip-dt-qc` | boolean |  |  |  |  |  | Skips deeptools QC repoting |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skips fastqc reporting |
| `--skip-heatmaps` | boolean |  |  |  |  |  | Skips deeptools heatmap generation |
| `--skip-igv` | boolean |  |  |  |  |  | Skips igv session generation |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skips multiqc |
| `--skip-peak-qc` | boolean |  |  |  |  |  | Skips peak QC reporting |
| `--skip-preseq` | boolean |  |  |  |  |  | Skips preseq reporting |
| `--skip-removeduplicates` | boolean |  |  |  |  |  | Skips de-duplication |
| `--skip-reporting` | boolean |  |  |  |  |  | Skips reporting |
| `--skip-trimming` | boolean |  |  |  |  |  | Skips trimming |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--singularity-pull-docker-container` | boolean |  |  |  |  |  | Pull Docker container. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  |  | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  |  | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dump-scale-factors` | boolean |  |  |  |  |  | Output calculated scale factors from pipeline |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  | `./results` | The output directory where the results will be saved. You have to use absolute paths to store on Cloud infrastructure. |
| `--save-align-intermed` | boolean |  |  |  |  |  | Save alignment intermediates to the output directory (WARNING: can be very large) |
| `--save-merged-fastq` | boolean |  |  |  |  |  | Save any technical replicate FASTQ files that were merged to the output directory |
| `--save-reference` | boolean |  |  |  |  |  | Save genome reference data to the output directory |
| `--save-spikein-aligned` | boolean |  |  |  |  |  | Save BAM files aligned to the spike-in genome to the output directory |
| `--save-trimmed` | boolean |  |  |  |  |  | Save trimmed FASTQ files to the output directory |
| `--save-unaligned` | boolean |  |  |  |  |  | Save unaligned sequences to the output directory |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | `16` | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `128.GB` | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches `^(\d+\.?\s*(s\|m\|h\|d\|day)\s*)+$` | `240.h` | Maximum amount of time that can be requested for any single job. |

## pipeline_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  | yes |  |  | `bowtie2` | Select aligner |
| `--consensus-peak-mode` | string |  |  | `group`, `all` |  | `group` | Specifies what samples to group together for consensus peaks. Options are [group, all] |
| `--dedup-target-reads` | boolean |  |  |  |  |  | De-duplicate target reads AND control reads (default is control only) |
| `--end-to-end` | boolean |  |  |  |  | `true` | Use --end-to-end mode of Bowtie2 during alignment |
| `--extend-fragments` | boolean |  |  |  |  | `true` | Specifies whether to extend paired-end fragments between the read mates when calculating coveage tracks |
| `--igg-scale-factor` | number |  |  |  |  | `0.5` | Specifies whether the background control is scaled prior to being used to normalise peaks. |
| `--igv-show-gene-names` | boolean |  |  |  |  | `true` | Show gene names instead of symbols in IGV browser sessions |
| `--macs2-broad-cutoff` | number |  |  |  |  | `0.1` | MACS2 broad cutoff parameter |
| `--macs2-narrow-peak` | boolean |  |  |  |  | `true` | Determines whether MACS2 broad or narrow peak mode is used for the peak caller |
| `--macs2-pvalue` | number |  |  |  |  |  | P-value threshold for macs2 peak caller. If set it will overide the qvalue. |
| `--macs2-qvalue` | number |  |  |  |  | `0.01` | Q-value threshold for MACS2 peak caller. |
| `--macs-gsize` | number |  |  |  |  | `2700000000` | parameter required by MACS2. If using an iGenomes reference these have been provided when `--genome` is set as *GRCh37*, *GRCh38*, *GRCm38*, *WBcel235*, *BDGP6*, *R64-1-1*, *EF2*, *hg38*, *hg19* and *mm10*. Otherwise the gsize will default to GRCh38. |
| `--minimum-alignment-q-score` | integer |  |  |  |  | `20` | Filter reads below a q-score threshold |
| `--mito-name` | string |  |  |  |  |  | Name of mitochondrial reads in reference genome. Only necessary when using a custom (non-igenomes) reference genome. |
| `--normalisation-binsize` | integer |  |  |  |  | `50` | If normsalisation option is one of "RPKM", "CPM", "BPM" - then the binsize that the reads count is calculated on is used. |
| `--normalisation-c` | integer |  | yes |  |  | `10000` | Normalisation constant for spike-in read normalisation |
| `--normalisation-mode` | string |  |  | `Spikein`, `RPKM`, `CPM`, `BPM`, `None` |  | `Spikein` | Sets the target read normalisation mode. Options are: ["Spikein", "RPKM", "CPM", "BPM", "None" ] |
| `--peakcaller` | string |  |  |  |  | `seacr` | Selects the peak caller for the pipeline. Options are: [seacr, macs2]. More than one peak caller can be chosen and the order specifies which is a primary peak called (the first) that will be used downstream. Any secondary peak callers will be run and outputed to the results folder. |
| `--remove-linear-duplicates` | boolean |  |  |  |  |  | De-duplicate reads based on read 1 5' start position. Relevant for assays using linear amplification with tagmentation (default is false). |
| `--remove-mitochondrial-reads` | boolean |  |  |  |  |  | Filter mitochondrial reads |
| `--replicate-threshold` | number |  |  |  |  | `1` | Minimum number of overlapping replicates needed for a consensus peak |
| `--seacr-norm` | string |  |  | `non`, `norm` |  | `non` | SEACR normalization. |
| `--seacr-peak-threshold` | number |  |  |  |  | `0.05` | SEACR specifies returns the top n fraction (between 0 and 1) of peaks based on total signal within peaks. This is only used if there are no controls included with the samples and if `--use_control` is `false` |
| `--seacr-stringent` | string |  |  | `stringent`, `relaxed` |  | `stringent` | SEACR stringency. |
| `--use-control` | boolean |  |  |  |  | `true` | Specifies whether to use a control to normalise peak calls against (e.g. IgG) |

## reference_data_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--blacklist` | string |  |  |  |  |  | Path to genome blacklist |
| `--bowtie2` | string |  |  |  |  |  | Path to bowtie2 index |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--gene-bed` | string |  |  |  |  |  | Path to gene BED file |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gtf` | string |  |  |  |  |  | Path to GTF annotation file |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--spikein-bowtie2` | string |  |  |  |  |  | Path to spike-in bowtie2 index |
| `--spikein-fasta` | string |  |  |  |  |  | Path to spike-in fasta |
| `--spikein-genome` | string |  |  |  |  | `K12-MG1655` | Name of the iGenome reference for the spike-in genome, defaulting to E. coli K12, for yeast set to R64-1-1, for fruit fly BDGP6 |

## reporting_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dt-calc-all-matrix` | boolean |  |  |  |  | `true` | Flag for whether to generate a heatmap for all samples together |
| `--dt-heatmap-gene-afterlen` | integer |  |  |  |  | `3000` | Deeptools heatmap gene plot after length (bases) |
| `--dt-heatmap-gene-beforelen` | integer |  |  |  |  | `3000` | Deeptools heatmap gene plot before length (bases) |
| `--dt-heatmap-gene-bodylen` | integer |  |  |  |  | `5000` | Deeptools heatmap gene plot body length (bases) |
| `--dt-heatmap-peak-afterlen` | integer |  |  |  |  | `3000` | Deeptools heatmap peak plot after length (bases) |
| `--dt-heatmap-peak-beforelen` | integer |  |  |  |  | `3000` | Deeptools heatmap peak plot before length (bases) |
| `--dt-qc-bam-binsize` | integer |  |  |  |  | `500` | Deeptools multiBamSummary bam bin size |
| `--dt-qc-corr-method` | string |  |  |  |  | `pearson` | Deeptools Correlation Plot statistical calculation method |
| `--igv-sort-by-groups` | boolean |  |  |  |  | `true` | Sort the IGV output tracks by group |
| `--min-frip-overlap` | number |  |  |  |  | `0.2` | Minimum fragment overlap for FriP score |
| `--min-peak-overlap` | number |  |  |  |  | `0.2` | Minimum peak overlap for peak reproducibility plot |

## trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  |  | `0` | Instructs Trim Galore to remove bp from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | integer |  |  |  |  | `0` | Instructs Trim Galore to remove bp from the 5' end of read 2 (paired-end reads only). |
| `--three-prime-clip-r1` | integer |  |  |  |  | `0` | Instructs Trim Galore to remove bp from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--three-prime-clip-r2` | integer |  |  |  |  | `0` | Instructs Trim Galore to remove bp from the 3' end of read 2 AFTER adapter/quality trimming has been performed. |
| `--trim-nextseq` | integer |  |  |  |  | `0` | Instructs Trim Galore to apply the --nextseq=X option, to trim based on quality after removing poly-G tails. |

<!-- Generated from nf-core/cutandrun@6e1125d4fee4ea7c8b70ed836bb0e92a89e3305f. Do not edit by hand. -->
