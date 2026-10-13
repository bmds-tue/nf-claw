---
name: seqinspector
version: 1.1.2
commit: 6aa08aabb00cdbb0f5b62adf2749b472e794ba04
---

# seqinspector — full parameter reference

nf-core/seqinspector pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## bbmap_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bbmap-clumpify-args` | string |  |  |  |  | markduplicates=true | Arguments to pass to BBMap Clumpify |
| `--save-bbmap-clumpify-reads` | boolean |  |  |  |  |  | Turn on saving of BBMap Clumpify deduplicated reads |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  | yes |  |  | s3://ngi-igenomes/testdata/nf-core/modules/ | Base path / URL for data used in the modules |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--sample-size` | number |  |  |  | ≥ 0 | 0 | Take a subset of reads for analysis. |
| `--skip-tools` | string |  |  |  | matches ^((bbmap_clumpify\|checkqc\|chelae\|fastp\|fastqc\|fastqe\|fastqscreen\|fq_lint\|kraken2\|multiqcsav\|picard_collecthsmetrics\|picard_collectmultiplemetrics\|riker\|rundirparser\|seqkit_stats\|seqfu_stats\|sequali\|toulligqc)?,?)*(?<!,)$ |  | Comma-separated string of tools to skip - overrides any other means of tools selection |
| `--subsample-tools` | string |  |  |  | matches ^((all\|null\|bbmap_clumpify\|chelae\|fastp\|fastqc\|fastqe\|fastqscreen\|fq_lint\|kraken2\|picard_collecthsmetrics\|picard_collectmultiplemetrics\|riker\|seqkit_stats\|seqfu_stats\|sequali\|toulligqc)?,?)*(?<!,)$ | fastqscreen,kraken2,picard_collecthsmetrics,picard_collectmultiplemetrics | Comma-separated string of tools to run on subsampled data. Tools not in this list run on original data. |
| `--tools` | string |  |  |  | matches ^((bbmap_clumpify\|checkqc\|chelae\|fastp\|fastqc\|fastqe\|fastqscreen\|fq_lint\|kraken2\|multiqcsav\|picard_collecthsmetrics\|picard_collectmultiplemetrics\|riker\|rundirparser\|seqkit_stats\|seqfu_stats\|sequali\|toulligqc)?,?)*(?<!,)$ |  | Comma-separated string of tools to run |
| `--tools-bundle` | string |  |  |  | matches ^((all\|bam\|fastq\|default\|illumina\|minimal\|ont\|null)?,?)*(?<!,)$ | default | Select some default setup for the tools to be run, tools can still be used to add tools |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## kraken2_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--kraken2-db` | string |  |  |  |  |  | Path to Kraken2 database file, either a gzipped file or the path to the uncompressed database. |
| `--kraken2-save-readclassifications` | boolean |  |  |  |  |  | Turn on saving of Kraken2 per-read taxonomic assignment file |
| `--kraken2-save-reads` | boolean |  |  |  |  |  | Turn on saving of Kraken2-aligned reads |
| `--kraken-save-uncompressed-db` | boolean |  |  |  |  |  | Turn on saving of uncompressed Kraken2 DB |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bait-intervals` | string (file path) |  |  |  | matches ^\S+.(bed\|bed.gz\|interval_list)$ |  | Path to bait intervals file. |
| `--bwamem2` | string (directory path) |  |  |  |  |  | Path to bwamem2 indices. |
| `--dict` | string (file path) |  |  |  | matches ^\S+.dict$ |  | Sequence dictionary for the reference fasta file provided. |
| `--fai` | string (file path) |  |  |  | matches ^\S+.fai$ |  | Fasta index for the reference fasta file provided. |
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--fastq-screen-references` | string |  |  |  |  | ${projectDir}/assets/example_fastq_screen_references.csv | A .csv of reference genomes to be mapped against by FastQ Screen |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--target-intervals` | string (file path) |  |  |  | matches ^\S+.(bed\|bed.gz\|interval_list)$ |  | Path to target intervals file. |

## riker_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--riker-args` | string |  |  |  |  | --tools alignment basic isize | Arguments to pass to riker multi |

## validation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--checkqc-config` | string (file path) |  |  |  |  |  | Path to custom CheckQC config |
| `--continue-with-lint-fail` | boolean |  |  |  |  | true | Whether to continue with the pipeline if linting fails for a single sample. |
| `--fq-lint-args` | string |  |  |  |  |  | Arguments to pass to FQ lint |

<!-- Generated from nf-core/seqinspector@6aa08aabb00cdbb0f5b62adf2749b472e794ba04. Do not edit by hand. -->
