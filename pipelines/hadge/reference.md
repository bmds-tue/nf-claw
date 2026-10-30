---
name: hadge
version: 1.0.0
commit: 921d3780498d0d6f4da0d3ea8c8416d214a3ff42
---

# hadge — full parameter reference

nf-core/hadge pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## bff_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bff-barcodeWhitelist` | string or null |  |  |  |  |  | Path to barcode whitelist for preprocessing. |
| `--bff-callerDisagreementThreshold` | number or null |  |  |  |  |  | Threshold for caller disagreement. |
| `--bff-cellbarcodeWhitelist` | string or null |  |  |  |  |  | Path to cell barcode whitelist for GenerateCellHashingCalls(). |
| `--bff-chemistry` | string |  |  |  |  | `10xV3` | Library chemistry (e.g., 10xV3). |
| `--bff-doHeatmap` | boolean |  |  |  |  | `true` | Whether to generate heatmaps in BFF. |
| `--bff-doTSNE` | boolean |  |  |  |  |  | Whether to compute tSNE visualization in BFF. |
| `--bff-majorityConsensusThreshold` | number or null |  |  |  |  |  | Majority consensus threshold. |
| `--bff-methods` | string |  |  | `COMBINED`, `RAW`, `CLUSTER` |  | `COMBINED` | Method(s) to use within BFF. |
| `--bff-methodsForConsensus` | string or null |  |  |  |  |  | Methods to use for consensus calling. |
| `--bff-metricsFile` | string or null |  |  |  |  |  | Optional metrics file path. |
| `--bff-perCellSaturation` | number or null |  |  |  |  |  | Per-cell saturation value. |
| `--bff-preprocessing` | boolean |  |  |  |  | `true` | Whether to run preprocessing steps for BFF. |

## cellsnp_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cellsnp-celltag` | string |  |  |  |  | `CB` | Tag for cell barcodes, e.g., CB for 10x Genomics. Set to 'None' for bulk RNA-seq or SMART-seq2. |
| `--cellsnp-countorphan` | boolean |  |  |  |  |  | If true, do not skip anomalous read pairs (i.e., count orphan reads). |
| `--cellsnp-exclflag` | string |  |  |  |  |  | Excluding flags in SAM/BAM: skip reads that have ANY of these flags. See SAM format specification for details. |
| `--cellsnp-inclflag` | string |  |  |  |  |  | Required flags in SAM/BAM: skip reads that don't have ALL of these flags. See SAM format specification for details. |
| `--cellsnp-maxdepth` | integer |  |  |  | ≥ 0 | `0` | Maximum read depth at a position per input file. Set to 0 for highest possible value. |
| `--cellsnp-mincount` | integer |  |  |  | ≥ 0 | `20` | Minimum aggregated count (across cells) for SNPs to be included in the output. |
| `--cellsnp-minlen` | integer |  |  |  | ≥ 0 | `30` | Minimum read length (after clipping) for a read to be included. |
| `--cellsnp-minmaf` | number |  |  |  | ≥ 0; ≤ 0.5 | `0` | Minimum minor allele frequency (MAF) for SNPs to be included in the output. |
| `--cellsnp-minmapq` | integer |  |  |  | ≥ 0 | `20` | Minimum mapping quality for a read to be included. |
| `--cellsnp-umitag` | string |  |  |  |  | `Auto` | Tag for UMI barcodes, e.g., UB for 10x Genomics. Set to 'None' for bulk RNA-seq or SMART-seq2 without UMIs. |

## demuxem_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--demuxem-alpha-on-samples` | number |  |  |  | ≥ 0; ≤ 1 | `0` | The Dirichlet prior concentration parameter (alpha) on samples. An alpha value < 1.0 will make the prior sparse. |
| `--demuxem-gender-genes` | string |  |  |  |  |  | Comma-separated list of gender-specific genes (e.g. Xist) for generating violin plots. |
| `--demuxem-generate-diagnostic-plots` | boolean |  |  |  |  | `true` | Generate diagnostic plots. |
| `--demuxem-min-num-genes` | integer |  |  |  | ≥ 0 | `100` | Only demultiplex cells/nuclei with at least this number of expressed genes. |
| `--demuxem-min-num-umis` | integer |  |  |  | ≥ 0 | `100` | Only demultiplex cells/nuclei with at least this number of UMIs. |
| `--demuxem-min-signal-hashtag` | number |  |  |  | ≥ 0 | `10` | Any cell/nucleus with less than this count of hashtags from the signal will be marked as unknown. |
| `--demuxem-random-state` | integer |  |  |  | ≥ 0 | `0` | The random seed used in the KMeans algorithm to separate empty ADT droplets from others. |

