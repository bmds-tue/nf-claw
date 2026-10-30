---
name: tumourevo
version: 1.0.0
commit: 180ae5447d0eb0214f650b6fcf7dabed0c77b5a2
---

# tumourevo — full parameter reference

nf-core/tumourevo pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## cnaqc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cnaqc-blacklist-indels` | string |  |  |  |  | `TRUE` | If TRUE INDEL are excluded from CNAqc analysis and following steps otherwise are kept. |
| `--cnaqc-matching-strategy` | string |  |  | `closest`, `rightmost` |  | `rightmost` | For clonal simple CNAs, if "closest" the closest peak will be used to match the expected peak. If "rightmost" peaks are matched prioritizing right to left peaks (the higher-VAF gets matched first); this strategy is more correct in principle but works only if there are no spurious peaks in the estimated density. |
| `--cnaqc-min-absolute-karyotype-mutations` | integer |  |  |  |  | `100` | For clonal simple CNAs, this is the same as `cnaqc_min_karyotype_size` (not declared in this pinned schema), but with a cut measured on absolute mutation counts. |
| `--cnaqc-muts-per-karyotype` | integer |  |  |  |  | `25` | Minimum number of mutations that are required to be mapped to a karyotype in order to compute CCF values. |
| `--cnaqc-purity-error` | number |  |  |  |  | `0.05` | For clonal simple CNAs, the purity error tolerance to determine QC pass or fail. |

## driver_annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--drivers-table` | string |  |  |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/tumourevo/data/DRIVER_ANNOTATION/ANNOTATE_DRIVER/Compendium_Cancer_Genes.tsv` | Path to driver table. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | boolean |  |  |  |  |  | Email address for completion summary. |
| `--email-on-fail` | boolean |  |  |  |  |  | Email address for completion summary, only when pipeline fails. |
| `--monochrome-logs` | boolean |  |  |  |  |  | Do not use coloured log outputs. |
| `--plaintext-email` | boolean |  |  |  |  |  | Send plain-text email instead of HTML. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## joincnaqc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--joincnaqc-keep-original` | string |  |  | `TRUE`, `FALSE` |  | `TRUE` | If TRUE the original CNAqc object is kept in the joinCNAqc object, otherwise it is lost. |

## main_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string |  |  |  |  |  | Path to reference fasta file. |
| `--filter` | boolean |  |  |  |  |  | Flag for filtering or not QC mutations. |
| `--genome` | string | yes |  | `GRCh38`, `GRCh37` |  | `GRCh38` | Reference genome name. |
| `--publish-dir-mode` | string |  |  |  |  | `copy` | Method used to save pipeline results to output directory. |
| `--qc-chr` | boolean |  |  |  |  |  | If True QC analysis is performed by chromosome otherwise is performed whole genome |
| `--tools` | string |  |  |  | matches `^((tinc\|mobster\|viber\|pyclone-vi\|sparsesignatures\|sigprofiler)?,?)*(?<!,)$` | `tinc,mobster,viber,pyclone-vi,sparsesignatures,sigprofiler` | List of tools for running the pipeline. |

## mobster

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--mobster-k` | string |  |  |  | matches `^[1-9][0-9]*:[1-9][0-9]*$` | `1:5` | A vector with the number of Beta components to use. |
| `--mobster-min-vaf` | number |  |  |  |  | `0.05` | Threshold for minimum VAF to use in the deconvolution |
| `--mobster-n-cutoff` | integer |  |  |  |  | `10` | The minimum number of mutations assigned to a cluster to be returned as output. |
| `--mobster-pi-cutoff` | number |  |  |  |  | `0.02` | The minimum mixing proportion of a cluster to be returned as output. |
| `--mobster-tail` | string |  |  | `TRUE`, `FALSE` |  | `TRUE` | Whether to use tail mutations for subclonal deconvolution or not . |

## other

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | boolean |  |  |  |  |  | Institutional config contact information. |
| `--config-profile-description` | boolean |  |  |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  |  |  |  |  |  |
| `--config-profile-url` | boolean |  |  |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  |  |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  |  |  |  | `master` | Git commit id for Institutional configs. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  |  |  |  |  |  |
| `--hostnames` | boolean |  |  |  |  |  |  |
| `--igenomes-base` | string |  |  |  |  | `s3://ngi-igenomes/igenomes/` |  |
| `--igenomes-ignore` | boolean |  |  |  |  |  |  |
| `--pipelines-testdata-base-path` | string |  |  |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` |  |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--tracedir` | string |  |  |  |  | `null/pipeline_info` |  |
| `--validate-params` | boolean |  |  |  |  | `true` |  |
| `--version` | boolean |  |  |  |  |  |  |

