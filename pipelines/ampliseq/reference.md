---
name: ampliseq
version: 3.0.0
commit: 992e6df34065067185b5e34665b5861b6827981d
---

# ampliseq — full parameter reference

nf-core/ampliseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## amplicon_sequence_variants_asv_calculation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--asv-calling` | string |  |  | `dada2`, `savont`, `auto` |  | auto | Tool for ASV calculation. |
| `--mergepairs-consensus-gap` | integer |  |  |  |  | -4 | DADA2: The penalty score assigned for each gap introduced during sequence alignment. |
| `--mergepairs-consensus-match` | integer |  |  |  |  | 1 | DADA2: The score assigned for each matching base pair during sequence alignment. |
| `--mergepairs-consensus-maxmismatch` | integer |  |  |  |  | 0 | DADA2: The maximum number of mismatches allowed within the overlapping region for merging reads. |
| `--mergepairs-consensus-minoverlap` | integer |  |  |  |  | 12 | DADA2: The minimum number of overlapping base pairs required to merge forward and reverse reads. |
| `--mergepairs-consensus-mismatch` | integer |  |  |  |  | -2 | DADA2: The penalty score assigned for each mismatched base pair during sequence alignment. |
| `--mergepairs-consensus-percentile-cutoff` | number |  |  |  |  | 0.001 | DADA2: The percentile used to determine a stringent cutoff which will correspond to the minimum observed overlap in the dataset. This ensures that only read pairs with high overlap are merged into consensus sequences. Those with insufficient overlap are concatenated. |
| `--mergepairs-strategy` | string |  |  | `merge`, `concatenate`, `consensus` |  | merge | DADA2: Strategy to merge paired end reads. When paired end reads are not sufficiently overlapping for merging, you can use "concatenate" (not recommended). When you have a mix of overlapping and non overlapping reads use "consensus" |
| `--sample-inference` | string |  |  | `independent`, `pooled`, `pseudo` |  | pooled | Mode of sample inference: "independent", "pooled" or "pseudo" |
| `--savont-options` | string |  |  |  |  | --fl-16s | Options for Savont ONT analysis |

## asv_filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--exclude-taxa` | string |  |  |  |  | mitochondria,chloroplast | Comma separated list of unwanted taxa, to skip taxa filtering use "none" |
| `--min-frequency` | integer |  |  |  |  | 1 | Abundance filtering |
| `--min-samples` | integer |  |  |  |  | 1 | Prevalence filtering |

## asv_post_processing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--decontam` | string |  |  | `none`, `decontaminate`, `notcontaminant` |  | none | Choose whether decontamination with `decontam` is applied to features. |
| `--decontam-decontaminate-method` | string |  |  | `auto`, `frequency`, `prevalence`, `combined`, `minimum`, `either`, `both` |  | auto | Choose the decontamination method for `--decontam decontaminate`. |
| `--decontam-decontaminate-threshold` | number |  |  |  | ≥ 0; ≤ 1 | 0.1 | Choose the contamination likelihood threshold for `--decontam decontaminate`. |
| `--decontam-notcontaminant-threshold` | number |  |  |  | ≥ 0; ≤ 1 | 0.5 | Choose the non-contaminant likelihood threshold for `--decontam notcontaminant`. |
| `--filter-codons` | boolean |  |  |  |  |  | Filter ASVs based on codon usage |
| `--filter-ssu` | string |  |  | `bac,arc,mito,euk`, `bac`, `arc`, `mito`, `euk`, `bac,arc`, `bac,mito`, `bac,euk`, `arc,mito`, `arc,euk`, `mito,euk`, `bac,arc,mito`, `bac,mito,euk`, `arc,mito,euk` |  |  | Enable SSU filtering. Comma separated list of kingdoms (domains) in Barrnap, a combination (or one) of "bac", "arc", "mito", and "euk". ASVs that have their lowest evalue in that kingdoms are kept. |
| `--max-len-asv` | integer |  |  |  |  |  | Maximum ASV length |
| `--min-len-asv` | integer |  |  |  |  |  | Minimal ASV length |
| `--orf-end` | integer |  |  |  |  |  | Ending position of codon tripletts |
| `--orf-start` | integer |  |  |  |  | 1 | Starting position of codon tripletts |
| `--raise-filter-stacksize` | boolean |  |  |  |  | true | Raise stack size when filtering VSEARCH clusters |
| `--stop-codons` | string |  |  |  |  | TAA,TAG | Define stop codons |
| `--vsearch-cluster` | boolean |  |  |  |  |  | Post-cluster ASVs with VSEARCH |
| `--vsearch-cluster-id` | number |  |  |  | ≥ 0; ≤ 1 | 0.97 | Pairwise Identity value used when post-clustering ASVs if `--vsearch_cluster` option is used (default: 0.97). |