## demuxlet_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--demuxlet-alpha` | string |  |  |  |  | `0.1,0.2,0.3,0.4,0.5` | Grid of alpha to search for. |
| `--demuxlet-doublet-prior` | number |  |  |  | ≥ 0; ≤ 1 | `0.5` | Prior probability of doublet. |
| `--demuxlet-field` | string |  |  |  |  | `GT` | FORMAT field to extract the genotype, likelihood, or posterior from. |
| `--demuxlet-geno-error-coeff` | number |  |  |  | ≥ 0; ≤ 1 | `0` | Slope of genotype error rate. [error] = [offset] + [1-offset]*[coeff]*[1-r2] |
| `--demuxlet-geno-error-offset` | number |  |  |  | ≥ 0; ≤ 1 | `0.1` | Offset of genotype error rate. [error] = [offset] + [1-offset]*[coeff]*[1-r2] |
| `--demuxlet-min-callrate` | number |  |  |  | ≥ 0; ≤ 1 | `0.5` | Minimum call rate. |
| `--demuxlet-min-mac` | integer |  |  |  | ≥ 0 | `1` | Minimum minor allele frequency. |
| `--demuxlet-r2-info` | string |  |  |  |  | `R2` | INFO field name representing R2 value. Used for representing imputation quality. |

## donor_match_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cell-genotype` | string or null (file path) |  |  |  |  |  | Path to cell genotype file (necessary only for donor_match mode). |
| `--demultiplexing-result` | string or null (file path) |  |  |  |  |  | Path to demultiplexing result CSV file (necessary only for donor_match mode). |
| `--find-variants` | boolean |  |  |  |  | `true` | Find variants for donor matching. |
| `--gt-donors` | string or null (file path) |  |  |  |  |  | Path to cell genotype file (necessary only for donor_match mode). |
| `--match-donor` | boolean |  |  |  |  | `true` | Match donor between different demultiplexing methods. |
| `--match-donor-method1` | string or null |  |  |  |  |  | First method to use for donor matching. |
| `--match-donor-method2` | string or null |  |  |  |  |  | Second method to use for donor matching. |
| `--subset-gt-donors` | boolean |  |  |  |  | `true` | Option to subset the donor genotype based on detected variants. |
| `--variant-count` | integer |  |  |  | ≥ 0 | `10` | Minimum variant count threshold. |
| `--variant-pct` | number |  |  |  | ≥ 0.5; ≤ 1 | `0.9` | The Minimal percentage of a variant for filtering. Has to be in a range between `[0,5;1[`. For example, 0.9 means that we only keep variants with a frequency higher than 90% or lower than 10%. |
| `--vireo-filtered-variants` | string or null (file path) |  |  |  |  |  | Path to Vireo filtered variants file (optional, only used in donor_match mode). |

## dsc_pileup_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dsc-pileup-cap-bq` | integer |  |  |  | ≥ 0; ≤ 60 | `40` | Maximum base quality (higher BQ will be capped). |
| `--dsc-pileup-excl-flag` | integer |  |  |  |  | `3844` | SAM/BAM FLAGs to be excluded. |
| `--dsc-pileup-min-bq` | integer |  |  |  | ≥ 0 | `13` | Minimum base quality to consider (lower BQ will be skipped). |
| `--dsc-pileup-min-mq` | integer |  |  |  | ≥ 0 | `20` | Minimum mapping quality to consider (lower MQ will be ignored). |
| `--dsc-pileup-min-snp` | integer |  |  |  | ≥ 0 | `0` | Minimum number of SNPs with coverage for a droplet/cell to be considered. |
| `--dsc-pileup-min-td` | integer |  |  |  | ≥ 0 | `0` | Minimum distance to the tail (lower will be ignored). |
| `--dsc-pileup-min-total` | integer |  |  |  | ≥ 0 | `0` | Minimum number of total reads for a droplet/cell to be considered. |
| `--dsc-pileup-min-uniq` | integer |  |  |  | ≥ 0 | `0` | Minimum number of unique reads (determined by UMI/SNP pair) for a droplet/cell to be considered. |
| `--dsc-pileup-tag-group` | string |  |  |  |  | `CB` | Tag representing readgroup or cell barcodes to partition the BAM file into multiple groups. For 10x Genomics, use CB. |
| `--dsc-pileup-tag-umi` | string |  |  |  |  | `UB` | Tag representing UMIs. For 10x Genomics, use UB. |

