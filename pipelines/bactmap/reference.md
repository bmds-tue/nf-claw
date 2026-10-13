---
name: bactmap
version: 1.0.0
commit: 834642d8ac150ca10d705833223e7bcf15efc210
---

# bactmap — full parameter reference

nf-core/bactmap pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## compulsory_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--reference` | string | yes |  |  |  |  | Path to a fasta file of the reference sequence |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--enable-conda` | boolean |  |  |  |  |  | enable conda rather than use containers |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--max-multiqc-email-size` | string |  | yes |  |  | 25.MB | NOT USED: File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-title` | string |  | yes |  |  |  | Custom title for the MultiQC report. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden-params` | boolean |  |  |  |  |  | Show all params when using `--help` |
| `--singularity-pull-docker-container` | boolean |  | yes |  |  |  | Instead of directly downloading Singularity images for use with Singularity, force the workflow to pull and convert Docker containers instead. |
| `--skip-multiqc` | boolean |  | yes |  |  |  | NOT USED: Skip MultiQC |
| `--tracedir` | string |  | yes |  |  | ${params.outdir}/pipeline_info | Directory to keep pipeline Nextflow logs and reports. |
| `--validate-params` | boolean |  |  |  |  | true | Boolean whether to validate parameters against the schema at runtime |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string | yes |  |  |  |  | Path to a sample sheet describing paths to input fastq files |
| `--outdir` | string |  |  |  |  | ./results | The output directory where the results will be saved. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |
| `--hostnames` | string |  | yes |  |  |  | Institutional configs hostname. |

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | 4 | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches ^[\d\.]+\s*.(K\|M\|G\|T)?B$ | 16.GB | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches ^[\d\.]+\.*(s\|m\|h\|d)$ | 240.h | Maximum amount of time that can be requested for any single job. |

## optional_pipeline_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adapter-file` | string |  |  |  |  | ${baseDir}/assets/adapters.fas | path to file containing adapters in fasta format |
| `--fasttree` | boolean |  |  |  |  |  | Build a tree using the FastTree approximate ML algorithm |
| `--genome-size` | string |  |  |  |  |  | Specify genome size for subsampling rather than estimation using mash sketch |
| `--iqtree` | boolean |  |  |  |  |  | Build a tree using the IQ-TREE ML algorithm |
| `--non-GATC-threshold` | number |  |  |  |  | 0.5 | Maximum non GATC bases (i.e - and N) to allow in pseudogenome sequences |
| `--rapidnj` | boolean |  |  |  |  |  | Build a tree using the RapidNJ neighbour-joining algorithm |
| `--raxmlng` | boolean |  |  |  |  |  | Build a tree using the RAxML-NG ML algorithm |
| `--remove-recombination` | boolean |  |  |  |  |  | Remove recombination using gubbins |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | Saved failed read files after trimminng |
| `--subsampling-depth-cutoff` | integer |  |  |  |  | 100 | Desired coverage depth when subsampling |
| `--subsampling-off` | boolean |  |  |  |  |  | Turn off subsampling |
| `--trim` | boolean |  |  |  |  | true | Trim reads |

<!-- Generated from nf-core/bactmap@834642d8ac150ca10d705833223e7bcf15efc210. Do not edit by hand. -->
