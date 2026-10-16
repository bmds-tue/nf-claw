---
name: epitopeprediction
version: 3.2.0
commit: e637bc7c49e6e05a09f5207501a142ec68d8570b
---

# epitopeprediction — full parameter reference

nf-core/epitopeprediction pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## external_software

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--accept-mixmhcpred-license` | boolean |  |  |  |  | false | Confirm that you have read the MixMHCpred and MixMHC2pred licenses and use them for academic non-commercial research only. |
| `--external-tools-meta` | string |  | yes |  |  |  | Specifies the path to the JSON file with meta information on external prediction tools. |
| `--netmhciipan-path` | string (file path) |  |  |  | matches ^\S+\.tar\.gz$ |  | To use the 'netmhciipan' tool, specify the path to the original Linux software tarball for NetMHCIIpan 4.3 here. |
| `--netmhcpan-path` | string (file path) |  |  |  | matches ^\S+\.tar\.gz$ |  | To use the 'netmhcpan' tool, specify the path to the original Linux software tarball for NetMHCpan 4.2 here. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
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
| `--max-peptide-length-classI` | integer |  |  |  |  | 12 | Specifies the maximum peptide length for MHC class I peptides. |
| `--max-peptide-length-classII` | integer |  |  |  |  | 25 | Specifies the maximum peptide length for MHC class II peptides. |
| `--min-peptide-length-classI` | integer |  |  |  |  | 8 | Specifies the minimum peptide length for MHC class I peptides. |
| `--min-peptide-length-classII` | integer |  |  |  |  | 8 | Specifies the minimum peptide length for MHC class II peptides. |
| `--mutation-flanking-aas` | integer |  |  |  |  | 25 | Number of amino acids flanking the mutation on each side in the published variant protein FASTA (`variant_fasta/`); frameshifts run to the new stop. |
| `--peptide-col-name` | string |  |  |  |  | sequence | Specifies the column name in the input file that contains the peptide sequences. |
| `--proteome-reference` | string (file path) |  |  |  |  |  | Optional reference proteome FASTA for self-filtering variant peptides. |
| `--tools` | string |  |  |  |  | mhcnuggets | Specifies the prediction tool(s) to use. |
| `--use-ba-rank` | boolean |  | yes |  |  | false | Use BA_Rank instead of EL_Rank for netMHCpan and netMHCIIpan predictions. |
| `--wide-format-output` | boolean |  |  |  |  | false | Specifies that the output file will be in wide format. |
| `--wild-type` | boolean |  |  |  |  | false | Also predict the wild-type counterparts of variant peptides. |

## reference_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ref-fasta` | string (file path) |  |  |  |  |  | Reference genome FASTA matching the build (Ensembl primary assembly, contigs 1..MT), plain or bgzipped, with a .fai (and .gzi) index alongside. Required for variant (VCF) input unless --vep_download_cache is set. |
| `--vep-cache` | string (file or directory path) |  |  |  |  |  | Path to the VEP offline Ensembl cache. Either the cache directory or a `.tar.gz` of it. Required for variant input unless --vep_download_cache is set. |
| `--vep-cache-version` | integer |  |  |  |  |  | VEP cache version, matching the downloaded cache (e.g. 116). Required for variant input. |
| `--vep-download-cache` | boolean |  |  |  |  |  | Download the VEP cache and reference FASTA in-pipeline instead of providing --vep_cache/--ref_fasta. |
| `--vep-genome` | string |  |  |  |  |  | VEP assembly, matching the cache (e.g. GRCh38, GRCm39). Required for variant input. |
| `--vep-species` | string |  |  |  |  |  | VEP species, matching the cache (e.g. homo_sapiens, mus_musculus). Required for variant input. |

## run_optimisation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--peptides-split-maxchunks` | integer |  |  |  |  | 100 | Specifies the maximum number of peptide chunks. |
| `--peptides-split-minchunksize` | integer |  |  |  |  | 5000 | Specifies the minimum number of peptides that should be written into one chunk. |

<!-- Generated from nf-core/epitopeprediction@e637bc7c49e6e05a09f5207501a142ec68d8570b. Do not edit by hand. -->