## freemuxlet_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--freemuxlet-bf-thres` | number |  |  |  | ≥ 0 | `5.41` | Bayes Factor Threshold used in the initial clustering. |
| `--freemuxlet-doublet-prior` | number |  |  |  | ≥ 0; ≤ 1 | `0.5` | Prior probability of doublet. |
| `--freemuxlet-frac-init-clust` | number |  |  |  | ≥ 0; ≤ 1 | `1` | Fraction of droplets to be clustered in the very first round of initial clustering procedure. |
| `--freemuxlet-geno-error` | number |  |  |  | ≥ 0; ≤ 1 | `0.1` | Genotype error parameter per cluster. |
| `--freemuxlet-iter-init` | integer |  |  |  | ≥ 0 | `10` | Iteration for initial cluster assignment (set to zero to skip the iterations). |
| `--freemuxlet-keep-init-missing` | boolean |  |  |  |  |  | Keep missing cluster assignment as missing in the initial iteration. |
| `--freemuxlet-randomize-singlet-score` | boolean |  |  |  |  |  | Randomize the singlet scores to test its effect. |
| `--freemuxlet-seed` | integer |  |  |  | ≥ 0 | `0` | Seed for random number (use clocks if not set). |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
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

## gmmdemux_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gmmdemux-estimated-n-cells` | integer or null |  |  |  | ≥ 1 |  | If specified, it will generate the statistic summary of the dataset, including MSM and SSM rates. This requires an estimated total number of cells in the assay as input. |
| `--gmmdemux-examine` | string or null (file path) |  |  |  |  |  | Provide the cell list. Requires a file path argument. Only executes if -u is set. |
| `--gmmdemux-extract` | string |  |  |  |  |  | Names of the HTO tag(s) to extract, separated by ','. Joint HTO samples are combined with '+', such as 'HTO_1+HTO_2'. |
| `--gmmdemux-hto-names` | string or null |  |  |  |  |  | Comma separated list of HTO names, without whitespace. If null, hto_names are extracted from the input hto matrix from features.tsv.gz. |
| `--gmmdemux-random-state` | integer |  |  |  | ≥ 0 | `0` | The random seed used in the GaussianMixture algorithm. |
| `--gmmdemux-skip` | string or null (file path) |  |  |  |  |  | Load a full classification report and skip the mtx folder as input. Requires a file path argument. |
| `--gmmdemux-summary-report` | boolean |  |  |  |  | `true` | If true, summary report is generated. |
| `--gmmdemux-threshold` | number |  |  |  | ≥ 0; ≤ 1 | `0.8` | The confidence threshold value for classification. A higher value leads to more stringent classification. |
| `--gmmdemux-type-report` | boolean |  |  |  |  | `true` | If true, full classification report is generated, otherwise the simplified classification report. |

