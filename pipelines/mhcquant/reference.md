---
name: mhcquant
version: 3.3.0
commit: a4b6d51803af0fbde5acd8e9802df76280ba8306
---

# mhcquant — full parameter reference

nf-core/mhcquant pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## database_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string |  |  |  | matches `.fasta$` |  | Input FASTA protein database |
| `--skip-decoy-generation` | boolean |  |  |  |  | `false` | Add this parameter when you want to skip the generation of the decoy database. |

## epicore_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--epicore` | boolean |  |  |  |  | `false` | Compute core epitopes from overlapping peptides. |
| `--epicore-max-step-size` | integer |  |  |  |  | `5` | Specify the maximal difference between the start position of two peptides so they are still grouped together. |
| `--epicore-min-epi-length` | integer |  |  |  |  | `11` | Specify the minimal length of an core epitope. |
| `--epicore-min-overlap` | integer |  |  |  |  | `11` | Specify the minimal overlap of two peptides so they are grouped together. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  | `false` | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  | `false` | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  | `false` | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string | yes |  |  | matches `^(PXD\d{6,}\|\S+\.sdrf\.tsv\|\S+\.tsv)$` |  | Input: samplesheet TSV, SDRF file (.sdrf.tsv), or PRIDE accession (PXD...) |
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

## post_processing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotate-ions` | boolean |  |  |  |  | `false` | Create tsv files containing information about the MS2 ion annotations after processing. |
| `--generate-speclib` | boolean |  |  |  |  | `false` | Generate a spectral library from the search results. If `global_fdr` is specified, an additional global FDR-filtered library is generated from all MSruns in the samplesheet. |
| `--peptide-max-length` | integer |  |  |  |  | `12` | Specify the maximum length of peptides to be considered after processing |
| `--peptide-min-length` | integer |  |  |  |  | `8` | Specify the minimum length of peptides to be considered after processing |

## preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--filter-mzml` | boolean |  |  |  |  | `false` | Clean up spectrum files and remove artificial charge 0 peptides. |
| `--pick-ms-levels` | integer |  |  |  |  | `2` | Specify the MS levels for which the peak picking is applied (unless you use `--run_centroidisation`). |
| `--run-centroidisation` | boolean |  |  |  |  | `false` | Include the flag when the specified ms level is not centroided (default=false). |

## quantification_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-rt-alignment-shift` | integer |  |  |  |  | `300` | Set a maximum retention time shift for the linear RT alignment |
| `--quantification-fdr` | boolean |  | yes |  |  |  | Compute FDR for the targeted approach |
| `--quantification-mapping-tolerance` | number |  | yes |  |  | `0` | Specify a rt mapping tolerance for mapping features between runs |
| `--quantification-min-peak-width` | number |  | yes |  |  | `0.2` | Specify a minimum peak width for quantification |
| `--quantification-min-prob` | number |  | yes |  |  | `0` | Specify a cut off probability value for quantification events as a filter |
| `--quantification-mz-window` | number |  | yes |  |  | `5` | Specify a m/z window for matching between runs |
| `--quantification-peak-width` | number |  | yes |  |  | `60` | Specify a peak width for feature extraction |
| `--quantification-rt-window` | number |  | yes |  |  | `0` | Specify a rt window for matching between runs |
| `--quantify` | boolean |  |  |  |  | `false` | Turn on quantification mode |

