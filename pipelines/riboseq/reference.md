---
name: riboseq
version: 2.0.0
commit: 11d66a3b8ae1f41f9c385af36bd431c35bf015ab
---

# riboseq — full parameter reference

nf-core/riboseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `star` |  | `star` | Specifies the alignment algorithm to use - available options are currently 'star'. |
| `--bam-csi-index` | boolean |  |  |  |  |  | Create a CSI index for BAM files instead of the traditional BAI index. This will be required for genomes with larger chromosome sizes. |
| `--extra-kallisto-quant-args` | string |  |  |  |  |  | Extra arguments to pass to the kallisto quant command in addition to defaults defined by the pipeline. |
| `--extra-salmon-quant-args` | string |  |  |  |  |  | Extra arguments to pass to Salmon quant command in addition to defaults defined by the pipeline. |
| `--extra-star-align-args` | string |  |  |  |  |  | Extra arguments to pass to STAR alignment command in addition to defaults defined by the pipeline. Only available for the STAR-Salmon route. |
| `--kallisto-quant-fraglen` | integer |  |  |  |  |  | Estimated average fragment length required by kallisto for single-end libraries. |
| `--kallisto-quant-fraglen-sd` | integer |  |  |  |  |  | Estimated standard deviation of the fragment length required by kallisto for single-end libraries. |
| `--pseudo-aligner` | string |  |  | `salmon`, `kallisto` |  | `salmon` | Pseudo-aligner used for translational efficiency quantification under `--te_quantification_method pseudo`. |
| `--pseudo-aligner-kmer-size` | integer |  |  |  | ≥ 1 | `23` | Kmer length passed to Salmon indexing for pseudo-alignment quantification. |
| `--salmon-quant-libtype` | string |  |  | `A`, `IS`, `ISF`, `ISR`, `IU`, `MS`, `MSF`, `MSR`, `MU`, `OS`, `OSF`, `OSR`, `OU`, `SF`, `SR`, `U` |  |  | Override Salmon library type inferred based on strandedness defined in meta object. |
| `--seq-center` | string |  |  |  |  |  | Sequencing center information to be added to read group of BAM files. |
| `--star-ignore-sjdbgtf` | boolean |  |  |  |  |  | When using pre-built STAR indices do not re-extract and use splice junctions from the GTF file. |
| `--stranded-threshold` | number |  |  |  | ≥ 0.5; ≤ 1 | `0.8` | The fraction of stranded reads that must be assigned to a strandedness for confident assignment. Must be at least 0.5. |
| `--unstranded-threshold` | number |  |  |  | ≥ 0; ≤ 1 | `0.1` | The difference in fraction of stranded reads assigned to 'forward' and 'reverse' below which a sample is classified as 'unstranded'. By default the forward and reverse fractions must differ by less than 0.1 for the sample to be called as unstranded. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  |  | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string (file path) |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string (file path) |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
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
| `--contrasts` | string (file path) |  |  |  | matches `^\S+\.(csv\|tsv\|txt)$` |  | A CSV file describing sample contrasts |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.(csv\|tsv\|json\|yaml\|yml)$` |  | Path to comma-separated file containing information about the samples in the experiment. |
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
| `--test-data-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/riboseq/testdata/` | Base path / URL for data used in the test profiles |

## optional_outputs

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-align-intermeds` | boolean |  |  |  |  | `true` | Save the intermediate BAM files from the alignment step. |
| `--save-bbsplit-reads` | boolean |  |  |  |  |  | If this option is specified, FastQ files split by reference will be saved in the results directory. |
| `--save-merged-fastq` | boolean |  |  |  |  |  | Save FastQ files after merging re-sequenced libraries in the results directory. |
| `--save-non-ribo-reads` | boolean |  |  |  |  |  | If this option is specified, intermediate FastQ files containing non-rRNA reads will be saved in the results directory. |
| `--save-reference` | boolean |  |  |  |  |  | Save reference files and indexes generated by the pipeline in the results directory. |
| `--save-trimmed` | boolean |  |  |  |  |  | Save the trimmed FastQ files in the results directory. |
| `--save-umi-intermeds` | boolean |  |  |  |  |  | If this option is specified, intermediate FastQ and BAM files produced by UMI-tools are also saved in the results directory. |
| `--save-unaligned` | boolean |  |  |  |  |  | Where possible, save unaligned reads from either STAR, HISAT2 or Salmon to the results directory. |

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--extended-orf-analysis` | boolean |  |  |  |  |  | Discover novel ORFs in novel intergenic transcripts (from StringTie or user-supplied --novel_gtf) by feeding the hybrid GTF to genome-BAM ORF callers (Ribo-TISH predict, Ribotricer). Also enables the cross-caller ORF catalogue and ORF-level quantification, which do not need a novel-transcript source. Default false for backward compatibility. |
| `--extra-rpbp-predictorfs-args` | string |  |  |  |  |  | Extra CLI arguments passed to `select-final-prediction-set`. |
| `--extra-rpbp-preparegenome-args` | string |  |  |  |  |  | Extra CLI arguments passed to `prepare-rpbp-genome`. |
| `--gffcompare-class-codes` | string |  |  |  |  | `u` | Comma-separated gffcompare class codes to retain when filtering novel transcripts. |
| `--novel-gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Optional user-supplied novel-transcript GTF. When provided, StringTie assembly is skipped and this GTF is used directly as the source of novel transcripts. |
| `--orf-min-callers` | integer |  |  |  | ≥ 1 | `1` | Minimum number of ORF callers that must agree for an ORF to enter the consensus catalogue view. |
| `--orf-min-samples` | integer |  |  |  | ≥ 1 | `1` | Minimum number of samples an ORF must recur in to enter the consensus catalogue view. |
| `--rrna-blacklist` | string (file path) |  |  |  | matches `^\S+\.bed(\.gz)?$` |  | Optional BED file of rRNA/repeat regions to exclude from the novel-transcript GTF (strand-aware intersect). |
| `--run-price` | boolean |  |  |  |  |  | Opt in to running PRICE as an additional ORF caller (Bayesian, slow). |
| `--run-ribotricer` | boolean |  |  |  |  |  | Opt in to running Ribotricer as an additional ORF caller. |
| `--run-rpbp` | boolean |  |  |  |  |  | Opt in to running Rp-Bp as an additional ORF caller (Bayesian, slow). |
| `--skip-bbsplit` | boolean |  |  |  |  | `true` | Skip BBSplit for removal of non-reference genome reads. |
| `--skip-coverage-tracks` | boolean |  |  |  |  |  | Skip bigWig coverage track generation. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |
| `--skip-gtf-filter` | boolean |  |  |  |  |  | Skip filtering of GTF for valid scaffolds and/ or transcript IDs. |
| `--skip-gtf-transcript-filter` | boolean |  |  |  |  |  | Skip the 'transcript_id' checking component of the GTF filtering script used in the pipeline. |
| `--skip-linting` | boolean |  |  |  |  |  | Skip linting checks during FASTQ preprocessing and filtering. |
| `--skip-markduplicates` | boolean |  |  |  |  |  | Skip picard MarkDuplicates step. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-orf-collapse` | boolean |  |  |  |  |  | Skip the peptide-level small-ORF deduplication of the cross-sample ORF catalogue. |
| `--skip-plastid` | boolean |  |  |  |  |  | Skip plastid. |
| `--skip-qc` | boolean |  |  |  |  |  | Skip all QC steps except for MultiQC. |
| `--skip-ribocode` | boolean |  |  |  |  |  | Skip RiboCode. |
| `--skip-ribotish` | boolean |  |  |  |  |  | Skip Ribo-TISH. |
| `--skip-ribowaltz` | boolean |  |  |  |  |  | Skip riboWaltz. |
| `--skip-stringtie` | boolean |  |  |  |  | `true` | Skip StringTie reference-guided transcript assembly and merge. |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip the adapter trimming step. |
| `--skip-umi-extract` | boolean |  |  |  |  |  | Skip the UMI extraction from the read in case the UMIs have been moved to the headers in advance of the pipeline run. |
| `--smorf-max-aa` | integer |  |  |  | ≥ 1 | `100` | Maximum amino-acid length flagged as a small ORF in the catalogue's `is_smorf` column. |

## read_filtering_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bbsplit-fasta-list` | string (file path) |  |  |  |  |  | Path to comma-separated file containing a list of reference genomes to filter reads against with BBSplit. You have to also explicitly set `--skip_bbsplit false` if you want to use BBSplit. |
| `--bbsplit-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built BBSplit index. |
| `--extra-fqlint-args` | string |  |  |  |  | `--disable-validator P001` | Extra arguments to pass to the fq lint command. |
| `--remove-ribo-rna` | boolean |  |  |  |  | `true` | Enable the removal of reads derived from ribosomal RNA. |
| `--ribo-database-manifest` | string (file path) |  |  |  |  | `${projectDir}/assets/rrna-db-defaults.txt` | Text file containing paths to fasta files (one per line) that will be used to create the database for rRNA removal. |
| `--ribo-removal-tool` | string |  |  | `sortmerna`, `bowtie2`, `ribodetector` |  | `sortmerna` | Specifies which tool to use for ribosomal RNA removal. |
| `--ribodetector-chunk-size` | integer |  |  |  |  | `100` | Chunk size for RiboDetector to control memory usage. |
| `--sortmerna-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built sortmerna index. |

