---
name: chipseq
version: 2.1.0
commit: 76e2382b6d443db4dc2396e6831d1243256d80b0
---

# chipseq — full parameter reference

nf-core/chipseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## adapter_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 2 (paired-end reads only). |
| `--save-trimmed` | boolean |  |  |  |  |  | Save the trimmed FastQ files in the results directory. |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip the adapter trimming step. |
| `--three-prime-clip-r1` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--three-prime-clip-r2` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 2 AFTER adapter/quality trimming has been performed. |
| `--trim-nextseq` | integer |  |  |  |  |  | Instructs Trim Galore to apply the --nextseq=X option, to trim based on quality after removing poly-G tails. |

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `bwa`, `bowtie2`, `chromap`, `star` |  | `bwa` | Specifies the alignment algorithm to use - available options are 'bwa', 'bowtie2' and 'star'. |
| `--bamtools-filter-pe-config` | string (file or directory path) |  | yes |  |  | `$projectDir/assets/bamtools_filter_pe.json` | BAMTools JSON file with custom filters for paired-end data. |
| `--bamtools-filter-se-config` | string (file or directory path) |  | yes |  |  | `$projectDir/assets/bamtools_filter_se.json` | BAMTools JSON file with custom filters for single-end data. |
| `--bwa-min-score` | integer |  |  |  |  |  | Don’t output BWA MEM alignments with score lower than this parameter. |
| `--keep-dups` | boolean |  |  |  |  |  | Duplicate reads are not filtered from alignments. |
| `--keep-multi-map` | boolean |  |  |  |  |  | Reads mapping to multiple locations are not filtered from alignments. |
| `--save-align-intermeds` | boolean |  |  |  |  |  | Save the intermediate BAM files from the alignment step. |
| `--save-unaligned` | boolean |  |  |  |  |  | Save unaligned sequences to the output directory (only available for Bowtie 2 and STAR. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--fingerprint-bins` | integer |  | yes |  |  | `500000` | Number of genomic bins to use when calculating deepTools fingerprint plot. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string (file path) |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string (file path) |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  |  | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  |  | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--fragment-size` | integer |  |  |  |  | `200` | Estimated fragment size used to extend single-end reads. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--read-length` | integer |  |  | `50`, `75`, `100`, `150`, `200` |  |  | Read length used to calculate MACS3 genome size for peak calling if `--macs_gsize` isn't provided. |
| `--seq-center` | string |  |  |  |  |  | Sequencing center information to be added to read group of BAM files. |

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

## peak_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--broad-cutoff` | number |  |  |  |  | `0.1` | Specifies broad cutoff value for MACS3. Only used when --narrow_peak isnt specified. |
| `--macs-fdr` | number |  |  |  |  |  | Minimum FDR (q-value) cutoff for peak detection, --macs_fdr and --macs_pvalue are mutually exclusive. |
| `--macs-pvalue` | number |  |  |  |  |  | p-value cutoff for peak detection, --macs_fdr and --macs_pvalue are mutually exclusive. If --macs_pvalue cutoff is set, q-value will not be calculated and reported as -1 in the final .xls file. |
| `--min-reps-consensus` | integer |  |  |  |  | `1` | Number of biological replicates required from a given condition for a peak to contribute to a consensus peak. |
| `--narrow-peak` | boolean |  |  |  |  |  | Run MACS3 in narrowPeak mode. |
| `--save-macs-pileup` | boolean |  |  |  |  |  | Instruct MACS3 to create bedGraph files normalised to signal per million reads. |
| `--skip-consensus-peaks` | boolean |  |  |  |  |  | Skip consensus peak generation, annotation and counting. |
| `--skip-peak-annotation` | boolean |  |  |  |  |  | Skip annotation of MACS3 and consensus peaks with HOMER. |
| `--skip-peak-qc` | boolean |  |  |  |  |  | Skip MACS3 peak QC plot generation. |

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--deseq2-vst` | boolean |  |  |  |  | `true` | Use vst transformation instead of rlog with DESeq2. |
| `--skip-deseq2-qc` | boolean |  |  |  |  |  | Skip DESeq2 PCA and heatmap plotting. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |
| `--skip-igv` | boolean |  |  |  |  |  | Skip IGV. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-picard-metrics` | boolean |  |  |  |  |  | Skip Picard CollectMultipleMetrics. |
| `--skip-plot-fingerprint` | boolean |  |  |  |  |  | Skip deepTools plotFingerprint. |
| `--skip-plot-profile` | boolean |  |  |  |  |  | Skip deepTools plotProfile. |
| `--skip-preseq` | boolean |  |  |  |  |  | Skip Preseq. |
| `--skip-qc` | boolean |  |  |  |  |  | Skip all QC steps except for MultiQC. |
| `--skip-spp` | boolean |  |  |  |  |  | Skip Phantompeakqualtools. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--blacklist` | string (file or directory path) |  |  |  |  |  | Path to blacklist regions in BED format, used for filtering alignments. |
| `--bowtie2-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built Bowtie2 index. |
| `--bwa-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built BWA index. |
| `--chromap-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built Chromap index. |
| `--fasta` | string (file path) | yes |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--gene-bed` | string (file path) |  |  |  | matches `^\S+\.bed(\.gz)?$` |  | Path to BED file containing gene intervals. This will be created from the GTF file if not specified. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gff` | string (file path) |  |  |  | matches `^\S+\.gff(\.gz)?$` |  | Path to GFF3 annotation file. |
| `--gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Path to GTF annotation file. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--macs-gsize` | number |  |  |  |  |  | Effective genome size parameter required by MACS3. |
| `--save-reference` | boolean |  |  |  |  |  | If generated by the pipeline save the BWA index in the results directory. |
| `--star-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built STAR index. |

<!-- Generated from nf-core/chipseq@76e2382b6d443db4dc2396e6831d1243256d80b0. Do not edit by hand. -->
