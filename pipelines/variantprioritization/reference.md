---
name: variantprioritization
version: 1.0.0
commit: 8ba629c53dbdb65057c85a3b0a76a7eb2e8688ef
---

# variantprioritization — full parameter reference

nf-core/variantprioritization pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## cpsr_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--classify-all` | boolean |  |  |  |  |  | Also provide CPSR TIER classifications for variants with existing ClinVar classifications. |
| `--clinvar-report-noncancer` | boolean |  |  |  |  |  | Include ClinVar variants linked to non-cancer phenotypes/conditions. |
| `--custom-list` | string |  |  |  |  |  | Path to custom gene list file (single-column Ensembl gene identifiers). |
| `--custom-list-name` | string |  |  |  |  |  | Display name for custom panel/list. |
| `--diagnostic-grade-only` | boolean |  |  |  |  |  | For PanelApp panels (1-44), include GREEN-status genes only. |
| `--gwas-findings` | boolean |  |  |  |  |  | Report overlap with low/moderate-risk GWAS cancer variants. |
| `--ignore-noncoding` | boolean |  |  |  |  |  | Ignore non-coding (non protein-altering) variants in CPSR report. |
| `--maf-upper-threshold` | number |  |  |  |  | `0.9` | Upper gnomAD global MAF threshold for variants included in report. |
| `--panel-id` | string |  |  |  | matches `^\d+(,\d+)*$` | `0` | Comma-separated CPSR virtual panel identifier(s). |
| `--pgx-findings` | boolean |  |  |  |  |  | Report overlap with pharmacogenomic toxicity variants (CPIC/PgX). |
| `--pop-gnomad` | string |  |  | `afr`, `amr`, `eas`, `sas`, `asj`, `nfe`, `fin`, `global` |  | `nfe` | gnomAD population source used for ACMG frequency assessment. |
| `--secondary-findings` | boolean |  |  |  |  |  | Include variants in ACMG secondary findings gene list (v3.2). |
| `--vep-gencode-basic` | boolean |  |  |  |  |  | Consider basic GENCODE transcript set only with Variant Effect Predictor (VEP) (option '--gencode_basic' in VEP). |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## pcgr_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--all-reference-signatures` | boolean |  |  |  |  |  | Use all reference SBS signatures during signature re-fitting. |
| `--assay` | string |  |  | `WGS`, `WES`, `TARGETED` |  |  | Type of DNA sequencing assay performed for input data. |
| `--call-conf-tag` | string |  |  |  |  |  | VCF INFO tag for somatic call confidence. |
| `--cna-analysis` | boolean |  |  |  |  |  | Enable copy-number alteration (CNA) analysis and reporting. |
| `--cna-overlap-pct` | integer |  |  |  |  | `50` | Mean percent overlap between CNA segment and gene transcripts for reporting gains/losses. |
| `--control-ad-max` | integer |  |  |  |  |  | Maximum control/normal allelic depth (ALT-supporting reads) allowed when control depth+AF tags are provided. |
| `--control-af-max` | integer |  |  |  |  | `1` | Maximum control/normal allelic fraction allowed when control AF tag is provided. |
| `--control-af-tag` | string |  |  |  |  |  | VCF INFO tag for control/normal variant allelic fraction. |
| `--control-dp-min` | integer |  |  |  |  | `0` | Minimum control/normal depth for variant inclusion when control depth tag is provided. |
| `--control-dp-tag` | string |  |  |  |  |  | VCF INFO tag for control/normal sequencing depth. |
| `--effective-target-size-mb` | integer |  |  |  |  | `34` | Effective target size in Mb for TMB calculation. |
| `--estimate-msi` | boolean |  |  |  |  |  | Predict microsatellite instability (MSI) status. |
| `--estimate-signatures` | boolean |  |  |  |  |  | Estimate mutational signature contributions by re-fitting. |
| `--estimate-tmb` | boolean |  |  |  |  |  | Estimate tumor mutational burden (TMB). |
| `--include-artefact-signatures` | boolean |  |  |  |  |  | Include sequencing artefact signatures during fitting. |
| `--input-cpsr` | string |  |  |  |  |  | Path to CPSR-classified germline calls file. |
| `--input-cpsr-yaml` | string |  |  |  |  |  | Path to CPSR YAML configuration file. |
| `--min-mutations-signatures` | integer |  |  |  |  | `200` | Minimum number of SNVs required for mutational signature re-fitting. |
| `--no-html` | boolean |  |  |  |  |  | Do not generate PCGR HTML report. |
| `--prevalence-reference-signatures` | number |  |  |  |  | `0.1` | Minimum tumor-type prevalence (%) of reference signatures to include in re-fitting. |
| `--tmb-ad-min` | integer |  |  |  |  |  | Minimum tumor allelic depth (ALT-supporting reads) required for TMB calculation when depth+AF tags are available. |
| `--tmb-af-min` | number |  |  |  |  |  | Minimum tumor allelic fraction required for inclusion in TMB calculation when AF tag is available. |
| `--tmb-display` | string |  |  | `coding_and_silent`, `coding_non_silent`, `missense_only` |  | `coding_and_silent` | TMB measure to show in report. |
| `--tmb-dp-min` | integer |  |  |  |  |  | Minimum tumor depth required for inclusion in TMB calculation when depth tag is available. |
| `--tumor-ad-min` | integer |  |  |  |  |  | Minimum tumor allelic depth (ALT-supporting reads) for variant inclusion when tumor depth+AF tags are provided. |
| `--tumor-af-min` | integer |  |  |  |  | `0` | Minimum tumor allelic fraction for variant inclusion when tumor AF tag is provided. |
| `--tumor-af-tag` | string |  |  |  |  |  | VCF INFO tag for tumor variant allelic fraction. |
| `--tumor-dp-min` | integer |  |  |  |  | `0` | Minimum tumor depth for variant inclusion when tumor depth tag is provided. |
| `--tumor-dp-tag` | string |  |  |  |  |  | VCF INFO tag for tumor sequencing depth. |
| `--tumor-ploidy` | string |  |  |  |  |  | Estimated tumor ploidy. |
| `--tumor-purity` | string |  |  |  | ≥ 0; ≤ 1 |  | Estimated tumor purity. |
| `--tumor-site` | integer |  |  |  |  | `0` | Primary tumor type/site code used for site-specific interpretation. |
| `--vcf2maf` | boolean |  |  |  |  |  | Generate a MAF file for the input VCF using vcf2maf. |