## pyclone_vi

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--pyclonevi-density` | string |  |  | `beta-binomial`, `binomial` |  | `beta-binomial` | The probability density used to model the read count data. Choices are beta-binomial and binomial. |
| `--pyclonevi-n-cluster` | integer |  |  |  |  | `20` | The number of clusters to use while fitting. |
| `--pyclonevi-n-grid-point` | integer |  |  |  |  | `100` | Number of grid points used for approximating the posterior distribution. |
| `--pyclonevi-n-restarts` | integer |  |  |  |  | `100` | Number of random restarts of variational inference. |

## sigprofiler

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--download-sigprofiler-genome` | boolean |  |  |  |  | `true` | Specify True if the reference genome should be downloaded. |
| `--genome-installed-path` | string |  |  |  |  |  | Specify the path to the reference genome (if downloaded by the user), e.g. path/to/genome/tsb |
| `--publish-dir-mode-genome-sigprofiler` | string |  |  | `symlink`, `rellink`, `copy`, `copyNoFollow`, `move` |  | `move` | Mode of publishing the SigProfiler genome. |
| `--sigprofiler-context-type` | string |  |  |  | matches `^(96\|DINUC\|ID)(?:,(96\|DINUC\|ID))*$` | `96,DINUC,ID` | Mutation context name(s), separated by commas (,), that define the mutational contexts for signature extraction. In the default value, 96 represents the SBS96 context, DINUC represents the dinucleotide context, and ID represents the indel context. |
| `--sigprofiler-input-type` | string |  |  |  |  | `matrix` | 'matrix' is used for table format inputs using a tab separated file. |
| `--sigprofiler-max-nmf-iterations` | integer |  |  |  |  | `1000000` | The maximum number of iterations to be completed before NMF converges . |
| `--sigprofiler-maximum-signatures` | integer |  |  |  |  | `25` | The maximum number of signatures to be extracted. |
| `--sigprofiler-min-nmf-iterations` | integer |  |  |  |  | `10000` | The minimum number of iterations to be completed before NMF converges. |
| `--sigprofiler-minimum-signatures` | integer |  |  |  |  | `1` | The minimum number of signatures to be extracted. |
| `--sigprofiler-nmf-replicates` | integer |  |  |  |  | `100` | The number of iterations to be performed to extract each number signature. |
| `--sigprofiler-nmf-test-conv` | integer |  |  |  |  | `10000` | The number number of iterations to done between checking next convergence . |

