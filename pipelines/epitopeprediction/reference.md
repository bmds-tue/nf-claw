---
name: epitopeprediction
version: 3.1.1
commit: 48f2eaaeb9b2226489d60a69ce1796c2db4642f2
---

# epitopeprediction — full parameter reference

nf-core/epitopeprediction pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## external_software

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--external-tools-meta` | string |  | yes |  |  |  | Specifies the path to the JSON file with meta information on external prediction tools. |
| `--netmhc-system` | string |  |  | `linux`, `darwin` |  | linux | Specifies the operating system in use (Linux or Darwin). This is only necessary if conda is used. |
| `--netmhciipan-path` | string (file path) |  |  |  | matches ^\S+\.tar\.gz$ |  | To use the 'netmhciipan' tool, specify the path to the original software tarball for NetMHCIIpan 3.1 here. |
| `--netmhcpan-path` | string (file path) |  |  |  | matches ^\S+\.tar\.gz$ |  | To use the 'netmhcpan' tool, specify the path to the original software tarball for NetMHCpan 4.0 here. |

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
| `--input` | string (file path) | yes |  |  |  |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## peptide_prediction_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--binder-only` | boolean |  |  |  |  | false | Filter out non-binders from the final results. |
| `--fasta-output` | boolean |  |  |  |  | false | Specifies that sequences of proteins, affected by provided variants, will be written to a FASTA file. |
| `--fasta-peptide-flanking-region-size` | integer |  | yes |  |  | 25 | Specifies the size of the flanking regions around a mutation in a peptide in the FASTA file (if `fasta_output` is set to `true`). |
| `--max-peptide-length-classI` | integer |  |  |  |  | 12 | Specifies the maximum peptide length. |
| `--max-peptide-length-classII` | integer |  |  |  |  | 25 | Specifies the maximum peptide length for MHC class II peptides. |
| `--min-peptide-length-classI` | integer |  |  |  |  | 8 | Specifies the minimum peptide length. |
| `--min-peptide-length-classII` | integer |  |  |  |  | 8 | Specifies the minimum peptide length for MHC class II peptides. |
| `--peptide-col-name` | string |  |  |  |  | sequence | Specifies the column name in the input file that contains the peptide sequences. |
| `--tools` | string |  |  |  |  | mhcnuggets | Specifies the prediction tool(s) to use. |
| `--wide-format-output` | boolean |  |  |  |  | false | Specifies that the output file will be in wide format. |
| `--wild-type` | boolean |  |  |  |  |  | Specifies whether wild-type sequences should be predicted. |

## reference_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome-reference` | string |  |  |  |  | grch37 | Specifies the Ensembl genome reference version that will be used. |
| `--proteome-reference` | string (file path) |  |  |  |  |  | Specifies the reference proteome fasta file that is used for self-filtering peptides derived from provided genomic variants. |

## run_optimisation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--peptides-split-maxchunks` | integer |  |  |  |  | 100 | Specifies the maximum number of peptide chunks. |
| `--peptides-split-minchunksize` | integer |  |  |  |  | 5000 | Specifies the minimum number of peptides that should be written into one chunk. |
| `--split-by-variants` | boolean |  |  |  |  |  | Split VCF file into multiple files by number of variants. |
| `--split-by-variants-distance` | integer |  | yes |  |  | 110000 | Number of nucleotides between previous and current variant across split. |
| `--split-by-variants-size` | integer |  | yes |  |  | 0 | Number of variants that should be written into one file. Default: number of variants divided by ten |

<!-- Generated from nf-core/epitopeprediction@48f2eaaeb9b2226489d60a69ce1796c2db4642f2. Do not edit by hand. -->