## pcgr_tumoronly_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--exclude-dbsnp-nonsomatic` | boolean |  |  |  |  |  | Exclude variants with dbSNP support for non-somatic origin. |
| `--exclude-likely-het-germline` | boolean |  |  |  |  |  | Exclude variants likely to represent heterozygous germline events. |
| `--exclude-likely-hom-germline` | boolean |  |  |  |  |  | Exclude variants likely to represent homozygous germline events. |
| `--exclude-nonexonic` | boolean |  |  |  |  |  | Exclude non-exonic variants in tumor-only filtering. |
| `--exclude-pon` | boolean |  |  |  |  |  | Exclude variants overlapping panel-of-normals calls. |
| `--maf-gnomad-afr` | number |  |  |  |  | `0.002` | Maximum gnomAD AFR population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-amr` | number |  |  |  |  | `0.002` | Maximum gnomAD AMR population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-asj` | number |  |  |  |  | `0.002` | Maximum gnomAD ASJ population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-eas` | number |  |  |  |  | `0.002` | Maximum gnomAD EAS population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-fin` | number |  |  |  |  | `0.002` | Maximum gnomAD FIN population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-global` | number |  |  |  |  | `0.002` | Maximum global gnomAD AF tolerated in tumor-only filtering. |
| `--maf-gnomad-nfe` | number |  |  |  |  | `0.002` | Maximum gnomAD NFE population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-oth` | number |  |  |  |  | `0.002` | Maximum gnomAD OTH population AF tolerated in tumor-only filtering. |
| `--maf-gnomad-sas` | number |  |  |  |  | `0.002` | Maximum gnomAD SAS population AF tolerated in tumor-only filtering. |
| `--pon-vcf` | string |  |  |  |  |  | Path to panel-of-normals (PoN) VCF used to suppress recurrent artefacts. |
| `--tumor-only` | boolean |  |  |  |  |  | Run in tumor-only mode (no matched normal sample). |

## reference_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--pcgr-bundleversion` | integer |  |  |  |  | `20250314` | PCGR/CPSR reference data bundle version. |
| `--pcgr-database-dir` | string |  |  |  |  |  | Path to PCGR database. Set `pcgr_download` to `false` when using this. |
| `--pcgr-download` | boolean |  |  |  |  | `true` | Download PCGR reference database from the PCGR site. Set to `false` if you want to use a local path. |
| `--vep-cache` | string |  |  |  |  | `s3://annotation-cache/vep_cache/` | Path to VEP cache. |
| `--vep-cache-version` | integer |  |  |  |  | `113` | VEP cache version. |
| `--vep-species` | string |  | yes |  |  | `homo_sapiens` | VEP species. Defaults to `homo_sapiens`. |

## variantfiltering_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--filter-deepvariant` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for DeepVariant VCF records. |
| `--filter-freebayes-germline` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for FreeBayes germline VCF records. |
| `--filter-freebayes-somatic` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for FreeBayes somatic VCF records. |
| `--filter-haplotypecaller` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for HaplotypeCaller VCF records. |
| `--filter-mutect2` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for Mutect2 VCF records. |
| `--filter-strelka-indels` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for Strelka INDEL records. |
| `--filter-strelka-snvs` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for Strelka SNV records. |
| `--filter-strelka-variants` | string |  |  |  |  | `-i\'FORMAT/DP>10\` | Filtering expression for combined Strelka variant records. |

## vep_params_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--vep-buffer-size` | integer |  |  |  |  | `500` | Number of variants buffered per VEP processing block. |
| `--vep-gencode-all` | boolean |  |  |  |  | `true` | Use full GENCODE transcript set during annotation. |
| `--vep-n-forks` | integer |  |  |  |  | `4` | Number of parallel VEP forks. |
| `--vep-no-intergenic` | boolean |  |  |  |  |  | Skip annotation of intergenic variants. |
| `--vep-pick-order` | string |  |  |  |  | `mane_select,mane_plus_clinical,canonical,biotype,ccds,rank,tsl,appris,length` | Priority order used by VEP when selecting a single representative consequence. |

<!-- Generated from nf-core/variantprioritization@8ba629c53dbdb65057c85a3b0a76a7eb2e8688ef. Do not edit by hand. -->