## hasheddrops_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hasheddrops-alpha` | number or null |  |  |  |  |  | Scaling parameter for Dirichlet-multinomial sampling. |
| `--hasheddrops-ambient` | boolean |  |  |  |  | `true` | Whether to use ambient solution abundance. |
| `--hasheddrops-byRank` | integer or null |  |  |  |  |  | Alternative method for identifying empty droplets. |
| `--hasheddrops-combinations` | array |  |  |  |  |  | An integer matrix specifying valid combinations of HTOs. Number of items in each row has to be the same. |
| `--hasheddrops-confidentMin` | integer |  |  |  | ≥ 0 | `2` | Minimum threshold for confident singlet identification. |
| `--hasheddrops-confidentNmads` | integer |  |  |  | ≥ 0 | `3` | Number of MADs to identify confident singlets. |
| `--hasheddrops-constantAmbient` | boolean |  |  |  |  |  | Whether to use constant ambient contamination level. |
| `--hasheddrops-doubletMin` | integer |  |  |  | ≥ 0 | `2` | Minimum threshold for doublet identification. |
| `--hasheddrops-doubletMixture` | boolean |  |  |  |  |  | Whether to use 2-component mixture model for doublets. |
| `--hasheddrops-doubletNmads` | integer |  |  |  | ≥ 0 | `3` | Number of MADs to identify doublets. |
| `--hasheddrops-gene-col` | integer |  |  |  | ≥ 1 | `2` | Column to use for gene names. |
| `--hasheddrops-ignore` | number or null |  |  |  |  |  | Lower bound for ignoring barcodes. |
| `--hasheddrops-isCellFDR` | number |  |  |  | ≥ 0; ≤ 1 | `0.01` | FDR threshold for cell filtering. |
| `--hasheddrops-lower` | integer |  |  |  | ≥ 0 | `100` | Lower bound on total UMI count for empty droplets. |
| `--hasheddrops-minProp` | number |  |  |  | ≥ 0; ≤ 1 | `0.05` | Minimum proportion for ambient profile inference. |
| `--hasheddrops-niters` | integer |  |  |  | ≥ 1 | `10000` | Number of iterations for Monte Carlo p-value calculations. |
| `--hasheddrops-pseudoCount` | integer |  |  |  | ≥ 0 | `5` | Minimum pseudo-count for log-fold change computation. |
| `--hasheddrops-round` | boolean |  |  |  |  | `true` | Whether to round non-integer values. |
| `--hasheddrops-runEmptyDrops` | boolean |  |  |  |  |  | Whether to run EmptyDrops analysis as part of HashedDrops. |
| `--hasheddrops-testAmbient` | boolean |  |  |  |  | `true` | Whether to test ambient RNA. |

## hashsolo_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hashsolo-cell-hashing-columns` | array or null |  |  |  |  |  | Groovy list (['hash_1', 'hash_2']) of .obs columns that contain cell hashing counts. Can be null if the data is in 10x Genomics format, as the columns are derived from the input. |
| `--hashsolo-clustering-data` | string or null (directory path) |  |  |  |  |  | Input directory containing transcriptomic data in 10x mtx format. |
| `--hashsolo-number-of-noise-barcodes` | integer or null |  |  |  |  |  | Number of barcodes to use to create noise distribution. |
| `--hashsolo-pre-existing-clusters` | string or null |  |  |  |  |  | Column in cell_hashing_adata.obs for how to break up demultiplexing. |
| `--hashsolo-priors` | string |  |  |  |  | `0.01,0.8,0.19` | List of comma-separated priors for each hypothesis: NEGATIVE, SINGLET, DOUBLET. |
| `--hashsolo-round-digits` | integer |  |  |  | ≥ 0 | `10` | Number of decimal places to round numeric values in cell_hashing_data.obs before saving. If omitted, no rounding is applied. |

## htodemux_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--htodemux-init` | string |  |  |  |  | `NULL` | Initialization method for clustering. |
| `--htodemux-kfunc` | string |  |  |  |  | `clara` | Clustering function to use. |
| `--htodemux-nsamples` | integer |  |  |  | ≥ 1 | `100` | Number of samples for clustering. |
| `--htodemux-nstarts` | integer |  |  |  | ≥ 1 | `100` | Number of starts for clustering. |
| `--htodemux-quantile` | number |  |  |  | ≥ 0; ≤ 1 | `0.99` | The quantile to use for thresholding. |
| `--htodemux-seed` | integer |  |  |  |  | `42` | Random seed for reproducibility. |
| `--htodemux-verbose` | boolean |  |  |  |  | `true` | Whether to print verbose output. |

