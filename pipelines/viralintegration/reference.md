---
name: viralintegration
version: 0.1.1
commit: 70e558aaff836d43f5d662bf9c28414f4e6db642
---

# viralintegration — full parameter reference

nf-core/viralintegration pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  | false | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  | false | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--plaintext-email` | boolean |  | yes |  |  | false | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  | false | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  | false | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  | false | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  | false | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--max-hits` | integer | yes |  |  | ≥ 1 | 50 | Maximum hits |
| `--min-reads` | integer | yes |  |  | ≥ 1 | 5 | Minimum reads |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--remove-duplicates` | boolean | yes |  |  |  | true | To remove duplicate viral hits or not |
| `--viral-fasta` | string (file path) | yes |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ | https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/VIRUS_INSERTION_FINDING_LIB_SUPPLEMENT/virus_db.fasta | Path to fasta file with viral genomes |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | 16 | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 128.GB | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches ^(\d+\.?\s*(s\|m\|h\|d\|day)\s*)+$ | 240.h | Maximum amount of time that can be requested for any single job. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gtf` | string (file path) |  |  |  | matches ^\S+\.gtf(\.gz)?$ |  | Path to GTF annotation file. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

<!-- Generated from nf-core/viralintegration@70e558aaff836d43f5d662bf9c28414f4e6db642. Do not edit by hand. -->