## read_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--extra-fastp-args` | string |  |  |  |  |  | Extra arguments to pass to fastp command in addition to defaults defined by the pipeline. |
| `--extra-trimgalore-args` | string |  |  |  |  |  | Extra arguments to pass to Trim Galore! command in addition to defaults defined by the pipeline. |
| `--fastp-merge` | boolean |  |  |  |  | `false` | For paired-end data processed with fastp, merge overlapping read pairs into a single read. |
| `--min-trimmed-reads` | integer |  |  |  |  | `10000` | Minimum number of trimmed reads below which samples are removed from further processing. Some downstream steps in the pipeline will fail if this threshold is too low. |
| `--trimmer` | string |  |  | `trimgalore`, `fastp` |  | `trimgalore` | Specifies the trimming tool to use - available options are 'trimgalore' and 'fastp'. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--additional-fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | FASTA file to concatenate to genome FASTA file e.g. containing spike-in sequences. |
| `--canonical-gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Optional one-transcript-per-gene canonical GTF used as the annotation backbone for the genome-coordinate ORF callers (Ribo-TISH, Ribotricer), plastid P-site quantification and DTE. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--gencode` | boolean |  |  |  |  |  | Specify if your GTF annotation is in GENCODE format. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gff` | string (file path) |  |  |  | matches `^\S+\.gff(\.gz)?$` |  | Path to GFF3 annotation file. |
| `--gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Path to GTF annotation file. |
| `--gtf-extra-attributes` | string |  |  |  |  | `gene_name` | By default, the pipeline uses the `gene_name` field to obtain additional gene identifiers from the input GTF file when running Salmon. |
| `--gtf-group-features` | string |  |  |  |  | `gene_id` | Define the attribute type used to group features in the GTF file when running Salmon. |
| `--igenomes-base` | string |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--kallisto-index` | string (file path) |  |  |  |  |  | Path to a pre-built kallisto index file. |
| `--salmon-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built Salmon index. |
| `--star-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built STAR index. |
| `--transcript-fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA transcriptome file. |

