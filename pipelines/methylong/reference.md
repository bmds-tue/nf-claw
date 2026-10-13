---
name: methylong
version: 2.0.0
commit: 3513e80df682ad20f42d6429a2ee142b606949b5
---

# methylong — full parameter reference

nf-core/methylong pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ont-aligner` | string |  |  | `dorado`, `minimap2` |  | dorado | Aligner option in ONT workflow, default is dorado aligner, specify minimap2 to switch |
| `--pacbio-aligner` | string |  |  | `pbmm2`, `minimap2` |  | pbmm2 | Aligner option in PacBio workflow, default is pbmm2, specify minimap2 to switch |

## dmr_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dmr-a` | string |  |  |  |  |  | One of the group of DMR analysis in population scale |
| `--dmr-b` | string |  |  |  |  |  | Another group of DMR analysis in population scale |
| `--dmr-population-scale` | boolean |  |  |  |  |  | Indicate if required DMR analysis for population scale |
| `--haplotype-dmrer` | string |  |  | `dss`, `modkit` |  | dss | DMRer option in DMR analysis for haplotype level, default is dss, specify modkit to switch |
| `--population-dmrer` | string |  |  | `dss`, `modkit` |  | dss | DMRer option in DMR analysis for population scale, default is dss, specify modkit to switch |
| `--skip-snvs` | boolean |  |  |  |  |  | Indicate if to skip snvcall and phase |

## fiberseq_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fiberseq` | boolean |  |  |  |  |  | Indicate if required m6a calling for fiberseq data |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
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

## mod_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ccsmeth-ag-model` | string (file path) |  |  |  |  | ${projectDir}/bin/ccsmeth_models/model_ccsmeth_5mCpG_aggregate_attbigru_b11.v2p.ckpt | Ccsmeth call freqb model. |
| `--ccsmeth-cm-model` | string (file path) |  |  |  |  | ${projectDir}/bin/ccsmeth_models/model_ccsmeth_5mCpG_call_mods_attbigru2s_b21.v3.ckpt | Ccsmeth call mods model. |
| `--dorado-model` | string |  |  |  |  | sup | Specify dorado model, default is sup, other available models can be found on Dorado's GitHub repository. |
| `--dorado-modification` | string |  |  |  |  | 5mC_5hmC | Specify dorado modification, default is 5mC_5hmC, other available modifications can be found on Dorado's GitHub repository. |
| `--pacbio-modcall` | boolean |  |  |  |  |  | Indicate if required modcalling in PacBio workflow |
| `--pacbio-modcaller` | string |  |  | `jasmine`, `ccsmeth` |  | jasmine | Modcaller option in PacBio workflow, default is jasmine, specify ccsmeth to switch |

## mod_pileup_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--all-contexts` | boolean |  |  |  |  |  | Specify pileup context |
| `--bedgraph` | boolean |  |  |  |  |  | Indicate if required bedgraphs as output |
| `--denovo` | boolean |  |  |  |  |  | This option will identify and output all CG sites found in the consensus sequence from the reads in the `pb-CpG-tools`pileup (reference free); by default reference sequences are used to identify and output all CG sites. |
| `--m6a` | boolean |  |  |  |  |  | Indicate if pileup m6a motif |
| `--pileup-count` | boolean |  |  |  |  | model | Specify pbcpgtools pileup mode, default is using model mode, specify this parameter to switch to count mode |
| `--pileup-method` | string |  |  | `pbcpgtools`, `modkit` |  | pbcpgtools | Pileup method in PacBio workflow, default is pbcpgtools, specify modkit to switch |

## multiqc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |

## preprocessing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--no-trim` | boolean |  |  |  |  |  | Skip trimming in ONT workflow, will directly start from alignment step |
| `--reset` | boolean |  |  |  |  |  | Removes the alignment information added by aligners and updates flags accordingly |

<!-- Generated from nf-core/methylong@3513e80df682ad20f42d6429a2ee142b606949b5. Do not edit by hand. -->
