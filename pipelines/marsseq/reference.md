---
name: marsseq
version: 1.0.3
commit: b02ede773092f8a8a5999400acda6894d51b4d26
---

# marsseq — full parameter reference

nf-core/marsseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  | `false` | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  | `false` | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--plaintext-email` | boolean |  | yes |  |  | `false` | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  | `false` | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  | `false` | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  | `false` | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  | `false` | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--build-references` | boolean |  |  |  |  |  | Specifies which analysis type for the pipeline - either build references or analyse data |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--genomes-base` | string (directory path) |  | yes |  |  |  | Directory for Genomes references. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

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

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bowtie2-index` | string (directory path) |  |  |  |  |  | Path to BOWTIE2 index. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  | `mm10` | Name of Genomes reference. |
| `--gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Path to GTF annotation file. |
| `--star-index` | string (directory path) |  |  |  |  |  | Path to STAR index. |

## rna_velocity

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--read-length` | integer |  |  |  |  |  | Read length required for STAR aligner |
| `--velocity` | boolean |  |  |  |  | `false` | Run RNA velocity |

## skip_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-qc` | boolean |  |  |  |  |  | Skip QC steps |

<!-- Generated from nf-core/marsseq@b02ede773092f8a8a5999400acda6894d51b4d26. Do not edit by hand. -->
