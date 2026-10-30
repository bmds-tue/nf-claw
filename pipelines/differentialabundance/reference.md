---
name: differentialabundance
version: 2.0.0
commit: 30ed7741fc392127156c2fb10cfa3d69d216b54b
---

# differentialabundance — full parameter reference

nf-core/differentialabundance pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## base_abundance_values

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--affy-cel-files-archive` | string |  |  |  |  |  | Alternative to matrix: a compressed CEL files archive such as often found in GEO |
| `--feature-length-matrix` | string |  |  |  |  |  | (RNA-seq only): optional transcript/gene length matrix with samples and transcript_ids/gene_ids as in the abundance matrix. |
| `--matrix` | string (file path) |  |  |  | matches `^\S+\.(tsv\|csv)$\|\S*proteinGroups\.txt$` |  | TSV/CSV-format abundance matrix |
| `--querygse` | string |  |  |  |  |  | Use SOFT files from GEO by providing the GSE study identifier |

## base_features_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--control-features` | string (file path) |  |  |  |  |  | A text file listing technical features (e.g. spikes) |
| `--features` | string |  |  |  | matches `^\S+\.(csv\|tsv)$` |  | Supply your own feature annotations. Can be derived from the GTF (rnaseq) or from the Bioconductor annotation package (affy arrays). |
| `--features-id-col` | string | yes |  |  |  | `gene_id` | Feature ID attribute in the abundance table as well as in the GTF file (e.g. the gene_id field) |
| `--features-metadata-cols` | string |  |  |  |  | `gene_id,gene_name,gene_biotype` | Comma-separated string, specifies feature metadata columns to be used for exploratory analysis, platform-specific |
| `--features-name-col` | string | yes |  |  |  | `gene_name` | Feature name attribute in the abundance table as well as in the GTF file (e.g. the gene symbol field) |
| `--features-type` | string | yes |  |  |  | `gene` | Type of feature. Often 'gene' |
| `--sizefactors-from-controls` | boolean |  |  |  |  | `false` | When set, use the control features in scaling/ normalization (currently only supported for differential_method deseq2) |

## base_input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--contrasts` | string (file path) |  |  |  | matches `^\S+\.(csv\|tsv\|yml\|yaml)$` |  | A CSV/TSV/YML/YAML file describing sample contrasts to compare groups. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.(csv\|tsv)$` |  | Path to CSV/TSV file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--round-digits` | integer |  |  |  |  | `-1` | To how many digits should numeric output in different modules be rounded? If -1 or null, will not round. |
| `--seed` | integer |  |  |  |  |  | Global seed for stochastic methods |
| `--study-abundance-type` | string |  | yes |  |  | `abundance` | Label describing the abundance values in the report heading. |
| `--study-name` | string | yes |  |  |  | `study` | A string identifier used to name result files in the output directory |
| `--study-type` | string | yes |  | `rnaseq`, `generic_matrix`, `affy_array`, `maxquant`, `geo_soft_file` |  | `rnaseq` | Input data format category used for input validation and routing (not for selecting analysis methods). |

## base_observations_e_g_samples_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--observations-id-col` | string | yes |  |  |  | `sample` | Column in the sample sheet to be used as the primary sample identifier |
| `--observations-name-col` | string |  |  |  |  |  | Column in the sample sheet to be used as identifier for observations. If unset, the --observations_id_col is used. |
| `--observations-type` | string | yes |  |  |  | `sample` | Type of observation |

## base_paramsheet_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--paramset-name` | string |  |  |  |  |  | Name of the paramset to run. In profile mode, set by the analysis profile for output directory naming. In paramsheet mode, selects which paramset(s) to run (comma-separated). |
| `--paramsheet` | string (file path) |  |  |  | matches `^\S+\.(yaml\|yml)$` |  | Path to a paramsheet YAML file. Setting this activates multi-run (paramsheet) mode where paramsheet values take priority over CLI flags. |