## comparison

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--expected-abundances` | string (file path) |  |  |  | matches ^\S+\.(tsv\|txt)$ |  | Path to file of abundances of expected sequences in tsv format |
| `--expected-profile` | string (file path) |  |  |  | matches ^\S+\.(tsv\|txt)$ |  | Path to file of abundances of expected taxnonomies in tsv format |
| `--expected-sequences` | string (file path) |  |  |  | matches ^\S+\.(fasta\|fas\|fna\|fa\|ffn)$ |  | Path to file of expected sequences in fasta format |
| `--expected-sequences-merge` | string |  |  | `all`, `observed`, `expected`, `none` |  | all | How to handle multiple sequence matches |
| `--expected-sequences-mismatches` | integer |  |  |  | ≥ 0 | 0 | Threshold of accepted mismatches and gaps to the expected sequences |
| `--expected-sequences-region` | string |  |  | `alignment`, `observed`, `expected` |  | observed | What region of the sequence comparison is evaluated |

## differential_abundance_analysis

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ancom` | boolean |  |  |  |  |  | Perform differential abundance analysis with ANCOM |
| `--ancom-sample-min-count` | integer |  |  |  |  | 1 | Minimum sample counts to retain a sample for ANCOM analysis. Any sample below that threshold will be removed. |
| `--ancombc` | boolean |  |  |  |  |  | Perform differential abundance analysis with ANCOMBC |
| `--ancombc2` | boolean |  |  |  |  |  | Perform differential abundance analysis with ANCOMBC2 |
| `--ancombc2-formula` | string |  |  |  |  |  | Formula to perform differential abundance analysis with ANCOMBC2 |
| `--ancombc2-formula-reflvl` | string |  |  |  |  |  | Reference level for `--ancombc2_formula` |
| `--ancombc-effect-size` | number |  |  |  | ≥ 0 | 1.0 | Effect size threshold for differential abundance barplot for `--ancombc` and `--ancombc_formula` |
| `--ancombc-formula` | string |  |  |  |  |  | Formula to perform differential abundance analysis with ANCOMBC |
| `--ancombc-formula-reflvl` | string |  |  |  |  |  | Reference level for `--ancombc_formula` |
| `--ancombc-significance` | number |  |  |  | ≥ 0; ≤ 1 | 0.05 | Significance threshold for differential abundance barplot for `--ancombc` and `--ancombc_formula` |

## downstream_analysis

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--diversity-rarefaction-depth` | integer |  |  |  |  | 500 | Minimum rarefaction depth for diversity analysis. Any sample below that threshold will be removed. |
| `--metadata-category` | string |  |  |  |  |  | Comma separated list of metadata column headers for statistics. |
| `--metadata-category-barplot` | string |  |  |  |  |  | Comma separated list of metadata column headers for plotting average relative abundance barplots. |
| `--picrust` | boolean |  |  |  |  |  | If the functional potential of the bacterial community is predicted. |
| `--qiime-adonis-formula` | string |  |  |  |  |  | Formula for QIIME2 ADONIS metadata feature importance test for beta diversity distances |
| `--tax-agglom-max` | integer |  |  |  |  | 6 | Maximum taxonomy agglomeration level for taxonomic classifications |
| `--tax-agglom-min` | integer |  |  |  |  | 2 | Minimum taxonomy agglomeration level for taxonomic classifications |

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
| `--seed` | integer |  |  |  |  | 100 | Specifies the random seed. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches ^\S+\.(tsv\|csv\|yml\|yaml\|txt)$ |  | Path to tab-separated sample sheet |
| `--input-fasta` | string (file path) |  |  |  | matches ^\S+\.(fasta\|fas\|fna\|fa\|ffn)$ |  | Path to ASV/OTU fasta file |
| `--metadata` | string (file path) |  |  |  |  |  | Path to metadata sheet, when missing most downstream analysis are skipped (barplots, PCoA plots, ...). |
| `--multiregion` | string (file path) |  |  |  | matches ^\S+\.(tsv\|csv\|yml\|yaml\|txt)$ |  | Path to multi-region definition sheet, for multi-region analysis with Sidle |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--primer-fwd` | string |  |  |  |  |  | Forward primer sequence |
| `--primer-rev` | string |  |  |  |  |  | Reverse primer sequence |
| `--ref-taxonomy-storage` | string (directory path) |  |  |  |  |  | The directory where the reference taxonomy databases will be saved for re-use. Absolute paths to storage on Cloud infrastructure. |
| `--save-intermediates` | boolean |  |  |  |  |  | Save intermediate results such as QIIME2's qza and qzv files |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |
| `--multiqc-title` | string |  | yes |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |

