---
name: crisprseq
version: 2.3.0
commit: 0e9f915c4a3c89d02a66ec58e2decbc832323c8b
---

# crisprseq — full parameter reference

nf-core/crisprseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string (file path) |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string (file path) |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--analysis` | string | yes |  | `screening`, `targeted` |  |  | Type of analysis to perform. Targeted for targeted CRISPR experiments and screening for CRISPR screening experiments. |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--reference-fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to the reference FASTA file. Will override reference sequences provided by an input sample sheet. |

## screening_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bagel2` | boolean |  |  |  |  |  | Parameter indicating if BAGEL2 should be run |
| `--bagel-reference-essentials` | string |  |  |  |  | https://raw.githubusercontent.com/hart-lab/bagel/master/CEGv2.txt | Core essential gene set for BAGEL2 |
| `--bagel-reference-nonessentials` | string |  |  |  |  | https://raw.githubusercontent.com/hart-lab/bagel/master/NEGv1.txt | Non essential gene set for BAGEL2 |
| `--contrasts` | string (file path) |  |  |  |  |  | Comma-separated file with the conditions to be compared. The first one will be the reference (control) |
| `--count-table` | string (file path) |  |  |  | matches ^\S+\.(tsv\|txt)$ |  | Please provide your count table if the mageck test should be skipped. |
| `--crisprcleanr` | string |  |  |  |  |  | sgRNA library annotation for crisprcleanR |
| `--day0-label` | string |  |  |  |  |  | Specify the label for control sample (usually day 0 or plasmid). For every other sample label, the module will treat it as a treatment condition and compare with control sample for MAGeCK MLE |
| `--drugz` | boolean (file path) |  |  |  |  |  | Parameter indicating if DrugZ should be run |
| `--drugz-remove-genes` | string |  |  |  | matches \\S+ |  | Essential genes to remove from the drugZ modules |
| `--fasta` | string |  |  |  |  |  | Library in fasta file format in case you want to map with bowtie2 and then MAGeCK count |
| `--five-prime-adapter` | string |  |  |  |  |  | Sequencing adapter sequence to use for trimming on the 5' end |
| `--hit-selection-iteration-nb` | number |  |  |  |  | 1000 | Number of iterations the hit selection module should provide |
| `--hitselection` | boolean |  |  |  |  |  | Specify to run the Hitselection algorithm |
| `--library` | string (file path) |  |  |  | matches ^\S+\.(tsv\|txt)$ |  | sgRNA and targetting genes, tab separated |
| `--min-reads` | number |  |  |  |  | 30 | a filter threshold value for sgRNAs, based on their average counts in the control sample |
| `--min-targeted-genes` | number |  |  |  |  | 3 | Minimal number of different genes targeted by sgRNAs in a biased segment in order for the corresponding counts to be corrected for CRISPRcleanR |
| `--mle` | boolean |  |  |  |  |  | Parameter indicating if MAGeCK MLE should be run |
| `--mle-control-sgrna` | string |  |  |  |  |  | control-sgrna file for MAGeCK MLE |
| `--mle-design-matrix` | string (file path) |  |  |  |  |  | Design matrix used for MAGeCK MLE to call essential genes under multiple conditions while considering sgRNA knockout efficiency |
| `--rra` | boolean |  |  |  |  |  | Parameter indicating if MAGeCK RRA should be run instead of MAGeCK MLE. |
| `--three-prime-adapter` | string |  |  |  |  |  | Sequencing adapter sequence to use for trimming on the 3' end |

## targeted_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `minimap2`, `bwa`, `bowtie2` |  | minimap2 | Aligner program to use. |
| `--protospacer` | string |  |  |  | matches ^[ACGTacgt]+$ |  | Provide the same protospacer sequence for all samples. Will override protospacer sequences provided by an input samplesheet. |

## targeted_pipeline_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--overrepresented` | boolean |  |  |  |  |  | Trim overrepresented sequences from reads (cutadapt) |
| `--skip-clonality` | boolean |  |  |  |  |  | Skip the classification of samples by clonality. |
| `--umi-clustering` | boolean |  |  |  |  |  | If the sample contains umi-molecular identifyers (UMIs), run the UMI extraction, clustering and consensus steps. |

## umi_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--medaka-model` | string |  |  |  |  | https://github.com/nanoporetech/medaka/raw/master/medaka/data/r941_min_high_g303_model.hdf5 | Medaka model (-m) to use according to the basecaller used. |
| `--umi-bin-size` | integer |  |  |  |  | 1 | Minimum size of a UMI cluster. |

## vsearch_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--vsearch-id` | number |  |  |  | ≥ 0; ≤ 1 | 0.99 | Vsearch pairwise identity threshold. |
| `--vsearch-maxseqlength` | integer |  |  |  | ≥ 1 | 57 | Vsearch maximum sequence length. |
| `--vsearch-minseqlength` | integer |  |  |  | ≥ 1 | 55 | Vsearch minimum sequence length. |

<!-- Generated from nf-core/crisprseq@0e9f915c4a3c89d02a66ec58e2decbc832323c8b. Do not edit by hand. -->
