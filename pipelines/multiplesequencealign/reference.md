---
name: multiplesequencealign
version: 1.1.1
commit: 79724dac3d240b9bb7684532d3fe238b42f6a4b4
---

# multiplesequencealign — full parameter reference

nf-core/multiplesequencealign pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## align_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--build-consensus` | boolean |  |  |  |  |  | Build consensus alignment with M-COFFEE. |

## eval_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--calc-gaps` | boolean |  |  |  |  | `true` | Extract total number of gaps and average number of gaps of the alignment. |
| `--calc-irmsd` | boolean |  |  |  |  |  | Calculate the iRMSD of alignment. |
| `--calc-sp` | boolean |  |  |  |  | `true` | Calculate the Sum of Pairs of alignment. |
| `--calc-tc` | boolean |  |  |  |  | `true` | Calculate the Total Column Score of alignment. |
| `--calc-tcs` | boolean |  |  |  |  |  | Calculate the Transitive Consistency Score (TCS) of alignment. |
| `--skip-eval` | boolean |  |  |  |  |  | Skip all of the evaluations computation on the msa. |

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

## global_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-compression` | boolean |  |  |  |  |  | Produce uncompressed alignment files |
| `--skip-pdbconversion` | boolean |  |  |  |  |  | Skip the conversion of pdb files to fasta. |
| `--skip-preprocessing` | boolean |  |  |  |  |  | Skip the preprocessing step for the input files. |
| `--skip-validation` | boolean |  |  |  |  |  | Skip the validation of the input files. |
| `--use-gpu` | boolean |  |  |  |  |  | Run on CPUs (default) or GPUs |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches `^\S+\.(csv\|tsv\|yaml\|yml\|json)$` |  | Path to the samplesheet file containing information about datasets to be aligned and evaluated (samplesheet). |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--pdbs-dir` | string (file or directory path) |  |  |  |  |  | Path to a folder containing all the optional data files to be used (e.g. structures). |
| `--seqs` | string (file path) |  |  |  | matches `\S+\.f(n\|ast)?a$` |  | Path to the input fasta file. |
| `--templates-suffix` | string |  |  |  |  | `.pdb` | Suffix of the files given in the optional_data directory. |

## input_tools_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `CLUSTALO`, `FAMSA`, `KALIGN`, `LEARNMSA`, `MAFFT`, `MAGUS`, `MUSCLE5`, `TCOFFEE`, `REGRESSIVE`, `UPP`, `3DCOFFEE`, `MTMALIGN`, `FOLDMASON` |  |  | The aligner to be used. |
| `--args-aligner` | string |  |  |  |  |  | Extra arguments for the aligner tool. |
| `--args-tree` | string |  |  |  |  |  | Extra arguments for the tree building tool. |
| `--tools` | string (file path) |  |  |  | matches `^\S+\.(csv\|tsv\|yaml\|yml\|json)$` |  | Path to the file containing information about the tools to be deployed (toolsheet). |
| `--tree` | string |  |  | `FAMSA`, `CLUSTALO`, `MAFFT` |  |  | Tool to use for tree building. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## reports_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--shiny-app` | string (directory path) |  |  |  |  |  | Folder containing the main shiny app. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip the multiqc report generation. |
| `--skip-shiny` | boolean |  |  |  |  |  | Skip the shiny report generation. |
| `--skip-visualisation` | boolean |  |  |  |  |  | Skip the visualization generation. |

## stats_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--calc-seq-stats` | boolean |  |  |  |  |  | Calculate general statistics on input files. |
| `--calc-sim` | boolean |  |  |  |  |  | Calculate the percentage similarity across the sequences in the input files. |
| `--extract-plddt` | boolean |  |  |  |  |  | Extract plddt from structure files. Only works if the files have been generated by AF2. |
| `--skip-stats` | boolean |  |  |  |  |  | Skip all of the statistics computation on the fasta file. |

<!-- Generated from nf-core/multiplesequencealign@79724dac3d240b9bb7684532d3fe238b42f6a4b4. Do not edit by hand. -->