## multiregion_taxonomic_database

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--sidle-ref-aln-custom` | string (file path) |  |  |  | matches ^.*\.(fasta\|fas\|fna\|fa\|ffn)$ |  | Path to multiple sequence alignment of reference taxonomy sequences in fasta format |
| `--sidle-ref-cleaning` | string |  |  |  |  |  | Arguments for `qiime sidle reconstruct-taxonomy` regarding ad-hoc cleaning |
| `--sidle-ref-degenerates` | integer |  |  |  |  | 5 | Exclude reference sequences with more than this much degenerates |
| `--sidle-ref-seq-custom` | string (file path) |  |  |  | matches ^.*\.(fasta\|fas\|fna\|fa\|ffn)$ |  | Path to reference taxonomy sequences in fasta format |
| `--sidle-ref-tax-custom` | string (file path) |  |  |  | matches ^.*\.txt$ |  | Path to reference taxonomy strings (headerless, *.txt) |
| `--sidle-ref-taxonomy` | string |  |  | `silva`, `silva=128`, `greengenes`, `greengenes=13_8`, `greengenes88` |  |  | Name of supported database, and optionally also version number |
| `--sidle-ref-tree-custom` | string (file path) |  |  |  | matches ^.*\.qza$ |  | Path to SIDLE reference taxonomy tree (*.qza) |

## pipeline_report

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--report-abstract` | string (file path) |  |  |  |  |  | Path to Markdown file (md) that replaces the 'Abstract' section |
| `--report-css` | string |  |  |  |  | ${projectDir}/assets/nf-core_style.css | Path to style file (css) |
| `--report-logo` | string |  |  |  |  | ${projectDir}/assets/nf-core-ampliseq_logo_light_long.png | Path to logo file (png) |
| `--report-template` | string |  |  |  |  | ${projectDir}/assets/report_template.Rmd | Path to Markdown file (Rmd) |
| `--report-title` | string |  |  |  |  | Summary of analysis results | String used as report title |

## primer_removal

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cutadapt-max-error-rate` | number |  |  |  |  | 0.1 | Sets the maximum error rate for valid matches of primer sequences with reads for cutadapt (-e). |
| `--cutadapt-min-overlap` | integer |  |  |  |  | 3 | Sets the minimum overlap for valid matches of primer sequences with reads for cutadapt (-O). |
| `--double-primer` | boolean |  |  |  |  |  | Cutadapt will be run twice to ensure removal of potential double primers |
| `--ignore-failed-trimming` | boolean |  |  |  |  |  | Ignore files with too few reads after trimming. |
| `--retain-untrimmed` | boolean |  |  |  |  |  | Cutadapt will retain untrimmed reads, choose only if input reads are not expected to contain primer sequences. |

## read_trimming_and_quality_filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ignore-failed-filtering` | boolean |  |  |  |  |  | Ignore files with too few reads after quality filtering. |
| `--max-ee` | integer |  |  |  |  | 2 | DADA2 read filtering option |
| `--max-ee-r` | integer |  |  |  |  |  | DADA2 read filtering option for reverse reads, overriding --max_ee for reverse reads only (paired-end Illumina data only) |
| `--max-len` | integer |  |  |  |  |  | DADA2 read filtering option |
| `--min-len` | integer |  |  |  |  | 50 | DADA2 read filtering option |
| `--trunc-qmin` | integer |  |  |  |  | 25 | If --trunclenf and --trunclenr are not set, these values will be automatically determined using this median quality score |
| `--trunc-rmin` | number |  |  |  | ≥ 0; ≤ 1 | 0.75 | Assures that values chosen with --trunc_qmin will retain a fraction of reads. |
| `--trunclenf` | integer |  |  |  |  |  | DADA2 read truncation value for forward strand, set this to 0 for no truncation |
| `--trunclenr` | integer |  |  |  |  |  | DADA2 read truncation value for reverse strand, set this to 0 for no truncation |
| `--truncq` | integer |  |  |  | ≥ 0 | 2 | Truncate each read at the first instance of a quality score less than or equal to `--truncq`. |