## riboseq_specific_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--equalise-read-lengths` | boolean |  |  |  |  | `false` | Trim RNA-seq reads to match Ribo-seq read lengths before quantification. This addresses potential biases when comparing the two modalities due to different read lengths. |
| `--equalise-read-lengths-target` | integer |  |  |  | ≥ 15 |  | Target read length for RNA-seq trimming. If not specified, the average Ribo-seq read length will be derived from paired samples using seqkit stats. This parameter is required if RNA-seq samples have no paired Ribo-seq sample. |
| `--extra-anota2seq-run-args` | string |  |  |  |  |  | Extra arguments to pass to anota2seq in addition to defaults defined by the pipeline. Available options include: --gene_id_col (column name for gene IDs in count table, default: 'gene_id'), --exclude_samples_col and --exclude_samples_values (exclude samples by column value, semicolon-separated). Note: --samples_pairing_col and --samples_batch_col are automatically set from the 'pair' and 'batch' columns in the contrast file if present. |
| `--extra-deltate-args` | string |  |  |  |  |  | Extra arguments to pass to deltaTE (DESeq2) in addition to defaults defined by the pipeline. |
| `--extra-dotseq-args` | string |  |  |  |  |  | Extra arguments forwarded to the DOTSeq R template (ORF-level DTE + DOU). Accepts any of the template's `--key value` options, e.g. `--min_count`, `--stringent`, `--dispersion_modeling`, `--nullweight`, `--top_hits`. |
| `--extra-orf-anota2seq-run-args` | string |  |  |  |  |  | Extra arguments forwarded to anota2seq for the ORF-level call. Accepts the same options as the gene-level `--extra_anota2seq_run_args`. |
| `--extra-orf-deltate-args` | string |  |  |  |  |  | Extra arguments forwarded to the deltaTE DESeq2 module for the ORF-level call. Accepts the same options as the gene-level deltaTE module. |
| `--extra-plastid-make-wiggle-args` | string |  |  |  |  |  | Extra arguments to pass to plastid/make_wiggle command in addition to defaults defined by the pipeline. |
| `--extra-plastid-metagene-generate-args` | string |  |  |  |  |  | Extra arguments to pass to plastid/metagene_generate command in addition to defaults defined by the pipeline. |
| `--extra-plastid-psite-args` | string |  |  |  |  |  | Extra arguments to pass to plastid/psite command in addition to defaults defined by the pipeline. |
| `--extra-price-indexgenome-args` | string |  |  |  |  |  | Extra CLI arguments passed to `gedi -e IndexGenome`. |
| `--extra-price-price-args` | string |  |  |  |  |  | Extra CLI arguments passed to `gedi -e Price`. |
| `--extra-ribocode-gtfupdate-args` | string |  |  |  |  |  | Extra arguments to pass to the RiboCode GTFupdate command in addition to defaults defined by the pipeline. |
| `--extra-ribocode-metaplots-args` | string |  |  |  |  |  | Extra arguments to pass to the RiboCode metaplots command in addition to defaults defined by the pipeline. |
| `--extra-ribocode-prepare-args` | string |  |  |  |  |  | Extra arguments to pass to the RiboCode prepare_transcripts command in addition to defaults defined by the pipeline. |
| `--extra-ribocode-ribocode-args` | string |  |  |  |  |  | Extra arguments to pass to the RiboCode command in addition to defaults defined by the pipeline. |
| `--extra-ribotish-predict-args` | string |  |  |  |  |  | Extra arguments to pass to the ribotish predict command in addition to defaults defined by the pipeline. |
| `--extra-ribotish-quality-args` | string |  |  |  |  |  | Extra arguments to pass to the ribotish quality command in addition to defaults defined by the pipeline. |
| `--extra-ribotricer-detectorfs-args` | string |  |  |  |  |  | Extra arguments to pass to the ribotricer detect-orfs command in addition to defaults defined by the pipeline. |
| `--extra-ribotricer-prepareorfs-args` | string |  |  |  |  |  | Extra arguments to pass to the ribotricer prepare-orfs command in addition to defaults defined by the pipeline. |
| `--extra-ribowaltz-args` | string |  |  |  |  |  | Extra arguments to pass to the riboWaltz command in addition to defaults defined by the pipeline. |
| `--extra-stringtie-args` | string |  |  |  |  |  | Extra arguments to pass to per-sample StringTie in addition to defaults defined by the pipeline. |
| `--extra-stringtie-merge-args` | string |  |  |  |  |  | Extra arguments to pass to StringTie --merge (e.g. `-T 1 -f 0.1` to tighten the merged annotation). |
| `--plastid-default-psite-offset` | integer |  |  |  |  | `12` | Default p-site offset to use for read lengths where the offset cannot be determined automatically from the data. |
| `--plastid-max-length` | integer |  |  |  |  | `50` | Plastid only considers reads of at most the given length. |
| `--plastid-min-length` | integer |  |  |  |  | `15` | Plastid only considers reads of at least the given length. |
| `--ribo-lfc-threshold` | number |  |  |  |  | `0` | Minimum absolute log2 fold change for translated mRNA (Ribo-seq) to be considered significant. Set to 0 to disable. Maps to anota2seq selDeltaP / deltaTE lfc_threshold_ribo. |
| `--rna-lfc-threshold` | number |  |  |  |  | `0` | Minimum absolute log2 fold change for total mRNA to be considered significant. Set to 0 to disable. Maps to anota2seq selDeltaT / deltaTE lfc_threshold_rna. |
| `--te-lfc-threshold` | number |  |  |  |  | `0.2630344` | Minimum absolute log2 fold change for translational efficiency (TE) to be considered significant. Genes must meet both p-value and effect size thresholds. Default is log2(1.2) matching anota2seq. Maps to anota2seq selDeltaPT / deltaTE lfc_threshold_te. |
| `--te-quantification-method` | string |  |  | `alignment`, `pseudo`, `plastid_psite` |  | `plastid_psite` | Quantification method for translational efficiency analysis: 'plastid_psite' (in-frame P-site counts from plastid, default), 'alignment' (STAR -> Salmon) or 'pseudo' (Salmon pseudo-alignment). |
| `--translational-efficiency-method` | string |  |  |  | matches `^(anota2seq\|deltate\|dotseq)(,(anota2seq\|deltate\|dotseq))*$` | `anota2seq` | Comma-separated list of translational efficiency methods to run; any of `anota2seq`, `deltate`, `dotseq`. Each runs independently. `dotseq` is ORF-level only (no gene-level fit) and requires `--extended_orf_analysis true`. |