## htodemux_visualization_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--htodemux-visualization-featureScatter` | boolean |  |  |  |  | `true` | Generate feature scatter plot. If no features are provided (one of them is null), the first two features from the assay will be used. |
| `--htodemux-visualization-heatMap` | boolean |  |  |  |  | `true` | Generate heatmap. |
| `--htodemux-visualization-heatMapNcells` | integer |  |  |  | ≥ 1 | `500` | Number of cells for heatmap. |
| `--htodemux-visualization-ridgeNCol` | integer |  |  |  | ≥ 1 | `2` | The number of plots that are dispalyed next to each other in one row. The number of plots corresponds to the number of Hash Tag Oligo (HTO) identifiers. |
| `--htodemux-visualization-ridgePlot` | boolean |  |  |  |  | `true` | Generate ridge plot. |
| `--htodemux-visualization-scatterFeat1` | string |  |  |  |  |  | Name of a Hash Tag Oligo (HTO) identifiers, usually defined in the `feature.tsv` of the hto matrix folder. |
| `--htodemux-visualization-scatterFeat2` | string |  |  |  |  |  | Name of a Hash Tag Oligo (HTO) identifiers, usually defined in the `feature.tsv` of the hto matrix folder. |
| `--htodemux-visualization-tSNE` | boolean |  |  |  |  | `true` | Generate a two dimensional tSNE embedding for HTOs. |
| `--htodemux-visualization-tSNEApprox` | boolean |  |  |  |  |  | Approximate tSNE. |
| `--htodemux-visualization-tSNEDimMax` | integer |  |  |  | ≥ 1 | `2` | Max number of donors. |
| `--htodemux-visualization-tSNEIdents` | string |  |  | `Singlet`, `Doublet`, `Negative` |  | `Negative` | What should we remove from the object (we have Singlet, Doublet and Negative). |
| `--htodemux-visualization-tSNEInvert` | boolean |  |  |  |  | `true` | Invert tSNE selection. |
| `--htodemux-visualization-tSNEPerplexity` | integer |  |  |  | ≥ 1 | `100` | Value for perplexity. |
| `--htodemux-visualization-tSNEVerbose` | boolean |  |  |  |  |  | Verbose tSNE. |
| `--htodemux-visualization-vlnFeatures` | string |  |  |  |  | `nCount_RNA` | Features to plot (gene expression, metrics, PC scores, anything that can be retrieved by FetchData). |
| `--htodemux-visualization-vlnLog` | boolean |  |  |  |  | `true` | Plot the feature axis on log scale. |
| `--htodemux-visualization-vlnPlot` | boolean |  |  |  |  | `true` | Generate violin plot. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bam-qc` | boolean |  |  |  |  | `true` | Perform BAM QC. |
| `--common-variants` | string |  |  |  | matches `^\S+\.vcf(\.gz)?$` |  | File with common variants. If provided, the BAM files will be filtered to only include reads that overlap with the common variants. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--genetic-tools` | string |  |  |  | matches `^(vireo\|demuxlet\|freemuxlet\|souporcell\|cellsnp)(,(vireo\|demuxlet\|freemuxlet\|souporcell\|cellsnp))*$` | `vireo` | Tools used for genetic demultiplexing. |
| `--hash-tools` | string |  |  |  | matches `^(htodemux\|multiseq\|bff\|demuxem\|gmm-demux\|hasheddrops\|hashsolo)(,(htodemux\|multiseq\|bff\|demuxem\|gmm-demux\|hasheddrops\|hashsolo))*$` | `gmm-demux` | Tools used for hash demultiplexing. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--mode` | string | yes |  | `genetic`, `hashing`, `rescue`, `donor_match` |  | `rescue` | Mode of the pipeline. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-intermediates` | boolean |  |  |  |  |  | Save intermediate files. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## multiseqdemux_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--multiseqdemux-autoThresh` | boolean |  |  |  |  | `true` | Whether to automatically determine thresholds. |
| `--multiseqdemux-maxiter` | integer |  |  |  | ≥ 1 | `5` | Maximum number of iterations. |
| `--multiseqdemux-qrangeBy` | number |  |  |  | ≥ 0; ≤ 1 | `0.05` | Step size for quantile range. |
| `--multiseqdemux-qrangeFrom` | number |  |  |  | ≥ 0; ≤ 1 | `0.1` | Start of quantile range. |
| `--multiseqdemux-qrangeTo` | number |  |  |  | ≥ 0; ≤ 1 | `0.9` | End of quantile range. |
| `--multiseqdemux-quantile` | number |  |  |  | ≥ 0; ≤ 1 | `0.7` | The quantile to use for thresholding. |
| `--multiseqdemux-verbose` | boolean |  |  |  |  | `true` | Whether to print verbose output. |

