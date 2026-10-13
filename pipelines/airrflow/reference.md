---
name: airrflow
version: 5.1.2
commit: 601bbe64a4a035b531b70626eeacca9770100e6e
---

# airrflow — full parameter reference

nf-core/airrflow pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## adapter_trimming

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adapter-fasta` | string |  |  |  |  |  | Fasta file with adapter sequences to be trimmed. |
| `--clip-r1` | integer |  |  |  |  | 0 | Number of bases to clip 5' in R1 reads. |
| `--clip-r2` | integer |  |  |  |  | 0 | Number of bases to clip 5' in R2 reads. |
| `--save-trimmed` | boolean |  |  |  |  |  | Option to save trimmed reads. |
| `--three-prime-clip-r1` | integer |  |  |  |  | 0 | Number of bases to clip 3' in R1 reads. |
| `--three-prime-clip-r2` | integer |  |  |  |  | 0 | Number of bases to clip 3' in R2 reads. |
| `--trim-fastq` | boolean |  |  |  |  | true | Whether to trim adapters in fastq reads with fastp. |
| `--trim-nextseq` | boolean |  |  |  |  |  | Trim adapters specific for Nextseq sequencing |

## bulk_filtering_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--collapseby` | string |  |  |  |  | sample_id | Name of the field used to collapse duplicated sequences. |
| `--detect-contamination` | boolean |  |  |  |  |  | Whether to run the process to detect contamination. |
| `--remove-chimeric` | boolean |  |  |  |  |  | Whether to apply the chimera removal filter. |

## clonal_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clonal-threshold` | string or number |  |  |  |  | auto | Set the clustering threshold Hamming distance value. Default: 'auto' |
| `--cloneby` | string |  |  |  |  | subject_id | Name of the field used to group data files to identify clones. |
| `--crossby` | string |  |  |  |  | subject_id | Name of the field used to identify external groups used to identify a clonal threshold. |
| `--lineage-tree-builder` | string |  |  | `raxml`, `igphyml` |  | raxml | Lineage tree software to use to build trees within Dowser. If you change the default, also set the `lineage_tree_exec` parameter. |
| `--lineage-tree-exec` | string |  |  |  |  | /usr/local/bin/raxml-ng | Path to lineage tree building executable. |
| `--lineage-trees` | boolean |  |  |  |  |  | Perform clonal lineage tree analysis. |
| `--singlecell` | string |  |  |  |  | single_cell | Name of the field used to determine if a sample is single cell sequencing or not. |
| `--skip-all-clones-report` | boolean |  |  |  |  |  | Skip report of EnchantR DefineClones for all samples together. |
| `--skip-clonal-analysis` | boolean |  |  |  |  |  | Skip all clonal anlaysis processes |
| `--skip-report-threshold` | boolean |  |  |  |  |  | Skip report of EnchantR FindThreshold for all samples together. |

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
| `--multiqc-methods-description` | string |  | yes |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--multiqc-title` | string |  | yes |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/airrflow/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## genotyping_and_novel_alleles_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genotypeby` | string |  |  |  |  | subject_id | Name of the field used to group data files to infer genotype. |
| `--genotyping` | boolean |  |  |  |  |  | Perform TIgGER novel allele and genotype inference. |
| `--genotyping-clonal-threshold` | number |  |  |  |  | 0.2 | Threshold for determining if two sequences come from the same clone or not. |
| `--novel-allele-inference` | boolean |  |  |  |  |  | Perform TIgGER novel allele inference. |
| `--single-clone-representative` | boolean |  |  |  |  |  | Keep only one representative sequence per clone to perform genotype inference. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.tsv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--miairr` | string |  |  |  |  | ${projectDir}/assets/reveal/mapping_MiAIRR_BioSample_v1.3.1.tsv | Path to MiAIRR-BioSample mapping |
| `--mode` | string |  |  | `fastq`, `assembled` |  | fastq | Specify the processing mode for the pipeline. Available options are "fastq" and "assembled". |
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

## primer_input_and_positions

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cprimer-position` | string |  |  | `R1`, `R2` |  | R1 | Indicate if C region primers are in the R1 or R2 reads. |
| `--cprimer-start` | integer |  |  |  |  | 0 | Start position of C region primers (without counting the UMI barcode). |
| `--cprimers` | string |  |  |  |  |  | Path to a fasta file containing the C-region primer sequences. |
| `--primer-revpr` | boolean |  |  |  |  |  | Specify to match the tail-end of the sequence against the reverse complement of the primers. This also reverses the behavior of the --start argument, such that start position is relative to the tail-end of the sequence. (default: False)Maximum scoring error for the Presto MaxPrimer process for the C and/or V region primers identification. |
| `--vprimer-start` | integer |  |  |  |  | 0 | Start position of V region primers (without counting the UMI barcode). |
| `--vprimers` | string |  |  |  |  |  | Path to a fasta file containinc the V-region primer sequences. |

