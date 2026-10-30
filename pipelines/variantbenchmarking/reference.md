---
name: variantbenchmarking
version: 1.5.0
commit: 8b21c01749c4447b285d242a198127736f3ffe51
---

# variantbenchmarking — full parameter reference

nf-core/variantbenchmarking pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochromeLogs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
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
| `--ambiguous-beds` | string (file path) |  |  |  | matches `^\S+\.(bed)?(\.gz)?$` |  | Path to ambiguous BED. Only applicable to sompy tool. |
| `--analysis` | string | yes |  | `germline`, `somatic` |  |  | The analysis type used by the input files |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--enable-missing-genotypes` | string |  |  |  | matches `^((test\|truth)?,?)*(?<!,)$` |  | The pipeline filter outs missing genotypes with ./. or 0/0 by default, enable using missing genotypes for test, truth. Should be a comma-separated list of one or more of the following options: test, truth |
| `--ensemble-truth` | integer |  |  |  | ≥ 1 |  | Ensemble truth using input VCF files following the majority rule specified. This method should be used only if truth file is not available |
| `--exclude-expression` | string |  |  |  | length ≥ 1 |  | Use bcftools expressions https://samtools.github.io/bcftools/bcftools.html#expressions to exclude variants |
| `--falsepositive-bed` | string (file path) |  |  |  | matches `^\S+\.(bed)?(\.gz)?$` |  | Path to false positive BED. Only applicable to happy and sompy tool. |
| `--include-expression` | string |  |  |  | length ≥ 1 |  | Use bcftools expressions https://samtools.github.io/bcftools/bcftools.html#expressions to include variants |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.(csv\|tsv\|yaml\|yml\|json)$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--max-sv-size` | integer |  |  |  | ≥ -1 | `-1` | Maximum SV size of variants to benchmark, -1 to disable |
| `--method` | string | yes |  |  | matches `^((truvari\|svanalyzer\|happy\|sompy\|rtgtools\|wittyer\|intersect\|bndeval\|concordance)?,?)*(?<!,)$` |  | The benchmarking methods to use. For germline small variants (SNV and INDEL) use happy and/or rtgtools, for somatic small variants (SNV and INDEL) use sompy and/or rtgtools, for structural variants use wittyer, truvari and/or svanalyzer, for copy number variations use wittyer and/or truvari. Use intersect to intersect BED files. Should be a comma-separate list of one or more of the following options: truvari, svanalyzer, happy, sompy, rtgtools, wittyer, intersect |
| `--min-allele-freq` | number |  |  |  | ≥ -1 | `-1` | Minimum Alele Frequency of variants to benchmark, Use -1 to disable |
| `--min-num-reads` | integer |  |  |  | ≥ -1 | `-1` | Minimum number of read supporting variants to benchmark, Use, -1 to disable |
| `--min-sv-size` | integer |  |  |  | ≥ 0 | `0` | Minimum SV size of variants to benchmark, 0 to disable |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--preprocess` | string |  |  |  | matches `^((normalize\|split_multiallelic\|deduplicate\|prepy\|filter_contigs)?,?)*(?<!,)$` |  | The preprocessing steps to perform on the input files. Should be a comma-separated list of one or more of the following options: split_multiallelic, normalizate, deduplicate, prepy, filter_contigs |
| `--regions-bed` | string (file path) |  |  |  | matches `^\S+\.(bed\|vcf)?(\.gz)?$` |  | Path to regions BED or VCF files. Works similar to Bcftools -R. |
| `--skip-plots` | string |  |  |  | matches `^((svlength\|upset\|metrics)?,?)*(?<!,)$` |  | Skip plots: metrics, upset, svlength |
| `--sv-standardization` | string |  |  |  | matches `^((variantextractor\|svync\|svdecompose\|svtk)?,?)*(?<!,)$` |  | The standardization methods to perform on the input files. Should be a comma-separated list of one or more of the following options: variantextractor, svync, svdecompose, svtk |
| `--targets-bed` | string (file path) |  |  |  | matches `^\S+\.(bed\|vcf)?(\.gz)?$` |  | Path to targets BED. Works similar to Bcftools -T. It will be only used with happy, sompy or rtgtools. |
| `--truth-id` | string |  |  |  |  |  | Truth id, sample name to define truth vcf |
| `--truth-vcf` | string (file path) |  |  |  | matches `^\S+\.vcf(\.gz)?$` |  | Path to the golden set VCF files. |
| `--variant-type` | string | yes |  | `small`, `snv`, `indel`, `structural`, `copynumber` |  |  | Variant types to benchmark |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |
| `--test-data-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/variantbenchmarking` | Base path / URL for data used in the test profiles |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--chain` | string (file path) |  |  |  | matches `^\S+\.(chain\|bed)?(\.gz)?$` |  | Path to the chain file required for liftover. |
| `--dictionary` | string (file path) |  |  |  | matches `^\S+\.dict$` |  | The dictionary file is required for liftover process. It has to be .dict of genome file used in the workflow. |
| `--fai` | string (file path) | yes |  |  | matches `^\S+\.fai$` |  | Path to FAI genome file. |
| `--fasta` | string (file path) | yes |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--liftover` | string |  | yes |  | matches `^((test\|truth)?,?)*(?<!,)$` |  | Run liftover workflow: test,truth |
| `--rename-chr` | string (file path) |  |  |  | matches `^\S+\.txt$` |  | Path to the ranaming chromosomes for lifting over. |
| `--sdf` | string (file path) |  |  |  | matches `^\S+\.sdf$` |  | The SDF file needed to run rtgtools vcfeval |
| `--stratification-bed` | string (directory path) |  |  |  |  |  | Path to stratification BED files provided in a directory. This directory has to be given together with stratification_tsv, list BED files in stratification_tsv. Only applicable to happy tool. |
| `--stratification-tsv` | string (file path) |  |  |  | matches `^\S+\.tsv$` |  | List the stratification BED files in this file, to be used with stratification_bed |

<!-- Generated from nf-core/variantbenchmarking@8b21c01749c4447b285d242a198127736f3ffe51. Do not edit by hand. -->
