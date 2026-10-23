---
name: rnasplice
version: 2.0.0
commit: aceb47ab77cf0edfb290a44035328ed5b7eb0be8
---

# rnasplice — full parameter reference

nf-core/rnasplice pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `star_salmon`, `star` |  | star_salmon | Specifies the alignment algorithm to use. |
| `--bam-csi-index` | boolean |  |  |  |  |  | Create a CSI index for BAM files instead of the traditional BAI index. This will be required for genomes with larger chromosome sizes. |
| `--pseudo-aligner` | string |  |  | `salmon` |  | salmon | Specifies the pseudo aligner to use. Runs in addition to `--aligner`. |
| `--salmon-quant-libtype` | string |  |  |  |  |  | Override Salmon library type inferred based on strandedness defined in meta object. |
| `--save-align-intermeds` | boolean |  |  |  |  |  | Save the intermediate BAM files from the alignment step. |
| `--save-unaligned` | boolean |  |  |  |  |  | Where possible, save unaligned reads from either STAR or Salmon to the results directory. |
| `--seq-center` | string |  |  |  |  |  | Sequencing center information to be added to read group of BAM files. |
| `--skip-alignment` | boolean |  |  |  |  |  | Skip all of the alignment-based processes within the pipeline. |
| `--star-ignore-sjdbgtf` | boolean |  |  |  |  |  | When using pre-built STAR indices do not re-extract and use splice junctions from the GTF file. |

## dexseq_deu_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aggregation` | boolean |  |  |  |  | true | Combine overlapping genes into a single aggregate gene. |
| `--alignment-quality` | integer |  |  |  | ≥ 0 | 10 | Minimum alignment quality required for reads to be counted. |
| `--dexseq-exon` | boolean |  |  |  |  | true | Run DEXSeq differential exon usage workflow. |
| `--gff-dexseq` | string (file path) |  |  |  | matches ^\S+\.gff(\.gz)?$ |  | Path to GFF3 annotation file. |
| `--n-dexseq-plot` | integer |  |  |  | ≥ 0 | 10 | Plot the N most significant genes from the DEXSeq results. |
| `--save-dexseq-annotation` | boolean |  |  |  |  |  | Save pre-processed GFF annotation file. |
| `--save-dexseq-plot` | boolean |  |  |  |  | true | Save plots of the per gene DEXSeq results. |

## dexseq_dtu_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dexseq-dtu` | boolean |  |  |  |  | true | Run DEXSeq differential transcript usage workflow. |
| `--dtu-txi` | string |  |  | `dtuScaledTPM`, `scaledTPM` |  | dtuScaledTPM | Abundance estimates used to generate the estimated counts. |
| `--ignore-tx-version` | boolean |  |  |  |  | false | Ignore transcript version numbers when matching Salmon quantification output to tx2gene file. |
| `--min-feature-expr` | integer |  |  |  | ≥ 0 | 10 | Minimal feature expression. |
| `--min-feature-prop` | number |  |  |  | ≥ 0; ≤ 1 | 0.1 | Minimal proportion for feature expression. This value should be between 0 and 1. |
| `--min-gene-expr` | integer |  |  |  | ≥ 0 | 10 | Minimal gene expression. |
| `--min-samps-feature-expr` | integer |  |  |  | ≥ 0 | 2 | Minimal number of samples where features should be expressed. |
| `--min-samps-feature-prop` | integer |  |  |  | ≥ 0 | 2 | Minimal number of samples where features should have at least the proportion `--min_feature_prop`. |
| `--min-samps-gene-expr` | integer |  |  |  | ≥ 0 | 4 | Minimal number of samples where genes should be expressed. |

## edger_deu_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--edger-exon` | boolean |  |  |  |  | true | Run edgeR workflow. |
| `--n-edger-plot` | integer |  |  |  | ≥ 0 | 10 | Plot the N most significant genes from the edgeR results. |
| `--save-edger-plot` | boolean |  |  |  |  | true | Save plots of the per gene edgeR results. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  |  | Base path for the test data directory. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format `yyyy-MM-dd_HH-mm-ss`. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--contrasts` | string | yes |  |  |  |  | Path to comma-separated file containing information about the contrasts in the experiment. |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-merged-fastq` | boolean |  |  |  |  |  | Save FastQ files after merging re-sequenced libraries in the results directory. |
| `--source` | string | yes |  | `fastq`, `genome_bam`, `transcriptome_bam`, `salmon_results` |  | fastq | Source of input files. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## isoformswitchanalyzer

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--isoformswitchanalyzer` | boolean |  |  |  |  | true | Run the IsoformSwitchAnalyzeR workflow. |
| `--isoformswitchanalyzer-alpha` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Alpha value for differential isoform expression. |
| `--isoformswitchanalyzer-dIF` | number |  |  |  | ≥ 0; ≤ 1 | 0.1 | dIF cutoff value for differential isoform expression. |

## leafcutter_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--leafcutter` | boolean |  |  |  |  |  | Run the LeafCutter workflow. |