## protocol

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--library-generation-method` | string |  |  | `specific_pcr_umi`, `specific_pcr`, `dt_5p_race`, `dt_5p_race_umi`, `sc_10x_genomics`, `trust4` |  |  | Protocol used for the V(D)J amplicon sequencing library generation. |
| `--race-linker` | string |  |  |  |  |  | Path to fasta file containing the linker sequence, if no V-region primers were used but a linker sequence is present (e.g. 5' RACE SMARTer TAKARA protocol). |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  | true | Do not load the iGenomes reference config. |

## report_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--report-css` | string |  |  |  |  | ${projectDir}/assets/nf-core_style.css | Custom report style file in css format. |
| `--report-logo` | string |  |  |  |  | ${projectDir}/assets/nf-core-airrflow_logo_light.png | Custom logo for the report. |
| `--report-logo-img` | string |  |  |  |  | ${projectDir}/assets/nf-core-airrflow_logo_reports.png | Custom logo for the EnchantR reports. |
| `--report-rmd` | string |  |  |  |  | ${projectDir}/assets/repertoire_comparison.Rmd | Custom report Rmarkdown file. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip multiqc report. |
| `--skip-report` | boolean |  |  |  |  |  | Skip repertoire analysis and report generation. |

## rnaseq_based_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--trust4-barcode-whitelist` | string |  |  |  |  |  | path to the barcode whitelist. |
| `--trust4-cell-barcode-read` | string |  |  | `R1`, `R2` |  |  | Specifies which read holds the barcodes |
| `--trust4-read-format` | string |  |  |  |  |  | Specifies where in the read the barcodes and UMIs can be found. |
| `--trust4-umi-read` | string |  |  | `R1`, `R2` |  |  | Indicate if UMI indices are recorded in the R1 (default) or R2 fastq file. |