## sparsesignature

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--sparsesignatures-cross-validation-entries` | number |  |  |  |  | `0.01` | The cross-validation test size, i.e., the percentage of entries set to zero during NMF and used for validation. |
| `--sparsesignatures-cross-validation-iterations` | integer |  |  |  |  | `5` | The number of randomized restarts of a single cross-validation repetition, in case of poor fits. |
| `--sparsesignatures-cross-validation-repetitions` | integer |  |  |  |  | `50` | The number of repetitions of the cross-validation procedure. |
| `--sparsesignatures-iterations` | integer |  |  |  |  | `30` | The number of iterations of every single run of NMF LASSO. |
| `--sparsesignatures-k` | string |  |  |  | matches `^[1-9][0-9]*:[1-9][0-9]*$` | `3:10` | Number of signatures to be discovered. |
| `--sparsesignatures-lambda-rate-alpha` | integer |  |  |  |  | `0` | The candidate values of the sparsity parameter for the exposure-matrix entries alpha whose goodness of fit is assessed by cross-validation. |
| `--sparsesignatures-lambda-values-alpha` | string |  |  |  | matches `^c\(\s*[0-9]+(?:\.[0-9]+)?(?:\s*,\s*[0-9]+(?:\.[0-9]+)?)*\s*\)$` | `c(0.00, 0.01, 0.05, 0.10)` | The candidate values of the sparsity parameter for the exposure-matrix entries alpha whose goodness of fit is assessed by cross-validation. |
| `--sparsesignatures-lambda-values-beta` | string |  |  |  | matches `^c\(\s*[0-9]+(?:\.[0-9]+)?(?:\s*,\s*[0-9]+(?:\.[0-9]+)?)*\s*\)$` | `c(0.01, 0.05, 0.1, 0.2)` | The candidate values of the sparsity parameter for the signature matrix 'beta' whose goodness of fit is assessed by cross-validation. |
| `--sparsesignatures-max-iterations-lasso` | integer |  |  |  |  | `10000` | The number of sub-iterations involved in the sparsification phase, within a full NMF LASSO iteration. |
| `--sparsesignatures-nmf-runs` | integer |  |  |  |  | `10` | Number of iterations to estimate the length(K) matrices beta (including the background signature) in case the argument beta is NULL. Ignored if beta is given. |
| `--sparsesignatures-num-processes` | string |  |  |  | matches `^(all\|[0-9]+:[0-9]+)$` | `all` | The number of requested NMF worker subprocesses to spawn. If Inf, an adaptive maximum number is automatically chosen. If NA or NULL, the function is run as a single process. |
| `--sparsesignatures-seed` | integer |  |  |  |  | `42` | Seed for the random number generation. To be set for reproducibility. |

## tinc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--tinc-normal-contamination-lv` | integer |  |  |  |  | `3` | A number that represent the normal contamination level for which the sample is considered passed or failed. |

## variant_annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--download-cache-vep` | boolean |  |  |  |  | `true` | Parameter for downloading VEP cache. |
| `--vep-cache` | string |  |  |  |  |  | Path to VEP cache. |
| `--vep-cache-version` | string |  |  |  |  |  | VEP cache version. |
| `--vep-custom-args` | string |  |  |  |  | `--everything --filter_common --per_gene --total_length --offline --format vcf` | Add an extra custom argument to VEP. |
| `--vep-genome` | string |  |  |  |  |  | VEP reference genome name. |
| `--vep-species` | string |  |  |  |  |  | VEP species. |

## vcf2cnaqc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--vcf-filter-mutations` | boolean |  |  |  |  | `true` | Flag for filtering mutations from vcf. |

## viber

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--viber-binomial-cutoff` | number |  |  |  |  | `0.05` | The minimum Binomial success probability when applying a heuristic procedure to filter clusters after Variational Inference. |
| `--viber-dimensions-cutoff` | integer |  |  |  |  | `1` | The minimum number of dimensions where we want to detect a Binomial component when applying a heuristic procedure to filter clusters after Variational Inference. |
| `--viber-k` | integer |  |  |  |  | `10` | The maximum number of clusters returned. Lower values speed up convergence. |
| `--viber-pi-cutoff` | number |  |  |  |  | `0.02` | The minimum size of the mixture component when applying a heuristic procedure to filter clusters after Variational Inference. |
| `--viber-re-assign` | string |  |  | `TRUE`, `FALSE` |  | `FALSE` | Boolean value whether points assigned to a cluster that is filtered our, are re-assigned from the density function. |

<!-- Generated from nf-core/tumourevo@180ae5447d0eb0214f650b6fcf7dabed0c77b5a2. Do not edit by hand. -->