## miso

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fig-height` | integer |  |  |  | ≥ 1 | 7 | Sashimi figure height (inches). |
| `--fig-width` | integer |  |  |  | ≥ 1 | 7 | Sashimi figure width (inches). |
| `--miso-genes` | string |  |  |  | matches ^[\w-]+(,\s+[\w-]+)*$ | ENSG00000004961, ENSG00000005302, ENSG00000147403 | List containing identifiers of genes to plot. |
| `--miso-genes-file` | string |  |  |  |  |  | New-line separate file containing identifiers of genes to plot. |
| `--miso-read-len` | integer |  |  |  | ≥ 1 | 75 | Read length used to calculate coverage. |
| `--sashimi-plot` | boolean |  |  |  |  | true | Create sashimi plots using MISO. |

## qc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-bigwig` | boolean |  |  |  |  | true | Skip bigWig file creation. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |

## read_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  | ≥ 0 |  | Instructs Trim Galore to remove bp from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | integer |  |  |  | ≥ 0 |  | Instructs Trim Galore to remove bp from the 5' end of read 2 (paired-end reads only). |
| `--min-trimmed-reads` | integer |  |  |  | ≥ 0 | 10000 | Minimum number of trimmed reads below which samples are flagged in multiqc output. |
| `--save-trimmed` | boolean |  |  |  |  |  | Save the trimmed FastQ files in the results directory. |
| `--skip-trimgalore-fastqc` | boolean |  |  |  |  |  | Skip TrimGalore! FastQC. |
| `--skip-trimming` | boolean |  |  |  |  |  | Use this if your input FastQ files have already been trimmed outside of the workflow or if you're very confident that there is no adapter contamination in your data. |
| `--three-prime-clip-r1` | integer |  |  |  | ≥ 0 |  | Instructs Trim Galore to remove bp from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--three-prime-clip-r2` | integer |  |  |  | ≥ 0 |  | Instructs Trim Galore to remove bp from the 3' end of read 2 AFTER adapter/quality trimming has been performed. |
| `--trim-nextseq` | integer |  |  |  | ≥ 0 |  | Instructs Trim Galore to apply the --nextseq=X option, to trim based on quality after removing poly-G tails. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--gencode` | boolean |  |  |  |  |  | Specify if your transcript FASTA file is in GENCODE format. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gff` | string (file path) |  |  |  | matches ^\S+\.gff(\.gz)?$ |  | Path to GFF3 annotation file. |
| `--gtf` | string (file path) |  |  |  | matches ^\S+\.gtf(\.gz)?$ |  | Path to GTF annotation file. |
| `--gtf-extra-attributes` | string |  |  |  |  | gene_name | By default, the pipeline uses the gene_name field to obtain additional gene identifiers from the input GTF file when running Salmon. |
| `--gtf-group-features` | string |  |  |  |  | gene_id | Define the attribute type used to group features in the GTF file when running Salmon. |
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--salmon-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built Salmon index. |
| `--save-reference` | boolean |  |  |  |  |  | If generated by the pipeline save the STAR index in the results directory. |
| `--star-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built STAR index. |
| `--transcript-fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA transcriptome file. |

## rmats_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rmats` | boolean |  |  |  |  | true | Run rMATS workflow. |
| `--rmats-max-exon-len` | integer |  |  |  | ≥ 1 | 500 | Maximum exon length. |
| `--rmats-min-intron-len` | integer |  |  |  | ≥ 0 | 50 | Minimum Intron Length. |
| `--rmats-novel-splice-site` | boolean |  |  |  |  |  | Detect splicing events that involve an unannotated splice site. |
| `--rmats-paired-stats` | boolean |  |  |  |  | false | Use paired statistical model. It requires that the same individuals are measured in both conditions. |
| `--rmats-read-len` | integer |  |  |  | ≥ 1 | 40 | The length of each read. |
| `--rmats-splice-diff-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.0001 | The cutoff used in the null hypothesis test for differential splicing. |

## suppa_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clusterevents-dpsithreshold` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Lower-bound for the absolute delta PSI value to cluster. |
| `--clusterevents-eps` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Maximum distance (between 0 and 1) to consider two events as members of the same cluster. |
| `--clusterevents-isoform` | boolean |  |  |  |  | true | Cluster transcripts according to PSI values across conditions |
| `--clusterevents-local-event` | boolean |  |  |  |  | true | Cluster events according to PSI values across conditions |
| `--clusterevents-method` | string |  |  | `OPTICS`, `DBSCAN` |  | DBSCAN | Clustering method to use. |
| `--clusterevents-metric` | string |  |  | `euclidean`, `manhattan`, `cosine` |  | euclidean | Distance metric. |
| `--clusterevents-min-pts` | integer |  |  |  | ≥ 1 | 20 | Minimum number of events required per cluster. |
| `--clusterevents-separation` | number |  |  |  | ≥ 0; ≤ 1 |  | Maximum distance in PSI space of an event to a cluster. |
| `--clusterevents-sigthreshold` | number |  |  |  | ≥ 0; ≤ 1 |  | P-value threshold to consider an event significant from the dpsi file. |
| `--diffsplice-alpha` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Family-wise error rate to use for the multiple test correction. |
| `--diffsplice-area` | integer |  |  |  | ≥ 1 | 1000 | Number of points in the local area of the delta PSI - average TPM distribution. |
| `--diffsplice-gene-correction` | boolean |  |  |  |  | true | Correct the p-values by gene. |
| `--diffsplice-isoform` | boolean |  |  |  |  | true | Calculate differential splicing for differential transcript usage across multiple conditions with replicates |
| `--diffsplice-local-event` | boolean |  |  |  |  | true | Calculate differential splicing for AS events across multiple conditions with replicates. |
| `--diffsplice-lower-bound` | number |  |  |  | ≥ 0; ≤ 1 | 0 | Lower-bound for the absolute delta PSI value to test for significance. |
| `--diffsplice-median` | boolean |  |  |  |  |  | Use the median to calculate the Delta PSI, instead of the mean. |
| `--diffsplice-method` | string |  |  | `empirical`, `classical` |  | empirical | The method to use to calculate the significance. |
| `--diffsplice-nan-threshold` | number |  |  |  | ≥ 0; ≤ 1 | 0 | Proportion of samples with nan values allowed per condition to calculate a delta PSI. |
| `--diffsplice-paired` | boolean |  |  |  |  | true | Indicates if replicates across conditions are paired. |
| `--diffsplice-tpm-threshold` | number |  |  |  | ≥ 0 | 0 | Minimum expression (calculated as average TPM value within-replicates and between-conditions) to be included in the analysis. |
| `--generateevents-boundary` | string |  |  | `S`, `V` |  | S | Boundary type (only used for local AS events). |
| `--generateevents-event-type` | string |  |  |  |  | SE SS MX RI FL | Space separated list of events to generate. |
| `--generateevents-exon-length` | integer |  |  |  | ≥ 1 | 100 | Defines the number of nucleotides to display in the output GTF. |
| `--generateevents-pool-genes` | boolean |  |  |  |  | true | Redefine genes by clustering together transcripts by genomic stranded overlap and sharing at least one exon. |
| `--generateevents-threshold` | integer |  |  |  | ≥ 0 | 10 | Variability threshold. |
| `--psiperevent-total-filter` | integer |  |  |  | ≥ 0 | 0 | Minimum total expression of the transcripts involved in the event. |
| `--suppa` | boolean |  |  |  |  | true | Run SUPPA workflow. |
| `--suppa-per-isoform` | boolean |  |  |  |  | true | Quantify isoform inclusion levels (PSIs) from multiple samples. |
| `--suppa-per-local-event` | boolean |  |  |  |  | true | Quantify event inclusion levels (PSIs) from multiple samples. |
| `--suppa-tpm` | string (file or directory path) |  |  |  |  |  | Expression file containing the abundances of all transcripts (ideally in TPM units). |

<!-- Generated from nf-core/rnasplice@aceb47ab77cf0edfb290a44035328ed5b7eb0be8. Do not edit by hand. -->