## running_specific_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--run-pplace` | boolean |  |  |  |  | false | Run phylogenetic placement when reference trees are specified by the selected `--dada_ref_taxonomy` |

## sequencing_input

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--binned-quality` | string |  |  |  | matches ^[0-9]+(,[0-9]+)*$ |  | Comma separated quality bins for DADA2. If data has binned quality scores. |
| `--ignore-binned-quality` | boolean |  |  |  |  |  | Ignore warnings about binned quality scores. |
| `--ignore-empty-input-files` | boolean |  |  |  |  |  | Ignore input files with too few reads. |
| `--illumina-pe-readthrough` | boolean |  |  |  |  |  | If analyzing Illumina paired end reads of an amplicon with large length variability such as ITS |
| `--min-read-counts` | integer |  |  |  |  | 1 | Set read count threshold for failed samples. |
| `--quality-type` | string |  |  | `Auto`, `FastqQuality`, `SFastqQuality` |  | Auto | Type of quality scores in raw read data for DADA2 |
| `--sequencing-type` | string |  |  | `illumina_pe`, `illumina_se`, `iontorrent`, `pacbio`, `nanopore` |  | illumina_pe | Sequencing technology of the data, determines analyze settings and tools. |

## skipping_specific_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-abundance-tables` | boolean |  |  |  |  |  | Skip producing any relative abundance tables |
| `--skip-alpha-rarefaction` | boolean |  |  |  |  |  | Skip alpha rarefaction |
| `--skip-barplot` | boolean |  |  |  |  |  | Skip producing barplot |
| `--skip-barrnap` | boolean |  |  |  |  |  | Skip annotating SSU matches. |
| `--skip-chopper` | boolean |  |  |  |  |  | Skip quality filtering with Chopper (ONT reads). |
| `--skip-cutadapt` | boolean |  |  |  |  |  | Skip primer trimming with cutadapt. This is not recommended! Use only in case primer sequences were removed before and the data does not contain any primer sequences. |
| `--skip-dada-addspecies` | boolean |  |  |  |  |  | Skip species level when using DADA2 for taxonomic classification. This reduces the required memory dramatically under certain conditions. |
| `--skip-dada-quality` | boolean |  |  |  |  |  | Skip quality check with DADA2. Can only be skipped when `--trunclenf` and `--trunclenr` are set. |
| `--skip-dada-taxonomy` | boolean |  |  |  |  |  | Skip taxonomic classification with DADA2 |
| `--skip-diversity-indices` | boolean |  |  |  |  |  | Skip alpha and beta diversity analysis |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC reporting |
| `--skip-parquet-summary` | boolean |  |  |  |  |  | Skip writing summary tables as Parquet, alongside the default gzipped tsv |
| `--skip-phyloseq` | boolean |  |  |  |  |  | Skip exporting phyloseq rds object(s) |
| `--skip-porechop-abi` | boolean |  |  |  |  |  | Skip adapter trimming with porechop_ABI (ONT reads). |
| `--skip-qiime` | boolean |  |  |  |  |  | Skip all steps that are executed by QIIME2, including QIIME2 software download, taxonomy assignment by QIIME2, barplots, relative abundance tables, diversity analysis, differential abundance testing. |
| `--skip-qiime-downstream` | boolean |  |  |  |  |  | Skip steps that are executed by QIIME2 except for taxonomic classification. Skip steps including barplots, relative abundance tables, diversity analysis, differential abundance testing. |
| `--skip-report` | boolean |  |  |  |  |  | Skip Markdown summary report |
| `--skip-taxonomy` | boolean |  |  |  |  |  | Skip taxonomic classification. |
| `--skip-tse` | boolean |  |  |  |  |  | Skip exporting TreeSummarizedExperiment rds object(s) |