## umi_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--umi-dedup-tool` | string |  |  | `umitools`, `umicollapse` |  | `umitools` | Specifies the tool to use for UMI deduplication - available options are 'umitools' and 'umicollapse'. |
| `--umi-discard-read` | integer |  |  |  |  |  | After UMI barcode extraction discard either R1 or R2 by setting this parameter to 1 or 2, respectively. |
| `--umitools-bc-pattern` | string |  |  |  |  |  | The UMI barcode pattern to use e.g. 'NNNNNN' indicates that the first 6 nucleotides of the read are from the UMI. |
| `--umitools-bc-pattern2` | string |  |  |  |  |  | The UMI barcode pattern to use if the UMI is located in read 2. |
| `--umitools-dedup-primary-only` | boolean |  |  |  |  | `true` | Filter to primary alignments before UMI-tools dedup. |
| `--umitools-dedup-stats` | boolean |  |  |  |  |  | Generate output stats when running "umi_tools dedup". |
| `--umitools-extract-method` | string |  |  |  |  | `string` | UMI pattern to use. Can be either 'string' (default) or 'regex'. |
| `--umitools-grouping-method` | string |  |  | `unique`, `percentile`, `cluster`, `adjacency`, `directional` |  | `directional` | Method to use to determine read groups by subsuming those with similar UMIs. All methods start by identifying the reads with the same mapping position, but treat similar yet nonidentical UMIs differently. |
| `--umitools-umi-separator` | string |  |  |  |  |  | The character that separates the UMI in the read name. Most likely a colon if you skipped the extraction with UMI-tools and used other software. |
| `--with-umi` | boolean |  |  |  |  |  | Enable UMI extraction and UMI-based read deduplication for all samples unless overridden by the optional `with_umi` samplesheet column. |

<!-- Generated from nf-core/riboseq@11d66a3b8ae1f41f9c385af36bd431c35bf015ab. Do not edit by hand. -->