## rescoring_settings

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--deeplc-calibration-set-size` | number |  | yes |  |  | `0.15` | Specify the number or percentage of PSMs that should be used for calibration of the DeepLC model. |
| `--fdr-level` | string |  |  | `peptide_level_fdrs`, `psm_level_fdrs`, `protein_level_fdrs` |  | `peptide_level_fdrs` | Specify the level at which the false discovery rate should be computed. |
| `--fdr-threshold` | number |  |  |  |  | `0.01` | Specify the false discovery rate threshold at which peptide hits should be selected. |
| `--feature-generators` | string |  |  |  |  | `deeplc,ms2pip` | Specify the feature generator that should be used for rescoring. One or multiple of basic,ms2pip,deeplc,ionmob |
| `--global-fdr` | boolean |  |  |  |  | `false` | Compute global FDR and backfilter sample-specific FDRs |
| `--ms2pip-model` | string |  |  | `Immuno-HCD`, `timsTOF`, `timsTOF2023`, `CID`, `CIDch2`, `CID-TMT`, `TMT`, `HCD`, `HCDch2`, `TTOF5600`, `iTRAQ`, `iTRAQphospho` |  | `Immuno-HCD` | Specify the MS²PIP model that should be used for rescoring. Checkout the MS²PIP documentation for available models. |
| `--ms2pip-model-dir` | string (directory path) |  | yes |  |  |  | Specify a local directory holding at least the MS²PIP models specified in `ms2pip_model`. |
| `--rescoring-engine` | string |  |  | `percolator`, `mokapot` |  | `percolator` | Specify the rescoring engine that should be used for rescoring. Either percolator or mokapot |
| `--subset-max-train` | integer |  | yes |  |  | `0` | Maximum subset for Percolator training iterations |

## search_settings

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--activation-method` | string |  |  | `ALL`, `CID`, `ECD`, `ETD`, `PQD`, `HCD`, `IRMPD` |  | `ALL` | Specify which fragmentation method was used in the MS acquisition |
| `--default-params-file-comet` | string |  | yes |  |  |  | Specify custom Comet params file. All parameters of this take precedence. |
| `--digest-mass-range` | string |  |  |  |  | `800:2500` | Specify the mass range in Dalton that peptides should fulfill to be considered for peptide spectrum matching. |
| `--enzyme` | string |  | yes | `unspecific cleavage`, `no cleavage`, `Arg-C/P`, `Asp-N`, `Lys-C`, `Lys-N`, `Chymotrypsin`, `CNBr`, `Trypsin`, `Arg-C`, `PepsinA`, `Trypsin/P`, `glutamyl endopeptidase` |  | `unspecific cleavage` | Specify which enzymatic restriction should be applied |
| `--fixed-mods` | string |  |  |  |  |  | Specify which fixed modifications should be applied to the database search |
| `--fragment-bin-offset` | number |  |  |  |  | `0.0` | Specify the fragment bin offset to be used for the comet database search. |
| `--fragment-mass-tolerance` | number |  |  |  |  | `0.01` | Specify the fragment mass tolerance to be used for the comet database search. |
| `--instrument` | string |  |  | `high_res`, `low_res` |  | `high_res` | Comets theoretical_fragment_ions parameter: theoretical fragment ion peak representation, high_res: sum of intensities plus flanking bins, ion trap (low_res) ms/ms: sum of intensities of central M bin only |
| `--num-hits` | integer |  |  |  |  | `1` | Specify the number of hits that should be reported for each spectrum. |
| `--number-mods` | integer |  |  |  |  | `3` | Specify the maximum number of modifications that should be contained in a peptide sequence match. |
| `--prec-charge` | string |  |  |  |  | `2:3` | Specify the precursor charge range that peptides should fulfill to be considered for peptide spectrum matching. |
| `--precursor-error-units` | string |  |  | `ppm`, `Da`, `amu` |  | `ppm` | Specify the unit of the precursor mass tolerance to be used for the Comet database search. |
| `--precursor-mass-tolerance` | integer |  |  |  |  | `5` | Specify the precursor mass tolerance to be used for the Comet database search. |
| `--remove-precursor-peak` | boolean |  |  |  |  | `false` | Include if you want to remove all peaks around precursor m/z |
| `--search-presets` | string (file path) |  |  |  | matches `^\S+\.tsv$` |  | TSV file with search parameter presets. Users can supply a custom file to define their own presets. |
| `--spectrum-batch-size` | integer |  | yes |  |  | `0` | Size of Spectrum batch for Comet processing (Decrease/Increase depending on Memory Availability) |
| `--use-NL-ions` | boolean |  |  |  |  | `false` | Include NL ions into the peptide spectrum matching |
| `--use-a-ions` | boolean |  |  |  |  | `false` | Include a ions into the peptide spectrum matching |
| `--use-c-ions` | boolean |  |  |  |  | `false` | Include c ions into the peptide spectrum matching |
| `--use-x-ions` | boolean |  |  |  |  | `false` | Include x ions into the peptide spectrum matching |
| `--use-z-ions` | boolean |  |  |  |  | `false` | Include z ions into the peptide spectrum matching |
| `--variable-mods` | string |  |  |  |  | `Oxidation (M)` | Specify which variable modifications should be applied to the database search |

<!-- Generated from nf-core/mhcquant@a4b6d51803af0fbde5acd8e9802df76280ba8306. Do not edit by hand. -->
