---
name: drop
version: 1.0.0
commit: 20388350d242746f8e799b28c3ae80421627b077
---

# drop — full parameter reference

nf-core/drop pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## aberrant_expression

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ae-fpkm-cutoff` | integer |  |  |  | ≥ 0 | 1 | A positive number indicating the minimum FPKM value for a gene to be considered expressed. |
| `--ae-genes-to-test` | string (file path) |  |  |  | matches ^\S+\.(yaml\|yml)$ |  | Full path to a yaml file specifying lists of candidate genes per sample to test during FDR correction. See the documentation for details on the structure of this file. |
| `--ae-groups` | string |  |  |  |  |  | A comma-separated list of aberrant expression groups to run. If empty, all groups are run. |
| `--ae-implementation` | string |  |  | `autoencoder`, `pca`, `peer` |  | autoencoder | Methods to remove sample covariation in OUTRIDER. |
| `--ae-max-tested-dimension-proportion` | integer |  |  |  | ≥ 1 | 3 | An integer that controls the maximum value that the encoding dimension can take. |
| `--ae-min-ids` | integer |  |  |  | ≥ 1 | 1 | A positive number indicating the minimum number of samples that a group needs in order to be analyzed. We recommend at least 50. |
| `--ae-padj-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | A number between (0, 1] indicating the maximum FDR an event can have in order to be considered an outlier. |
| `--ae-skip` | boolean |  |  |  |  |  | Skip aberrant expression analysis. |
| `--ae-use-grid-search-to-obtain-q` | boolean |  |  |  |  |  | If true, the optimal latent space dimension for the autoencoder will be determined by grid search. If false, OHT will be performed.. |
| `--ae-yield-size` | integer |  |  |  | ≥ 1 | 2000000 | An integer that sets the batch size for counting reads within a bam file. If memory issues persist lower the yieldSize. |
| `--ae-z-score-cutoff` | number |  |  |  | ≥ 0 | 0 | A non-negative number. Z scores (in absolute value) greater than this cutoff are considered as outliers. |