## differential_deseq2_specific_options_rna_seq_only

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--deseq2-alpha` | number |  |  |  |  | `0.1` | `alpha` parameter passed to results() |
| `--deseq2-alt-hypothesis` | string |  |  |  |  | `greaterAbs` | `altHypothesis` parameter passed to results() |
| `--deseq2-fit-type` | string |  |  | `parametric`, `local`, `mean`, `glmGamPoi` |  | `parametric` | `fitType` parameter passed to DESeq() |
| `--deseq2-independent-filtering` | boolean |  |  |  |  | `true` | `independentFiltering` parameter passed to results() |
| `--deseq2-lfc-threshold` | number |  |  |  |  | `0` | `lfcThreshold` parameter passed to results() |
| `--deseq2-min-replicates-for-replace` | integer |  |  |  |  | `7` | 'minReplicatesForReplace' parameter passed to DESeq() |
| `--deseq2-minmu` | number |  |  |  |  | `0.5` | `minmu` parameter passed to results() |
| `--deseq2-p-adjust-method` | string |  |  |  |  | `BH` | `pAdjustMethod` parameter passed to results() |
| `--deseq2-sf-type` | string |  |  | `ratio`, `poscounts`, `iterate` |  | `ratio` | `sfType` parameter passed to DESeq() |
| `--deseq2-shrink-lfc` | boolean |  |  |  |  | `true` | Shrink fold changes in results? |
| `--deseq2-test` | string |  |  | `Wald`, `LRT` |  | `Wald` | `test` parameter passed to DESeq() |
| `--deseq2-use-t` | boolean |  |  |  |  | `false` | `useT` parameter passed to DESeq2 |
| `--deseq2-vs-blind` | boolean |  |  |  |  | `true` | `blind` parameter for rlog() and/ or vst() |
| `--deseq2-vs-method` | string |  |  | `rlog`, `vst`, `rlog,vst` |  | `vst` | variance stabilisation method to use when making a variance stabilised matrix |
| `--deseq2-vst-nsub` | integer |  |  |  |  | `1000` | `nsub` parameter passed to vst() |

## differential_differential_analysis

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--differential-feature-id-column` | string | yes |  |  |  | `gene_id` | The feature identifier column in differential results tables |
| `--differential-file-suffix` | string |  |  |  |  |  | Advanced option: the suffix associated tabular differential results tables. Will by default use the appropriate suffix according to the study_type. |
| `--differential-max-pval` | number | yes |  |  |  | `1` | Maximum p value used to calculate differential feature numbers |
| `--differential-max-qval` | number | yes |  |  |  | `0.05` | Maximum q value used to calculate differential feature numbers |
| `--differential-method` | string |  |  | `deseq2`, `limma`, `dream`, `propd` |  | `deseq2` | Differential analysis method |
| `--differential-min-fold-change` | number | yes |  |  |  | `2` | Minimum fold change used to calculate differential feature numbers. Note that this number will be log2 transformed |
| `--differential-palette-name` | string | yes |  |  |  | `Set1` | Valid R palette name |
| `--differential-subset-to-contrast-samples` | boolean |  |  |  |  | `false` | In differential analysis (DEseq2 or Limma), subset to the contrast samples before modelling variance? |

## differential_dream_specific_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dream-adjust-method` | string |  |  | `BH`, `BY`, `holm`, `hochberg`, `hommel`, `bonferroni`, `fdr`, `none` |  | `BH` | Method used to adjust p-values for multiple testing (passed to p.adjust). |
| `--dream-apply-voom` | boolean |  |  |  |  | `false` | Turns on and off usage of voomWithDreamWeights() normalization in the DREAM module. |
| `--dream-confint` | boolean |  |  |  |  | `false` | passed to variancePartition::dream(), logical, should 95% confidence intervals be output for logFC? Alternatively, can take a numeric value between zero and one specifying the confidence level required. |
| `--dream-ddf` | string |  |  | `adaptive`, `Satterthwaite`, `Kenward-Roger` |  | `adaptive` | Method used to estimate effective degrees of freedom for hypothesis testing in the linear mixed model. Allowed values: adaptive (default), Satterthwaite, Kenward-Roger. |
| `--dream-lfc` | integer |  |  |  |  | `0` |  |
| `--dream-p-value` | integer |  |  |  |  | `1` |  |
| `--dream-proportion` | number |  |  |  |  | `0.01` | passed to variancePartition::dream() (via eBayes), assumed proportion of genes that are differentially expressed (numeric 0-1). |
| `--dream-reml` | boolean |  |  |  |  | `false` | passed to variancePartition::dream(), logical, use REML estimation for mixed-model variance components (passed through to lmer()). |
| `--dream-robust` | boolean |  |  |  |  | `false` | passed to variancePartition::dream() (via eBayes), logical, should the estimation of df.prior and var.prior be robustified against outlier sample variances? |
| `--dream-stdev-coef-lim` | string |  |  |  |  | `0.1,4` | passed to variancePartition::dream() (via eBayes), comma-separated numeric pair giving the lower and upper limits of the standard deviation of the logFC values used in the prior. |
| `--dream-trend` | boolean |  |  |  |  | `false` | passed to variancePartition::dream() (via eBayes), logical, should an intensity-dependent trend be allowed for the prior variance? |
| `--dream-winsor-tail-p` | string |  |  |  |  | `0.05,0.1` | passed to variancePartition::dream() (via eBayes), comma-separated numeric pair giving the proportion of the lower and upper tails to be winsorized before estimating the standard deviation. |

