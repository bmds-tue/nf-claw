---
name: detaxizer
version: 1.3.0
commit: 3586921aa3a4c49271f1b2082309bdc33c819749
---

# detaxizer — full parameter reference

nf-core/detaxizer pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## bbduk

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bbduk-kmers` | integer |  |  |  |  | 27 | Length of k-mers for classification carried out by bbduk |
| `--fasta-bbduk` | string |  |  |  |  |  | Location of the fasta which contains the contaminant sequences. |

## blastn

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--blast-coverage` | number |  |  |  |  | 40.0 | Coverage is the percentage of the query sequence which can be found in the alignments of the sequence match. It can be used to fine-tune the validation step. |
| `--blast-evalue` | number |  |  |  |  | 0.01 | The expected(e)-value contains information on how many hits of the same score can be found in a database of the size used in the query by chance. The parameter can be used to fine-tune the validation step. |
| `--blast-identity` | number |  |  |  |  | 40.0 | Identity is the percentage of the exact matches in the query and the sequence found in the database. The parameter can be used to fine-tune the validation step. |
| `--fasta-blastn` | string |  |  |  |  |  | Location of the fasta from which the blastn database will be constructed. |

## fastp_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fastp-cut-mean-quality` | integer |  |  |  |  | 1 | fastp option to define the mean quality for trimming |
| `--fastp-eval-duplication` | boolean |  |  |  |  |  | fastp option if duplicates should be filtered or not before classification |
| `--fastp-qualified-quality` | integer |  |  |  |  | 0 | fastp option to define the threshold of quality of an individual base |
| `--fastp-save-trimmed-fail` | boolean |  |  |  |  |  | fastp option defining if the reads which failed to be trimmed should be saved |
| `--reads-minlength` | integer |  |  |  |  | 0 | fastp option defining the minimum readlength of a read |
| `--save-clipped-reads` | boolean |  |  |  |  |  | fastp option to define if the clipped reads should be saved |

## general_workflow_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--classification-bbduk` | boolean |  |  |  |  |  | Signifies that bbduk is used in the classification process. Can be combined with the 'classification_kraken2' parameter to run both. |
| `--classification-kraken2` | boolean |  |  |  |  |  | Signifies that kraken2 is used in the classification process. Can be combined with the 'classification_bbduk' parameter to run both. For kraken2 alone no parameter is needed. |
| `--classification-kraken2-post-filtering` | boolean |  |  |  |  |  | If the filtered reads should be classified with kraken2. |
| `--filter-trimmed` | boolean |  |  |  |  |  | If the pre-processed reads should be used by the filter. |
| `--filter-with-classification` | boolean |  |  |  |  |  | When a validation via blastn is wanted but the filtering should use the IDs from the classification process. |
| `--filtering-tool` | string |  |  | `seqkit`, `bbmap` |  | seqkit | Select the read-filtering tool: seqkit or bbmap. seqkit normalizes FASTQ headers by temporarily renaming them; bbmap uses filterbyname.sh for exact header matching -- Note: BBTools I/O forces any base that is N to Q=0 (!). |
| `--output-removed-reads` | boolean |  |  |  |  |  | If the removed reads should also be written to the output folder. |
| `--preprocessing` | boolean |  |  |  |  |  | If preprocessing with fastp should be turned on. |
| `--save-intermediates` | boolean |  |  |  |  |  | Save intermediates to the results folder. |
| `--skip-filter` | boolean |  |  |  |  |  | If the filtering step should be skipped. |
| `--validation-blastn` | boolean |  |  |  |  |  | If a validation of the classified reads via blastn should be carried out. |

## generate_samplesheet_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--generate-downstream-samplesheets` | boolean |  |  |  |  |  | Turn on generation of samplesheets for downstream pipelines. |
| `--generate-pipeline-samplesheets` | string |  |  |  | matches ^(taxprofiler\|mag)(?:,(taxprofiler\|mag)){0,1} | taxprofiler,mag | Specify a comma separated string in quotes to specify which pipeline to generate a samplesheet for. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
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
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## kraken2

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cutoff-tax2filter` | integer |  |  |  |  | 0 | If a read has less k-mers assigned to the taxon/taxa to be assessed/to be filtered the read is ignored by the pipeline. |
| `--cutoff-tax2keep` | number |  |  |  | ≥ 0; ≤ 1 | 0.0 | Ratio per read of assigned to tax2filter k-mers to k-mers assigned to any other taxon (except unclassified). |
| `--cutoff-unclassified` | number |  |  |  | ≥ 0; ≤ 1 | 0.0 | Ratio per read of assigned to tax2filter k-mers to unclassified k-mers. |
| `--kraken2confidence` | number |  |  |  |  | 0.0 | Confidence in the classification of a read as a certain taxon. |
| `--kraken2confidence-filtered` | number |  |  |  |  | 0.0 | Confidence in the classification of a read as a certain taxon. For the filtered reads. |
| `--kraken2confidence-removed` | number |  |  |  |  | 0.0 | Confidence in the classification of a read as a certain taxon. For the removed reads. |
| `--kraken2db` | string |  |  |  |  | https://genome-idx.s3.amazonaws.com/kraken/k2_standard_20240605.tar.gz | The database which is used in the classification step. Please be aware that this default database will require ~60GB download and ~80GB RAM. |
| `--save-output-fastqs` | boolean |  | yes |  |  |  | Save unclassified reads and classified reads (those assigned to any taxon, not specifically assessed or filtered) to separate files. |
| `--save-output-fastqs-filtered` | boolean |  |  |  |  |  | Save unclassified reads and classified reads (those assigned to any taxon, not specifically assessed or filtered) to separate files. For the filtered reads. |
| `--save-output-fastqs-removed` | boolean |  |  |  |  |  | Save unclassified reads and classified reads (those assigned to any taxon, not specifically assessed or filtered) to separate files. For the removed reads. |
| `--tax2filter` | string |  |  |  |  | Homo sapiens | The taxon or taxonomic group to be assessed or filtered by the pipeline. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome` | string |  |  |  |  | GRCh38 | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--saveReference` | boolean |  |  |  |  | true |  |

<!-- Generated from nf-core/detaxizer@3586921aa3a4c49271f1b2082309bdc33c819749. Do not edit by hand. -->
