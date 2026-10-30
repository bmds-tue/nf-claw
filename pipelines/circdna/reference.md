---
name: circdna
version: 1.1.0
commit: 8e0e14c84f90c94d975c2bac6bde8e5a1d5bc8ab
---

# circdna — full parameter reference

nf-core/circdna pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## amplicon_architect_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aa-cngain` | string |  |  |  |  | `4.5` | Copy Number Threshold for seeds to be considered by AmpliconArchitect. |
| `--aa-data-repo` | string (directory path) |  |  |  |  |  | Absolute path to the downloaded AA data repository. See [AmpliconArchitect](https://github.com/jluebeck/AmpliconArchitect). |
| `--cnvkit-cnn` | string |  |  |  |  |  | Path to cnn file inside the AmpliconArchitect Data Repository of the respective reference genome. By default it uses the 'aa_data_repo' and the 'reference_build' input to construct the file path. |
| `--mosek-license-dir` | string (directory path) |  |  |  |  |  | Path to the directory containing the mosek license file 'mosek.lic'. |
| `--reference-build` | string |  |  |  |  |  | When running AmpliconArchitect, specify reference build ['GRCh37', 'GRCh38', 'mm10']. This is *mandatory* to match fasta and AA reference build! |

## circdna_identifier_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--circle-identifier` | string | yes |  |  |  |  | Specifies the circular DNA identification algorithm to use - available 'circle_map_realign', 'circle_map_repeats', 'circle_finder', 'circexplorer2', and 'ampliconarchitect'. Multiple circle_identifier's can be specified with a comma-separated string. E.g. `--circle_identifier 'circle_map_realign,unicycler'`. |

## circle_finder_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-circle-finder-intermediate` | boolean |  |  |  |  | `false` | Store bed files created during Circle_finder run. |

## circle_map_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-circle-map-intermediate` | boolean |  |  |  |  | `false` | Store bam file with read candidates for circle-map circular dna calling. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
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
| `--bam-sorted` | boolean |  |  |  |  |  | Specify if bam file is sorted [false, true]. If false or not specified, bam file will be sorted! |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--input-format` | string | yes |  |  |  |  | Specify input format. Default *FASTQ*. Options 'FASTQ' or 'BAM'. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-sorted-bam` | boolean |  |  |  |  |  | Specify if sorted bam file should be saved [false, true]. Default: false |

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

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--keep-duplicates` | boolean |  |  |  |  | `true` | Keep read duplications marked by picard MarkDuplicates. |
| `--save-markduplicates-bam` | boolean |  |  |  |  | `true` | Store bam with marked duplicate reads. |
| `--skip-markduplicates` | boolean |  |  |  |  | `false` | Skip Picard MarkDuplicates and duplicate filtering |
| `--skip-multiqc` | boolean |  |  |  |  | `false` | Skip MultiQC step. |
| `--skip-qc` | boolean |  |  |  |  | `false` | Skip all QC steps except for MultiQC. |

## read_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 2 (paired-end reads only). |
| `--save-merged-fastq` | boolean |  |  |  |  | `false` | Save the merged FastQ files in the results directory. |
| `--save-trimmed` | boolean |  |  |  |  | `false` | Save the trimmed FastQ files in the results directory. |
| `--skip-trimming` | boolean |  |  |  |  | `false` | Skip the adapter trimming step. |
| `--three-prime-clip-r1` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--three-prime-clip-r2` | integer |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 2 AFTER adapter/quality trimming has been performed. |
| `--trim-nextseq` | integer |  |  |  |  |  | Instructs Trim Galore to apply the --nextseq=X option, to trim based on quality after removing poly-G tails. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bwa-index` | string (directory path) |  |  |  |  |  | Path to the directory containg the BWA index files. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--save-reference` | boolean |  |  |  |  | `false` | Save the index reference fasta in the results directory. |

## unicycler_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-unicycler-intermediate` | boolean |  |  |  |  | `false` | Store fastq intermediate files created during Uniycler run. |

<!-- Generated from nf-core/circdna@8e0e14c84f90c94d975c2bac6bde8e5a1d5bc8ab. Do not edit by hand. -->
