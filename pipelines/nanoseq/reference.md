---
name: nanoseq
version: 3.1.0
commit: 6e563e54362cddb8e48d15c156251708c22d0e8d
---

# nanoseq — full parameter reference

nf-core/nanoseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  |  |  | `minimap2` | Specifies the aligner to use i.e. 'minimap2' or 'graphmap2'. |
| `--save-align-intermeds` | boolean |  |  |  |  |  | Save the '.sam' files from the alignment step - not done by default. |
| `--skip-alignment` | boolean |  |  |  |  |  | Skip alignment and downstream processes. |
| `--stranded` | boolean |  |  |  |  |  | Specifies if the data is strand-specific. Automatically activated when using '--protocol directRNA'. |

## demultiplexing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--barcode-both-ends` | boolean |  |  |  |  |  | Require barcode on both ends for basecaller. |
| `--barcode-kit` | string |  |  |  |  |  | Barcode kit used to perform the sequencing e.g. 'SQK-PBK004'. |
| `--gpu-cluster-options` | string |  |  |  |  |  | Cluster options required to use GPU resources (e.g. '--part=gpu --gres=gpu:1'). |
| `--gpu-device` | string |  |  |  |  | `auto` | Device specified in GPU mode using '--device'. |
| `--input-path` | string (file path) |  |  |  |  |  | Path to Nanopore run directory files (e.g. 'fastq_pass/*') or a basecalled fastq file that requires demultiplexing. |
| `--nanolyse-fasta` | string |  |  |  |  |  | Fasta file to be filtered against using NanoLyse |
| `--qcat-detect-middle` | boolean |  |  |  |  |  | Search for adapters in the whole read by applying the '--detect-middle' parameter in qcat. |
| `--qcat-min-score` | integer |  |  |  |  | `60` | Specify the minimum quality score for qcat in the range 0-100. |
| `--run-nanolyse` | boolean |  |  |  |  |  | Filter reads from FastQ files using NanoLyse |
| `--skip-demultiplexing` | boolean |  |  |  |  |  | Skip demultiplexing with qcat. |
| `--trim-barcodes` | boolean |  |  |  |  |  | Trim barcodes from the output sequences in the FastQ files from basecaller. |

## differential_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--quantification-method` | string |  |  |  |  | `bambu` | Specifies the transcript quantification method to use (available are: bambu or stringtie2). Only available when protocol is cDNA or directRNA. |
| `--skip-differential-analysis` | boolean |  |  |  |  |  | Skip differential analysis with DESeq2 and DEXSeq. |
| `--skip-quantification` | boolean |  |  |  |  |  | Skip transcript quantification and differential analysis. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--show-hidden-params` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--tracedir` | string |  | yes |  |  | `${params.outdir}/pipeline_info` | Directory to keep pipeline Nextflow logs and reports. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` | `./samplesheet.csv` | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) |  |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--protocol` | string | yes |  |  |  |  | Input sample type. Valid options: 'DNA', 'cDNA', and 'directRNA'. |

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
| `--max-time` | string |  | yes |  | matches `^(\d+\.?\s*(s\|m\|h\|day)\s*)+$` | `240.h` | Maximum amount of time that can be requested for any single job. |

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-bigbed` | boolean |  |  |  |  |  | Skip BigBed file generation. |
| `--skip-bigwig` | boolean |  |  |  |  |  | Skip BigWig file generation. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-nanoplot` | boolean |  |  |  |  |  | Skip NanoPlot. |
| `--skip-qc` | boolean |  |  |  |  |  | Skip all QC steps apart from MultiQC. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes` | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

## rna_fusion_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--jaffal-ref-dir` | string |  |  |  |  | `for_jaffal` | Specifies the reference directory for JAFFAL. |
| `--skip-fusion-analysis` | boolean |  |  |  |  |  | Skip differential analysis with DESeq2 and DEXSeq. |

## rna_modification_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-m6anet` | boolean |  |  |  |  |  | Skip m6A detection with m6anet. |
| `--skip-modification-analysis` | boolean |  |  |  |  |  | Skip RNA modification analysis. |
| `--skip-xpore` | boolean |  |  |  |  |  | Skip differential modification analysis with xpore. |

## variant_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--call-variants` | boolean |  |  |  |  |  | Specifies if variant calling will executed. |
| `--deepvariant-gpu` | boolean |  |  |  |  |  | Specifies whether to call variants with pepper_margin_deepvariant in GPU mode. |
| `--phase-vcf` | boolean |  |  |  |  |  | Specifies if vcf will be phased when using medaka. |
| `--skip-sv` | boolean |  |  |  |  |  | Skip structural variant calling. |
| `--skip-vc` | boolean |  |  |  |  |  | Skip variant calling. |
| `--split-mnps` | boolean |  |  |  |  |  | Specifies if MNPs will be split into SNPs when using medaka. |
| `--structural-variant-caller` | string |  |  |  |  | `sniffles` | Specifies the variant caller that will be used to call structural variants (available are: sniffles and cutesv). Structural variant calling is only available if '--call_variants' is set and the protocol is set to `DNA`. |
| `--variant-caller` | string |  |  |  |  | `medaka` | Specifies the variant caller that will used to call small variants (available are: medaka, deepvariant, and pepper_margin_deepvariant). Variant calling is only available if '--call_variants' is set and the protocol is set to `DNA`. Please note `deepvariant` and `pepper_margin_deepvariant` are only avaible if using singularity or docker. |

<!-- Generated from nf-core/nanoseq@6e563e54362cddb8e48d15c156251708c22d0e8d. Do not edit by hand. -->