## aberrant_splicing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--as-delta-psi-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.3 | A non-negative number. Delta psi values greater than this cutoff are considered as outliers. Recommand 0.3 for FRASER, 0.1 for FRASER2. |
| `--as-fraser-version` | string |  |  |  |  | FRASER2 | Version of FRASER to use. |
| `--as-genes-to-test` | string (file path) |  |  |  | matches ^\S+\.(yaml\|yml)$ |  | Full path to a yaml file specifying lists of candidate genes per sample to test during FDR correction. See the documentation for details on the structure of this file. |
| `--as-groups` | string |  |  |  |  |  | A comma-separated list of aberrant splicing groups to run. If empty, all groups are run. |
| `--as-implementation` | string |  |  | `PCA`, `PCA-BB-Decoder` |  | PCA | Methods to remove sample covariation in FRASER. |
| `--as-keep-non-standard-chrs` | boolean |  |  |  |  |  | Set to true if non standard chromosomes are to be kept for further analysis. |
| `--as-long-read` | boolean |  |  |  |  |  | Set to true only if counting Nanopore or PacBio long reads. |
| `--as-max-tested-dimension-proportion` | integer |  |  |  | ≥ 1 | 6 | An integer that controls the maximum value that the encoding dimension can take. |
| `--as-min-delta-psi` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | The minimal variation (in delta psi) required for an intron to pass the filter. |
| `--as-min-expression-in-one-sample` | integer |  |  |  | ≥ 1 | 20 | The minimal read count in at least one sample required for an intron to pass the filter. |
| `--as-min-ids` | integer |  |  |  | ≥ 1 | 1 | A positive number indicating the minimum number of samples that a group needs in order to be analyzed. We recommend at least 50. |
| `--as-padj-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.1 | Same as in aberrant expression. |
| `--as-quantile-for-filtering` | number |  |  |  | ≥ 0; ≤ 1 | 0.75 | Defines at which percentile the as_quantile_min_expression filter is applied. Recommand 0.95 for FRASER, 0.75 for FRASER2. |
| `--as-quantile-min-expression` | integer |  |  |  | ≥ 1 | 10 | The minimum total read count (N) an intron needs to have at the specified quantile across samples to pass the filter. See --as_quantile_for_filtering. |
| `--as-recount` | boolean |  |  |  |  |  | If true, it forces samples to be recounted. |
| `--as-skip` | boolean |  |  |  |  |  | Skip aberrant splicing analysis. |
| `--as-skip-filter` | boolean |  |  |  |  |  | If true, no filter is applied. We recommend filtering. |
| `--as-use-grid-search-to-obtain-q` | boolean |  |  |  |  |  | If true, the optimal latent space dimension for the autoencoder will be determined by grid search. If false, OHT will be performed.. |

## export_counts

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ec-exclude-groups` | string |  |  |  |  |  | A comma-separated list of aberrant expression and aberrant splicing groups whose counts should not be exported. If empty, all groups are exported. |
| `--ec-gene-annotations` | string |  |  |  |  |  | A comma-separated list of gene annotations to export. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/modules/data/ | Base URL or local path to location of module test dataset files |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/drop/data/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gene-annotation` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yml\|yaml)$ |  | Path to GTF gene annotations file. Equivalent to the `geneAnnotation` parameter in the snakemake pipeline, with the difference that a file depicting the kev-value pairs is expected here instead. |
| `--genome` | string | yes |  | `hg19`, `hs37d5 `, `hg38`, `GRCh38` |  |  | Equivalent to the `genomeAssembly` parameter in the snakemake pipeline. Either hg19/hs37d5 or hg38/GRCh38, depending on the genome assembly used for mapping |
| `--hpo-file` | string (file path) |  |  |  | matches ^\S+\.tsv(\.gz)?$ |  | Full path of the file containing HPO terms. If missing, it reads it from our webserver. Refer to [files-to-download](https://gagneurlab-drop.readthedocs.io/en/latest/prepare.html?highlight=drop_group#files-to-download). Equivalent to the `hpoFile` parameter in the snakemake pipeline. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.tsv$ |  | Path to the samplesheet file used by the pipeline. The file should be a TSV file. Equivalent to the `sampleAnnotation` parameter in the snakemake pipeline. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. Equivalent to the `root` parameter in the snakemake pipeline. |
| `--project-title` | string |  |  |  |  |  | Title of the project to be displayed on the rendered HTML output |
| `--random-seed` | boolean or integer |  |  |  |  |  | Specify a random seed for reproducibility |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## mono_allelic_expression

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--mae-add-af` | boolean |  |  |  |  |  | Add the allele frequencies from gnomAD |
| `--mae-allelic-ratio-cutoff` | number |  |  |  | ≥ 0.5; ≤ 1 | 0.8 | A number between [0.5, 1) indicating the maximum allelic ratio allele1/(allele1+allele2) for the test to be significant. |
| `--mae-dna-rna-match-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | fraction (0-1) used to seperate 'matching' samples and 'non-matching' samples comparing the DNA and RNA data during QC. |
| `--mae-gatk-header-check` | boolean |  |  |  |  |  | If true (recommended), it emits the header warnings of a VCF file when performing the allelic counts |
| `--mae-groups` | string |  |  |  |  |  | A comma-separated list of mono-allelic expression groups to run. If empty, all groups are run. |
| `--mae-max-af` | number |  |  |  | ≥ 0; ≤ 1 | 0.001 | Maximum allele frequency (of the minor allele) cut-off. Variants with AF equal or below this number are considered rare. |
| `--mae-max-var-freq-cohort` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Maximum variant frequency among the cohort. |
| `--mae-padj-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Same as in aberrant expression. |
| `--mae-qc-groups` | string |  |  |  |  |  | Same as 'groups', but for the VCF-BAM matching |
| `--mae-qc-vcf` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz$ |  | Full path to the vcf file used for VCF-BAM matching. Refer to [files-to-download](https://gagneurlab-drop.readthedocs.io/en/latest/prepare.html?highlight=drop_group#files-to-download). |
| `--mae-qc-vcf-tbi` | string (file path) |  |  |  | matches ^\S+\.tbi$ |  | Full path to the index of the vcf file used for VCF-BAM matching. Refer to [files-to-download](https://gagneurlab-drop.readthedocs.io/en/latest/prepare.html?highlight=drop_group#files-to-download) |
| `--mae-skip` | boolean |  |  |  |  |  | Skip mono-allelic expression analysis. |
| `--ncbi-dict` | string (file path) |  |  |  | matches ^\S+\.dict$ |  | Path to NCBI sequence dictionary file. If not provided, the pipeline will try to create it from the FASTA file. |
| `--ncbi-fai` | string (file path) |  |  |  | matches ^\S+\.fai$ |  | Path to NCBI FASTA index file. |
| `--ncbi-fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to NCBI FASTA genome file. Equivalent to the `ncbi` option in the `genome` parameter in the snakemake pipeline. |
| `--ucsc-dict` | string (file path) |  |  |  | matches ^\S+\.dict$ |  | Path to UCSC sequence dictionary file. . If not provided, the pipeline will try to create it from the FASTA file. |
| `--ucsc-fai` | string (file path) |  |  |  | matches ^\S+\.fai$ |  | Path to UCSC FASTA index file. |
| `--ucsc-fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to UCSC FASTA genome file. Equivalent to the `ucsc` option in the `genome` parameter in the snakemake pipeline. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

<!-- Generated from nf-core/drop@20388350d242746f8e799b28c3ae80421627b077. Do not edit by hand. -->