## taxonomic_assignment

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--addsh` | boolean |  |  |  |  |  | If ASVs should be assigned to UNITE species hypotheses (SHs). Only relevant for ITS data. |
| `--consolidate-taxonomies` | string |  |  | `first`, `most-specific`, `score` |  | first | How to pick one DADA2 taxonomy per ASV when `--dada_ref_taxonomy` lists several databases |
| `--cut-dada-ref-taxonomy` | boolean |  |  |  |  |  | If the expected amplified sequences are extracted from the DADA2 reference taxonomy database |
| `--cut-its` | string |  |  | `none`, `full`, `its1`, `its2` |  | none | Part of ITS region to use for taxonomy assignment: "full", "its1", or "its2" |
| `--dada-addspecies-allowmultiple` | boolean |  |  |  |  |  | If multiple exact matches against different species are returned |
| `--dada-assign-chunksize` | integer |  |  |  |  | 10000 | ASV fasta will be subset into chunks of this size for classification |
| `--dada-assign-taxlevels` | string |  |  |  |  |  | Comma separated list of taxonomic levels used in DADA2's assignTaxonomy function |
| `--dada-min-boot` | integer |  |  |  | ≥ 0; ≤ 100 | 50 | The minimum bootstrap confidence (out of 100 trials) for assigning a taxonomic level with DADA2. Matches `minBoot` in DADA2's assignTaxonomy method. |
| `--dada-ref-tax-custom` | string (file path) |  |  |  |  |  | Path to a custom DADA2 reference taxonomy database |
| `--dada-ref-tax-custom-sp` | string (file path) |  |  |  |  |  | Path to a custom DADA2 reference taxonomy database for species assignment |
| `--dada-ref-taxonomy` | string |  |  |  |  | sbdi-gtdb=R11-RS232-1 | Name of supported database(s), and optionally also version number(s) -- comma-separated for multiple databases |
| `--dada-taxonomy-rc` | boolean |  |  |  |  |  | If reverse-complement of each sequences will be also tested for classification |
| `--its-extractor` | string |  |  | `itsx`, `itsxrust` |  | itsx | Tool for ITS region extraction: "itsx" or "itsxrust". |
| `--its-partial` | integer |  |  |  |  | 0 | Cutoff for partial ITS sequences. Only full sequences by default. |
| `--kraken2-assign-taxlevels` | string |  |  |  |  |  | Comma separated list of taxonomic levels used in Kraken2. Will overwrite default values. |
| `--kraken2-confidence` | number |  |  |  | ≥ 0; ≤ 1 | 0.0 | Confidence score threshold for taxonomic classification. |
| `--kraken2-ref-tax-custom` | string (file path) |  |  |  |  |  | Path to a custom Kraken2 reference taxonomy database (*.tar.gz\|*.tgz archive or folder) |
| `--kraken2-ref-taxonomy` | string |  |  | `silva`, `silva=138`, `silva=132`, `rdp`, `rdp=18`, `greengenes`, `greengenes=13.5`, `standard`, `standard=20260626`, `standard=20240904`, `standard=20230605` |  |  | Name of supported database, and optionally also version number |
| `--pplace-aln` | string (file path) |  |  |  |  |  | File with reference sequences. Requires also `--pplace_tree` and `--pplace_model`. |
| `--pplace-alnmethod` | string |  |  | `clustalo`, `hmmer`, `mafft` |  | clustalo | Method used for alignment, "clustalo", "hmmer" or "mafft" |
| `--pplace-model` | string |  |  |  |  |  | Phylogenetic model to use in placement, e.g. 'LG+F' or 'GTR+I+F'. Requires also `--pplace_tree` and `--pplace_aln`. |
| `--pplace-name` | string |  | yes |  |  |  | A name for the run |
| `--pplace-sheet` | string (file path) |  |  |  | matches ^\S+\.(tsv\|csv\|yml\|yaml\|txt)$ |  | Spreadsheet with phylogenetic placement information. Possible columns: target, alignmethod, hmm, extract_hmm, align_hmm, align_extract_hmm, refseqfile, refphylogeny, model, taxonomy. |
| `--pplace-taxonomy` | string (file path) |  |  |  |  |  | Tab-separated file with taxonomy assignments of reference sequences. |
| `--pplace-tree` | string (file path) |  |  |  |  |  | Newick file with reference phylogenetic tree. Requires also `--pplace_aln` and `--pplace_model`. |
| `--qiime-classifier` | string (file path) |  |  |  |  |  | Path to QIIME2 trained classifier file (typically *-classifier.qza) |
| `--qiime-ref-tax-custom` | string |  |  |  |  |  | Path to files of a custom QIIME2 reference taxonomy database (tarball, or two comma-separated files) |
| `--qiime-ref-taxonomy` | string |  |  | `silva=138`, `silva`, `greengenes85`, `greengenes2`, `greengenes2=2024.09`, `greengenes2=2022.10` |  |  | Name of supported database, and optionally also version number |
| `--sintax-assign-taxlevels` | string |  |  |  |  |  | Comma separated list of taxonomic levels used in SINTAX with a custom reference database |
| `--sintax-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | 0.8 | Confidence cutoff for SINTAX taxonomic classification. |
| `--sintax-ref-tax-custom` | string (file path) |  |  |  |  |  | Path to a custom SINTAX reference database (fasta) |
| `--sintax-ref-taxonomy` | string |  |  | `coidb`, `coidb=221216`, `unite-fungi`, `unite-fungi=10.0`, `unite-fungi=9.0`, `unite-fungi=8.3`, `unite-fungi=8.2`, `unite-alleuk`, `unite-alleuk=10.0`, `unite-alleuk=9.0`, `unite-alleuk=8.3`, `unite-alleuk=8.2` |  |  | Name of supported database, and optionally also version number |
| `--vsearch-lca-assign-taxlevels` | string |  |  |  |  |  | Comma separated list of taxonomic levels for VSEARCH LCA with a custom reference database |
| `--vsearch-lca-id` | number |  |  |  | ≥ 0; ≤ 1 | 0.9 | VSEARCH usearch_global identity cutoff (`--id`) used for VSEARCH LCA. |
| `--vsearch-lca-lca-cutoff` | number |  |  |  | ≥ 0.5; ≤ 1 | 0.9 | LCA support threshold for VSEARCH LCA (`--lca_cutoff`). |
| `--vsearch-lca-maxaccepts` | integer |  |  |  | ≥ 0 | 0 | Maximum number of target sequences to accept per query for VSEARCH LCA (`--maxaccepts`). |
| `--vsearch-lca-maxrejects` | integer |  |  |  | ≥ 0 | 0 | Maximum number of non-matching target sequences to reject per query for VSEARCH LCA (`--maxrejects`). |
| `--vsearch-lca-query-cov` | number |  |  |  | ≥ 0; ≤ 1 | 1.0 | Minimum fraction of the query that must align to a target for VSEARCH LCA (`--query_cov`). |
| `--vsearch-lca-ref-tax-custom` | string (file path) |  |  |  |  |  | Path to a custom VSEARCH LCA reference database (SINTAX-compatible FASTA) |
| `--vsearch-lca-ref-taxonomy` | string |  |  | `coidb`, `coidb=221216`, `midori2-co1`, `midori2-co1=gb270`, `unite-fungi`, `unite-fungi=10.0`, `unite-fungi=9.0`, `unite-fungi=8.3`, `unite-fungi=8.2`, `unite-alleuk`, `unite-alleuk=10.0`, `unite-alleuk=9.0`, `unite-alleuk=8.3`, `unite-alleuk=8.2` |  |  | Name of built-in VSEARCH LCA reference database, and optionally also version number |

<!-- Generated from nf-core/ampliseq@992e6df34065067185b5e34665b5861b6827981d. Do not edit by hand. -->