## preprocessing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--preprocessing-assay` | string |  |  |  |  | `HTO` | Assay type for preprocessing. |
| `--preprocessing-gene-col` | integer |  |  |  |  | `2` | Column containing gene information. |
| `--preprocessing-margin` | integer |  |  |  |  | `2` | Margin parameter for preprocessing. |
| `--preprocessing-n-features` | integer |  |  |  |  | `2000` | Number of features to select. |
| `--preprocessing-ndelim` | string |  |  |  |  | `_` | Delimiter for parsing feature names. |
| `--preprocessing-norm-method` | string |  |  |  |  | `CLR` | Normalization method to use. |
| `--preprocessing-sel-method` | string |  |  |  |  | `mean.var.plot` | Method for feature selection. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

## souporcell_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--souporcell-common-variants` | string (file path) |  |  |  | matches `^\S+\.vcf(\.gz)?$` |  | Common variant loci or known variant loci vcf, must be vs same reference fasta. |
| `--souporcell-ignore` | boolean |  |  |  |  |  | Set to True to ignore data error assertions. |
| `--souporcell-known-genotypes` | string (file path) |  |  |  | matches `^\S+\.vcf$` |  | Known variants per clone in population vcf mode, must be .vcf right now we dont accept gzip or bcf sorry. |
| `--souporcell-known-genotypes-sample-names` | string |  |  |  |  |  | Which samples in population vcf from known genotypes option represent the donors in your sample. Provide space-separated sample names for multiple donors. |
| `--souporcell-max-loci` | integer |  |  |  | ≥ 0 | `2048` | Max loci per cell, affects speed. |
| `--souporcell-min-alt` | integer |  |  |  | ≥ 0 | `10` | Min alt to use locus. |
| `--souporcell-min-ref` | integer |  |  |  | ≥ 0 | `10` | Min ref to use locus. |
| `--souporcell-ploidy` | integer |  |  | `1`, `2` |  | `2` | Ploidy, must be 1 or 2. |
| `--souporcell-restarts` | integer |  |  |  | ≥ 0 | `100` | Number of restarts in clustering, when there are > 12 clusters we recommend increasing this to avoid local minima. |
| `--souporcell-skip-remap` | boolean |  |  |  |  |  | Don't remap with minimap2 (not recommended unless in conjunction with --common_variants). |

## vireo_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--vireo-ase-mode` | boolean |  |  |  |  |  | If true, turn on SNP specific allelic ratio (ASE mode). |
| `--vireo-cell-ambient-rnas` | boolean |  |  |  |  |  | If true, detect ambient RNAs in each cell (experimental feature). |
| `--vireo-cell-range` | string |  |  |  |  | `all` | Range of cells to process, e.g., '0-10000'. Default is 'all'. |
| `--vireo-extra-donor` | integer |  |  |  | ≥ 0 | `0` | Number of extra donors in pre-cluster, when GT needs to be learned. |
| `--vireo-extra-donor-mode` | string |  |  | `size`, `distance` |  | `distance` | Method for searching from extra donors. 'size': n_cell per donor; 'distance': GT distance between donors. |
| `--vireo-force-learn-gt` | boolean |  |  |  |  | `true` | If true, treat donor GT as prior only and learn genotypes from data. |
| `--vireo-genotag` | string |  |  | `GT`, `GP`, `PL` |  | `GT` | The tag for donor genotype in VCF file. Options: GT, GP, PL. |
| `--vireo-n-init` | integer |  |  |  | ≥ 1 | `50` | Number of random initializations when GT needs to be learned. |
| `--vireo-no-doublet` | boolean |  |  |  |  |  | If true, do not check for doublets during demultiplexing. |
| `--vireo-no-plot` | boolean |  |  |  |  |  | If true, turn off plotting GT distance. |
| `--vireo-rand-seed` | integer |  |  |  | ≥ 0 | `0` | Random seed for initialization. |

<!-- Generated from nf-core/hadge@921d3780498d0d6f4da0d3ea8c8416d214a3ff42. Do not edit by hand. -->