## differential_limma_specific_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--limma-adjust-method` | string |  |  | `holm`, `hochberg`, `hommel`, `bonferroni`, `BH`, `BY`, `fdr`, `null` |  | `BH` | passed to topTable(), method used to adjust the p-values for multiple testing. |
| `--limma-block` | string |  |  |  |  |  | Sample sheet column to be used to derive a vector or factor specifying a blocking variable on the arrays for limma::lmFit(); however, for random effects models, DREAM is the recommended approach in this pipeline |
| `--limma-confint` | boolean |  |  |  |  | `false` | passed to topTable(), logical, should confidence 95% intervals be output for logFC? Alternatively, can take a numeric value between zero and one specifying the confidence level required. |
| `--limma-correlation` | string |  |  |  |  |  | passed to limma::lmFit(), the inter-duplicate or inter-technical replicate correlation; however for random effects models, DREAM is the recommended approach in this pipeline |
| `--limma-lfc` | integer |  |  |  |  | `0` | passed to topTable(), minimum absolute log2-fold-change required |
| `--limma-method` | string |  |  | `ls`, `robust` |  | `ls` | passed to lmFit(), the fitting method |
| `--limma-ndups` | number |  |  |  |  |  | passed to lmFit(), positive integer giving the number of times each distinct probe is printed on each array. |
| `--limma-p-value` | number |  |  |  |  | `1` | cutoff value for adjusted p-values. Only genes with lower p-values are listed. |
| `--limma-proportion` | number |  |  |  |  | `0.01` | passed to eBayes(), a numeric value between 0 and 1, assumed proportion of genes which are differentially expressed |
| `--limma-robust` | boolean |  |  |  |  | `false` | passed to eBayes(), logical, should the estimation of df.prior and var.prior be robustified against outlier sample variances? |
| `--limma-spacing` | string |  |  |  |  |  | passed to lmFit(), positive integer giving the spacing between duplicate occurrences of the same probe, spacing=1 for consecutive rows. |
| `--limma-stdev-coef-lim` | string |  |  |  |  | `0.1,4` | passed to eBayes, comma separated string of two values, assumed lower and upper limits for the standard deviation of log2-fold-changes for differentially expressed genes |
| `--limma-trend` | boolean |  |  |  |  | `false` | passed to eBayes(), logical, should an intensity-dependent trend be allowed for the prior variance? |
| `--limma-use-voom` | boolean |  |  |  |  | `false` | Turns on and off usage of voom normalization in the Limma module. |
| `--limma-winsor-tail-p` | string |  |  |  |  | `0.05,0.1` | passed to eBayes, comma separated string of length 1 or 2, giving left and right tail proportions of x to Winsorize. Used only when robust=TRUE. |

## differential_propd_specific_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--propd-alpha` | number |  |  |  |  |  | Alpha value for the Box-Cox transformation used by propd. Leave unset to skip the transformation. |
| `--propd-fdr` | number |  |  |  |  | `0.05` | False discovery rate threshold used to define significantly proportional pairs. |
| `--propd-moderated` | boolean |  |  |  |  | `true` | Use moderated theta values in propd. |
| `--propd-number-of-cutoffs` | integer |  |  |  |  | `100` | Number of theta cutoffs evaluated when estimating FDR by permutation. |
| `--propd-permutation` | integer |  |  |  |  | `0` | Number of permutations for FDR estimation. 0 uses the analytical FDR from F-statistic p-values. |
| `--propd-save-adjacency` | boolean |  |  |  |  | `false` | Save the gene-by-gene adjacency matrix. Must be set to true when pairing propd with `--functional_method grea`, which consumes the adjacency. |
| `--propd-save-pairwise` | boolean |  |  |  |  | `false` | Save the table of significant pairwise statistics. |
| `--propd-save-pairwise-full` | boolean |  |  |  |  | `false` | Save the full table of pairwise statistics (very large). |
| `--propd-save-rdata` | boolean |  |  |  |  | `false` | Save the propd object as an RDS file. |

