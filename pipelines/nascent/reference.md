---
name: nascent
version: 2.3.0
commit: 7d4fe61975015f652c271886e661764b05cfd3bf
---

# nascent — full parameter reference

nf-core/nascent pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `bwa`, `bwamem2`, `dragmap`, `bowtie2`, `hisat2`, `star` |  | `bwa` | Specify aligner to be used to map reads to reference genome. |
| `--skip-alignment` | boolean |  |  |  |  |  | Skip all of the alignment-based processes within the pipeline. |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip the adapter trimming step. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
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

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bowtie2-index` | string |  | yes |  |  |  | Path to bowtie2 indices. |
| `--bwa-index` | string |  |  |  |  |  | Path to BWA mem indices. |
| `--bwamem2-index` | string |  | yes |  |  |  | Path to bwa-mem2 mem indices. |
| `--dragmap` | string |  | yes |  |  |  | Path to dragmap indices. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--gene-bed` | string (file path) |  |  |  | matches `^\S+\.bed(\.gz)?$` |  | Path to BED file containing gene intervals. This will be created from the GTF file if not specified. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gff` | string (file path) |  |  |  | matches `^\S+\.gff(3)?(\.gz)?$` |  | Path to GFF3 annotation file. |
| `--gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Path to GTF annotation file. |
| `--hisat2-index` | string |  |  |  |  |  | Path to HISAT2 indices. |
| `--homer-uniqmap` | string |  | yes |  |  |  | Path to HOMER uniqmap file or URL to download. |
| `--human-pangenomics-base` | string |  | yes |  |  | `https://s3-us-west-2.amazonaws.com/human-pangenomics` | Directory / URL base for CHM13 references. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--save-reference` | boolean |  |  |  |  |  | If generated by the pipeline save the BWA index in the results directory. |
| `--star-index` | string |  |  |  |  |  | Path to STAR indices. |

## transcript_identification_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assay-type` | string | yes |  | `CoPRO`, `GROcap`, `PROcap`, `CAGE`, `NETCAGE`, `RAMPAGE`, `csRNAseq`, `STRIPEseq`, `PROseq`, `GROseq`, `R_5`, `R_3`, `R1_5`, `R1_3`, `R2_5`, `R2_3` |  |  | What type of nascent or TSS assay the sample is. |
| `--filter-bed` | string |  |  |  | matches `^\S+\.bed(\.gz)?$` |  | Undesired regions, that transcripts should not overlap with |
| `--grohmm-max-ltprobb` | integer |  |  |  |  | `-400` | Maximum LTProbB value to use for groHMM. |
| `--grohmm-max-uts` | integer |  |  |  |  | `45` | Maximum number of UTs to use for groHMM. |
| `--grohmm-min-ltprobb` | integer |  |  |  |  | `-100` | Minimum LTProbB value to use for groHMM. |
| `--grohmm-min-uts` | integer |  |  |  |  | `5` | Minimum number of UTs to use for groHMM. |
| `--intersect-bed` | string |  |  |  | matches `^\S+\.bed(\.gz)?$` |  | Desired regions, that transcripts should overlap with |
| `--skip-grohmm` | boolean |  |  |  |  | `false` | Skip groHMM all together |
| `--use-homer-uniqmap` | boolean |  | yes |  |  | `false` | Use HOMER uniqmap for transcript identification. |

## umi_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--umitools-dedup-stats` | boolean |  |  |  |  |  | Generate output stats when running "umi_tools dedup". |
| `--with-umi` | boolean |  |  |  |  |  | Enable UMI-based read deduplication. |

<!-- Generated from nf-core/nascent@7d4fe61975015f652c271886e661764b05cfd3bf. Do not edit by hand. -->
