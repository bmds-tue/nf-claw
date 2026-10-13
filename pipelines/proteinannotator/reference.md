---
name: proteinannotator
version: 1.1.0
commit: cbf78d471f62d91af666e8c77bcd580b4743c6be
---

# proteinannotator — full parameter reference

nf-core/proteinannotator pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## domain_annotation_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--funfam-db` | string (file path) |  |  |  |  |  | Path to an already installed FunFam HMM database (.lib.gz). |
| `--funfam-latest-link` | string |  |  |  |  | https://download.cathdb.info/cath/releases/all-releases/v4_3_0/sequence-data/funfam-hmm3-v4_3_0.lib.gz | CATH hosted link to the latest available (v4_3_0) FunFam HMM database file. |
| `--hmmsearch-evalue-cutoff` | number |  |  |  |  | 0.001 | hmmsearch e-value cutoff threshold for reported results. Modifies the -E parameter of hmmsearch. |
| `--metagroot-db` | string (file path) |  |  |  |  |  | Path to an already installed metagRoot HMM database (.hmm.gz). |
| `--metagroot-latest-link` | string |  |  |  |  | https://pavlopoulos-lab.org/envofams/databases/hmmer/metagroot.hmm.gz | metagRoot hosted link to the latest available metagRoot HMM database file. |
| `--nmpfams-db` | string (file path) |  |  |  |  |  | Path to an already installed NMPFams HMM database. |
| `--nmpfams-latest-link` | string |  |  |  |  | https://pavlopoulos-lab.org/envofams/databases/hmmer/nmpfamsdb.hmm.gz | NMPFams hosted link to the latest NMPFams HMM database file. |
| `--pfam-db` | string (file path) |  |  |  |  |  | Path to an already installed Pfam HMM database (.hmm.gz). |
| `--pfam-latest-link` | string |  |  |  |  | https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz | InterPro hosted link to the latest Pfam HMM database file. |
| `--skip-funfam` | boolean |  |  |  |  |  | Skip the domain annotation with the FunFam database. |
| `--skip-metagroot` | boolean |  |  |  |  |  | Skip the domain annotation with the metagRoot database. |
| `--skip-nmpfams` | boolean |  |  |  |  |  | Skip the domain annotation with the NMPFams database. |
| `--skip-pfam` | boolean |  |  |  |  |  | Skip the domain annotation with the Pfam database. |

## functional_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--interproscan-applications` | string |  |  |  | matches ^\w+(,\w+)* | Hamap,PANTHER,PIRSF,TIGRFAM,sfld | Assigns the database(s) to be used to annotate the coding regions. |
| `--interproscan-db` | string |  |  |  |  |  | Path to pre-downloaded InterProScan database. |
| `--interproscan-db-url` | string |  |  |  |  | https://ftp.ebi.ac.uk/pub/software/unix/iprscan/5/5.72-103.0/interproscan-5.72-103.0-64-bit.tar.gz | Change the database version used for annotation. |
| `--interproscan-enableprecalc` | boolean |  |  |  |  |  | Pre-calculates residue mutual matches. |
| `--skip-interproscan` | boolean |  |  |  |  |  | Skip the functional annotation with InterProScan. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  |  |  |  |  | Base URL or local path to location of modules test dataset files |
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

## prediction_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--s4pred-outfmt` | string |  |  | `ss2`, `fas`, `horiz` |  | ss2 | Choose the output format (i.e., 'ss2', 'fas', 'horiz') for the s4pred per amino acid probability predictions (i.e., α-helix, β-strand, coil). Modifies the --outfmt parameter of s4pred run_model. |
| `--skip-s4pred` | boolean |  |  |  |  |  | Skip the secondary structure prediction. |

## quality_check_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-seq-length` | integer |  |  |  |  | 5000 | The maximum allowed sequence length |
| `--min-seq-length` | integer |  |  |  |  | 30 | The minimum allowed sequence length |
| `--remove-duplicates-on-sequence` | boolean |  |  |  |  |  | Remove duplicate input amino acid sequences, based on the sequence. |
| `--skip-preprocessing` | boolean |  |  |  |  |  | Skip all default QC steps for sequences (gap trimming, length filtering, validation, duplicate removal). |

<!-- Generated from nf-core/proteinannotator@cbf78d471f62d91af666e8c77bcd580b4743c6be. Do not edit by hand. -->