## sequence_assembly_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--align-cregion` | boolean |  |  |  |  |  | Align internal C-region for a more precise isotype characterization. |
| `--assemblepairs-sequential` | boolean |  |  |  |  |  | Use AssemblePairs sequential instead of AssemblePairs align when assembling read pairs. |
| `--buildconsensus-maxerror` | number |  |  |  |  | 0.1 | Maximum error for building the sequence consensus in the pRESTO BuildConsensus step. |
| `--buildconsensus-maxgap` | number |  |  |  |  | 0.5 | Maximum gap for building the sequence consensus in the pRESTO BuildConsensus step. |
| `--cluster-sets` | boolean |  |  |  |  | true | Cluster sequences by similarity regardless of any annotation with pRESTO ClusterSets and annotate the cluster ID additionally to the UMI barcode. |
| `--cregion-mask-mode` | string |  |  |  |  | tag | Mask mode for C-region alignment. |
| `--cregion-maxerror` | number |  |  |  |  | 0.3 | Maximum allowed error when aligning the internal C-region. |
| `--cregion-maxlen` | integer |  |  |  |  | 100 | Maximum allowed length when aligning the internal C-region. |
| `--filterseq-q` | integer |  |  |  |  | 20 | Quality threshold for pRESTO FilterSeq sequence filtering. |
| `--internal-cregion-sequences` | string |  |  |  |  |  | Provide internal C-region sequences for a more precise C-region characterization. Then also set the `align_cregion` flag. |
| `--maskprimers-align` | boolean |  |  |  |  |  | Align primers instead of scoring them. Used for protocols without primer fixed positions. |
| `--maskprimers-align-race` | boolean |  |  |  |  |  | Use MaskPrimers align for a 5' RACE protocol. |
| `--maskprimers-extract` | boolean |  |  |  |  |  | Use when primer sequences are unknown but when their approximate positions are known. |
| `--primer-consensus` | number |  |  |  |  | 0.6 | Maximum error for building the primer consensus in the pRESTO Buildconsensus step. |
| `--primer-maxlen` | integer |  |  |  |  | 50 | Maximum allowed primer length when aligning the primers. |
| `--primer-r1-extract-len` | integer |  |  |  |  | 0 | R1 primer extract length when using `--maskprimers_extract`. |
| `--primer-r1-mask-mode` | string |  |  | `cut`, `mask`, `trim`, `tag` |  | cut | Masking mode for R1 primers. |
| `--primer-r1-maxerror` | number |  |  |  |  | 0.2 | Maximum allowed error for R1 primer alignment. |
| `--primer-r2-extract-len` | integer |  |  |  |  | 0 | R2 primer extract length when using `--maskprimers_extract`. |
| `--primer-r2-mask-mode` | string |  |  | `cut`, `mask`, `trim`, `tag` |  | cut | Masking mode for R2 primers. |
| `--primer-r2-maxerror` | number |  |  |  |  | 0.2 | Maximum allowed error for R2 primer alignment. |
| `--skip-alignment-filter` | boolean |  |  |  |  |  | Skip filter step after alignment that ensures that locus should match the v_call chain, the sequence alignment should have at least 200 informative positions (excluding N or gaps), and maximum 10% N nucleotides in the alignment. |

## single_cell_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--reference-10x` | string |  |  |  |  |  | Path to the reference directory required by cellranger. Can either be directory or tar.gz. |

## translation_and_embedding_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--embedding-chain` | string |  |  |  |  | H | BCR or TCR chains to include for embedding. |
| `--embeddings` | string |  |  |  | matches ^((antiberta2\|antiberty\|balmpaired\|esm2)?,?)*(?<!,)$ |  | Generate sequence embeddings with amulety. |
| `--translate` | boolean |  |  |  |  |  | Generate a sequence amino acid translation with IgBlast. |
| `--use-gpu` | boolean |  |  |  |  |  | Use GPU to generate embeddings. |

## umi_barcode_handling

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--index-file` | boolean |  |  |  |  |  | Indicate if UMI indices are recorded in a separate index file. |
| `--umi-length` | integer |  |  |  |  | -1 | UMI barcode length in nucleotides. Set to 0 if no UMIs present. |
| `--umi-position` | string |  |  | `R1`, `R2` |  | R1 | Indicate if UMI indices are recorded in the R1 (default) or R1 fastq file. |
| `--umi-start` | integer |  |  |  |  | 0 | UMI barcode start position in the index read. |

## vdj_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fetch-germlines` | string |  |  | `none`, `imgt`, `airrc-imgt` |  | none | Fetch the selected germline reference bundle at runtime instead of using cached reference inputs. |
| `--productive-only` | boolean |  |  |  |  | true | Subset to productive sequences. |
| `--reassign` | boolean |  |  |  |  | true | Whether to reassign genes if the input file is an AIRR formatted tabulated file. |
| `--reference-fasta` | string |  |  |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/airrflow/database-cache/imgtdb_base.zip | Path to the germline reference fasta. |
| `--reference-igblast` | string |  |  |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/airrflow/database-cache/igblast_base.zip | Path to the cached igblast database. |
| `--save-germlines` | boolean |  |  |  |  | true | Save germline database to reuse the cache in future runs. |

<!-- Generated from nf-core/airrflow@601bbe64a4a035b531b70626eeacca9770100e6e. Do not edit by hand. -->