## exploratory_exploratory_analysis

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--exploratory-assay-names` | string |  | yes |  |  | `raw,normalised,variance_stabilised` | Specifies assay names to be used for matrices, platform-specific. |
| `--exploratory-clustering-method` | string | yes |  |  |  | `ward.D2` | Clustering method used in dendrogram creation |
| `--exploratory-cor-method` | string | yes |  |  |  | `spearman` | Correlation method used in dendrogram creation |
| `--exploratory-final-assay` | string |  | yes |  |  | `variance_stabilised` | Specifies final assay to be used for exploratory analysis, platform-specific |
| `--exploratory-log2-assays` | string |  |  |  |  | `raw,normalised` | Of which assays to compute the log2 during exploratory analysis. Not necessary for maxquant data as this is controlled by the pipeline. |
| `--exploratory-mad-threshold` | integer |  |  |  |  | `-5` | Threshold on MAD score for outlier identification |
| `--exploratory-main-variable` | string | yes |  |  |  | `auto_pca` | How should the main grouping variable be selected? 'auto_pca', 'contrasts', or a valid column name from the observations table. |
| `--exploratory-n-features` | integer | yes |  |  |  | `500` | Number of features selected before certain exploratory analyses. If -1, will use all features. |
| `--exploratory-palette-name` | string | yes |  |  |  | `Set1` | Valid R palette name |
| `--exploratory-whisker-distance` | number |  |  |  |  | `1.5` | Length of the whiskers in boxplots as multiple of IQR. Defaults to 1.5. |

## functional_decoupler_specific_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--decoupler-methods` | string |  |  |  |  | `ulm` | Comma-separated list of methods to use (e.g., 'ora,ulm') |
| `--decoupler-min-n` | integer |  |  |  | ≥ 1 | `5` | Removes sources of a net with less than min_n targets |
| `--decoupler-network` | string (file path) |  |  |  | matches `^\S+\.(tsv)$` |  | Path to TSV file containing network file for decoupler |

