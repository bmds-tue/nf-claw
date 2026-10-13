---
name: pairgenomealign
version: 3.0.4
commit: 8ee09a1cdc920fc90cd62358952045e5019e1fe0
---

# pairgenomealign — full parameter reference

nf-core/pairgenomealign pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--last-split-mismap` | string |  |  |  |  | 1e-05 | Mismap probability cutoff for `last-split`. |
| `--lastal-args` | string |  |  |  |  | -C2 -D1e9 | Arguments passed to both `last-train` and `lastal`. |
| `--lastal-extr-args` | string |  |  |  |  |  | Arguments passed only to `lastal` (useful when they are not recognised by `last-train`). |
| `--lastal-params` | string |  |  |  |  |  | Path to a file containing alignment parameters or a scoring matrix. If this option is used, `last-train` will be skipped and alignment parameters will be the same for each query. |
| `--m2m` | boolean |  |  |  |  |  | Make a many to many alignment |

## dotplot_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dotplot-filter` | boolean |  |  |  |  |  | Remove isolated alignments with the `maf-filter` tool. |
| `--dotplot-font-size` | integer |  |  |  |  | 14 | Font size of the sequence names on the dot plots. |
| `--dotplot-height` | integer |  |  |  |  | 10000 | Maximum height of the dot plots, in pixels. |
| `--dotplot-options` | string |  |  |  |  |  | Extra arguments passed to `last-dotplot` to customise the output. See <https://gitlab.com/mcfrith/last/-/blob/main/doc/last-dotplot.rst>. |
| `--dotplot-width` | integer |  |  |  |  | 1200 | Maximum width of the dot plots, in pixels. |
| `--multiqc-thumbs` | integer |  |  |  | ≥ 0 | 0 | Size of the alignments thumbnails in MultiQC (default 0 turns it off; 100 is a good value to start with). |
| `--skip-dotplot-m2m` | boolean |  |  |  |  |  | Do not generate the many-to-many alignment dot-plot. |
| `--skip-dotplot-m2o` | boolean |  |  |  |  |  | Do not generate the many-to-one alignment dot-plot. |
| `--skip-dotplot-o2m` | boolean |  |  |  |  |  | Do not generate the one-to-many alignment dot-plot. |
| `--skip-dotplot-o2o` | boolean |  |  |  |  |  | Do not generate the one-to-one alignment dot-plot. |

## export_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--export-aln-to` | string |  |  |  | matches ^((no_export\|axt\|bam\|bcf\|bed\|blast\|blasttab\|blasttab\+\|chain\|cram\|gff\|html\|psl\|sam\|tab)?,?)*(?<!,)$ | no_export | Convert the final _one-to-one_ alignment to a different format than MAF. |
| `--multi-cram` | boolean |  |  |  |  |  | Produce a multi-query CRAM file combining all the alignments. |

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

## indexing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--seed` | string |  |  | `YASS`, `NEAR`, `MAM4`, `MAM8`, `RY4`, `RY8`, `RY16`, `RY32`, `RY64`, `RY128` |  | RY4 | Select the LAST seed to index the _target_ genome. |
| `--softmask` | string |  |  | `tantan`, `original` |  | tantan | Customise the way to mask the _target_ genome. |
| `--strand` | string |  |  | `both`, `forward` |  | both | Index both strand, or just one. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--query` | string |  |  |  | matches ^\S+\.fn?(a\|q)(sta\|stq)?(\.gz)?$ |  | Path or URL to a FASTA genome file for the _query_ genome. |
| `--queryName` | string |  |  |  |  | query | Query genome name. |
| `--skip-assembly-qc` | boolean |  |  |  |  | false | Skip assembly QC. |
| `--target` | string (file path) | yes |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path or URL to a FASTA genome file for the _target_ genome. |
| `--targetName` | string |  |  |  |  | target | Target genome name. |

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
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

<!-- Generated from nf-core/pairgenomealign@8ee09a1cdc920fc90cd62358952045e5019e1fe0. Do not edit by hand. -->