## functional_functional_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--functional-method` | string |  |  | `none`, `gsea`, `gprofiler2`, `decoupler`, `grea` |  | `none` | Functional analysis method. Set to 'none' (default) to disable functional analysis. |
| `--gene-sets-files` | string |  |  |  |  |  | Gene sets in [GMT or GMX-format](https://docs.gsea-msigdb.org/#GSEA/Data_Formats/#gene-set-database-formats); for GSEA: multiple comma-separated input files in either format are possible. For gprofiler2: A single file in GMT format is possible; this has lowest priority and will be overridden by --gprofiler2_token and --gprofiler2_organism. |

## functional_gprofiler2

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gprofiler2-background-column` | string |  |  |  |  |  | Which column to use as gene IDs in the background matrix. |
| `--gprofiler2-background-file` | string |  |  |  | matches `^\S+\.(csv\|tsv\|txt)$\|auto\|false` | `auto` | Path to CSV/TSV/TXT file that should be used as a background list of genes for the query; alternatively, 'auto' (default) or 'false'. |
| `--gprofiler2-correction-method` | string |  |  | `gSCS`, `analytical`, `g_SCS`, `fdr`, `false_discovery_rate`, `bonferroni` |  | `gSCS` | The method that should be used for multiple testing correction. |
| `--gprofiler2-domain-scope` | string |  |  | `annotated`, `known`, `custom`, `custom_annotated` |  | `annotated` | How to calculate the statistical domain size. |
| `--gprofiler2-evcodes` | boolean |  |  |  |  | `false` | Whether to include evcodes in the results. |
| `--gprofiler2-max-qval` | number |  |  |  |  | `0.05` | Maximum q value used for significance testing. |
| `--gprofiler2-measure-underrepresentation` | boolean |  |  |  |  | `false` | Should underrepresentation be measured instead of overrepresentation? |
| `--gprofiler2-min-diff` | integer |  |  |  |  | `1` | How many genes must be differentially expressed in a pathway for it to be considered enriched? Default 1. |
| `--gprofiler2-organism` | string |  |  |  |  |  | Short name of the organism that is analyzed, e.g. hsapiens for homo sapiens. |
| `--gprofiler2-palette-name` | string |  |  |  |  | `Blues` | Valid R palette name |
| `--gprofiler2-significant` | boolean |  |  |  |  | `true` | Should only significant enrichment results be considered? |
| `--gprofiler2-sources` | string |  |  |  |  |  | On which source databases to run the gprofiler query |
| `--gprofiler2-token` | string |  |  |  |  |  | Token that should be used as a query. |

## functional_grea

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--grea-permutation` | integer |  |  |  |  | `100` | Number of permutations used by grea to estimate enrichment significance. |
| `--grea-set-max` | integer |  |  |  |  | `500` | Maximum number of features in a gene set. |
| `--grea-set-min` | integer |  |  |  |  | `15` | Minimum number of features in a gene set. |

## functional_gsea

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gsea-make-sets` | boolean |  |  |  |  | `true` | Make detailed geneset report? |
| `--gsea-median` | boolean |  |  |  |  | `false` | Use median for class metrics |
| `--gsea-metric` | string |  |  | `Signal2Noise`, `tTest`, `Ratio_of_Classes`, `Diff_of_Classes`, `log2_Ratio_of_Classes` |  | `Signal2Noise` | Metric for ranking genes |
| `--gsea-norm` | string |  |  | `meandiv`, `null` |  | `meandiv` | Normalisation mode |
| `--gsea-nperm` | integer |  |  |  |  | `1000` | Number of permutations |
| `--gsea-num` | integer |  |  |  |  | `100` | Number of markers |
| `--gsea-order` | string |  |  | `descending`, `ascending` |  | `descending` | Gene list ordering mode |
| `--gsea-permute` | string |  |  | `phenotype`, `gene_set` |  | `phenotype` | Permutation type |
| `--gsea-plot-top-x` | integer |  |  |  |  | `20` | Plot graphs for the top sets of each phenotype |
| `--gsea-rnd-type` | string |  |  | `no_balance`, `equalize_and_balance` |  | `no_balance` | Randomization mode |
| `--gsea-save-rnd-lists` | boolean |  |  |  |  | `false` | Save random ranked lists |
| `--gsea-scoring-scheme` | string |  |  | `weighted`, `weighted_p2`, `weighted_p1.5`, `classic` |  | `weighted` | Enrichment statistic |
| `--gsea-set-max` | integer |  |  |  |  | `500` | Max size: exclude larger sets |
| `--gsea-set-min` | integer |  |  |  |  | `15` | Min size: exclude smaller sets |
| `--gsea-sort` | string |  |  | `real`, `absolute` |  | `real` | Gene list sorting mode |
| `--gsea-zip-report` | boolean |  |  |  |  | `false` | Make a zipped file with all reports |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  |  | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  |  |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## preprocessing_affy_input_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--affy-background` | boolean |  |  |  |  | `true` | logical value. If set to true, apply background correction using RMA. |
| `--affy-bgversion` | integer |  |  |  |  | `2` | integer value indicating which RMA background to use |
| `--affy-build-annotation` | boolean |  |  |  |  | `true` | logical value. If TRUE, a matrix of probe annotations will be derived. |
| `--affy-cdfname` | string |  |  |  |  |  | Used to specify the name of an alternative cdf package. If set to NULL, then the usual cdf package based on Affymetrix' mappings will be used. |
| `--affy-destructive` | boolean |  |  |  |  | `false` | logical value. If TRUE, then works on the PM matrix in place as much as possible, good for large datasets. |
| `--affy-file-name-col` | string |  |  |  |  | `file` | Column of the sample sheet containing the Affymetrix CEL file name |
| `--affy-rm-extra` | boolean |  |  |  |  | `false` | if TRUE, then overrides what is in rm.mask and rm.oultiers. |
| `--affy-rm-mask` | boolean |  |  |  |  | `false` | should the spots marked as 'MASKS' set to NA? |
| `--affy-rm-outliers` | boolean |  |  |  |  | `false` | should the spots marked as 'OUTLIERS' set to NA? |

## preprocessing_filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--filtering-grouping-var` | string |  |  |  |  |  | An optional grouping variable to be used to calculate a min_samples value |
| `--filtering-min-abundance` | integer or boolean | yes |  |  |  |  | Minimum abundance value. Set to false to disable abundance filtering. |
| `--filtering-min-proportion` | number |  |  |  |  |  | A minimum proportion of observations, given as a number between 0 and 1, that must pass the threshold. Overrides minimum_samples |
| `--filtering-min-proportion-not-na` | number |  |  |  |  | `0.5` | A minimum proportion of observations, given as a number between 0 and 1, that must have a value (not NA) to retain the row/ feature (e.g. gene). |
| `--filtering-min-samples` | number |  |  |  |  | `1` | Minimum observations that must pass the threshold to retain the row/ feature (e.g. gene). |
| `--filtering-min-samples-not-na` | number |  |  |  |  |  | Minimum observations that must have a value (not NA) to retain the row/ feature (e.g. gene). Overrides filtering_min_proportion_not_na. |

## preprocessing_gtf_parsing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--features-gtf-feature-type` | string |  |  |  |  | `transcript` | If a GTF file is supplied, which feature type to use |
| `--features-gtf-table-first-field` | string |  |  |  |  | `gene_id` | If a GTF file is supplied, which field should go first in the converted output table |
| `--gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?` |  | Genome annotation file in GTF format |

## preprocessing_proteus_input_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--proteus-measurecol-prefix` | string |  |  |  |  | `LFQ intensity` | Prefix of the column names of the MaxQuant proteingroups table in which the intensity values are saved; the prefix has to be followed by the sample names that are also found in the samplesheet. Default: 'LFQ intensity'; will search for both the prefix as entered and the prefix followed by one whitespace. |
| `--proteus-norm-function` | string |  |  | `normalizeMedian`, `normalizeQuantiles` |  | `normalizeMedian` | Normalization function to use on the MaxQuant intensities. |
| `--proteus-palette-name` | string |  |  |  |  | `Set1` | Valid R palette name |
| `--proteus-plotmv-loess` | boolean |  |  |  |  | `true` | Should a loess line be added to the plot of mean-variance relationship of the conditions? Default: true. |
| `--proteus-plotsd-method` | string |  |  | `violin`, `dist`, `box` |  | `violin` | Which method to use for plotting sample distributions of the MaxQuant intensities; one of 'violin', 'dist', 'box'. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

## report_reporting_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--citations-file` | string |  |  |  |  | `${projectDir}/CITATIONS.md` | A markdown file containing citations to include in the final report |
| `--css-file` | string | yes | yes |  |  | `${projectDir}/assets/nf-core_style.css` | CSS to use to style the output, in lieu of the default nf-core styling |
| `--disable-report-modules` | string |  | yes |  |  |  | Comma-separated list of sections that should not be included in the final Quarto report |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--logo-file` | string | yes | yes |  |  | `${projectDir}/docs/images/nf-core-differentialabundance_logo_light.png` | A logo to display in the report instead of the generic pipeline logo. |
| `--report-author` | string |  |  |  |  |  | An author for reporting outputs |
| `--report-contributors` | string |  |  |  |  |  | Semicolon-separated string of contributor info that should be listed in the report. |
| `--report-description` | string |  |  |  |  |  | A description for reporting outputs |
| `--report-file` | string (file path) | yes |  |  | matches `^[^,\s]+\.(Rmd\|qmd\|ipynb)(\s*,\s*[^,\s]+\.(Rmd\|qmd\|ipynb))*$` | `${projectDir}/assets/differentialabundance_report.qmd` | Qmd/Rmd/ipynb report template(s) from which to create the pipeline report. Supply a single path or a comma-separated list of paths to render multiple reports per paramset. |
| `--report-title` | string |  |  |  |  |  | A title for reporting outputs |
| `--skip-reports` | boolean |  |  |  |  | `false` | Skip generation of reports |

## shiny_shiny_app_settings

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--shinyngs-build-app` | boolean |  |  |  |  | `true` | Should a Shiny app be built? |
| `--shinyngs-deploy-to-shinyapps-io` | boolean |  |  |  |  | `false` | Should the app be deployed to shinyapps.io? |
| `--shinyngs-shinyapps-account` | string |  |  |  |  |  | Your shinyapps.io account name |
| `--shinyngs-shinyapps-app-name` | string |  |  |  |  |  | The name of the app to push to in your shinyapps.io account |

<!-- Generated from nf-core/differentialabundance@30ed7741fc392127156c2fb10cfa3d69d216b54b. Do not edit by hand. -->
