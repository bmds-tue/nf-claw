---
name: rnavar
version: 1.3.0
commit: a0e4641409eb7aed4b325e543d20577f9c08e437
---

# rnavar — full parameter reference

nf-core/rnavar pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string | yes |  | `star` |  | star | Specifies the alignment algorithm to use. |
| `--bam-csi-index` | boolean |  |  |  |  |  | Create a CSI index for BAM files instead of the traditional BAI index. This will be required for genomes with larger chromosome sizes. |
| `--save-align-intermeds` | boolean |  |  |  |  |  | Save the intermediate BAM files from the alignment step. |
| `--save-unaligned` | boolean |  |  |  |  |  | Where possible, save unaligned reads from aligner to the results directory. |
| `--seq-center` | string |  |  |  |  |  | Sequencing center information to be added to read group of BAM files. |
| `--seq-platform` | string | yes |  |  |  | illumina | Specify the sequencing platform used |
| `--star-bins-bamsort` | integer |  |  |  | ≥ 0 | 50 | Specifies the number of genome bins for coordinate-sorting |
| `--star-ignore-sjdbgtf` | boolean |  |  |  |  |  | Do not use GTF file during STAR index building step |
| `--star-max-collapsed-junc` | integer |  |  |  | ≥ 0 | 1000000 | Specifies the maximum number of collapsed junctions |
| `--star-max-intron-size` | integer or string |  |  |  | ≥ 0 |  | Specifies the maximum intron size |
| `--star-max-memory-bamsort` | integer |  |  |  | ≥ 0 | 0 | Option to limit RAM when sorting BAM file. Value to be specified in bytes. If 0, will be set to the genome index size. |
| `--star-twopass` | boolean |  |  |  |  | true | Enable STAR 2-pass mapping mode. |

## general_reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--download-cache` | boolean |  |  |  |  |  | Download annotation cache. |
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  |  |  |  |  | Do not load the iGenomes reference config. |
| `--save-reference` | boolean |  |  |  |  |  | Save built references. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/ | Base URL or local path to location of pipeline test dataset files |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/rnavar/data/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--extract-umi` | boolean |  |  |  |  |  | Specify whether to remove UMIs from the reads with UMI-tools extract. This parameter will be replaced with `--tools umitools` in future release. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.(csv\|tsv\|yaml\|yml\|json)$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-merged-fastq` | boolean |  |  |  |  |  | Save FastQ files after merging re-sequenced libraries in the results directory. |
| `--skip-baserecalibration` | boolean |  |  |  |  |  | Skip the process of base recalibration steps i.e., GATK BaseRecalibrator and GATK ApplyBQSR. |
| `--skip-exon-bed-check` | boolean |  |  |  |  |  | Skip the check of the exon bed |
| `--skip-intervallisttools` | boolean |  |  |  |  |  | Skip the process of preparing interval lists for the GATK variant calling step |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC reports |
| `--skip-tools` | string |  | yes |  | matches ^((baserecalibrator\|intervallisttools\|multiqc\|removeunknownregions\|variantfiltration)*(,)*)*$ |  | Specify which tools RNAvar should skip. Values can be 'baserecalibrator', 'intervallisttools', 'multiqc', 'removeunknownregions' and 'variantfiltration' |
| `--skip-variantfiltration` | boolean |  |  |  |  |  | Skip variant filtering of GATK |
| `--tools` | string |  | yes |  | matches ^((umitools\|seq2hla\|bcfann\|snpeff\|vep\|merge)*(,)*)*$ |  | Specify which additional tools RNAvar should use. Values can be 'seq2hla', 'umitools', 'bcfann', 'snpeff', 'vep' or 'merge'. If you specify 'merge', the pipeline runs both snpeff and VEP annotation. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## postprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--remove-duplicates` | boolean |  |  |  |  |  | Specify whether to remove duplicates from the BAM during Picard MarkDuplicates step. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dbsnp` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz$ |  | Path to dbsnp file. |
| `--dbsnp-tbi` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz\.tbi$ |  | Path to dbsnp index. |
| `--dict` | string (file path) |  |  |  | matches ^\S+\.dict$ |  | Path to FASTA dictionary file. |
| `--exon-bed` | string (file path) |  |  |  | matches ^\S+\.bed$ |  | Path to BED file containing exon intervals. This will be created from the GTF file if not specified. |
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--fasta-fai` | string (file path) |  |  |  |  |  | Path to FASTA reference index. |
| `--feature-type` | string |  |  | `exon`, `transcript`, `gene` |  | exon | Type of feature to parse from annotation file |
| `--genome` | string |  |  |  |  | GRCh38 | Name of iGenomes reference. |
| `--gff` | string (file path) |  |  |  | matches ^\S+\.gff\d?$ |  | Path to GFF3 annotation file. |
| `--gtf` | string (file path) |  |  |  | matches ^\S+\.gtf$ |  | Path to GTF annotation file. |
| `--known-indels` | string (file path glob) |  |  |  |  |  | Path to known indels file. |
| `--known-indels-tbi` | string (file path glob) |  |  |  |  |  | Path to known indels file index. |
| `--read-length` | number |  |  |  | ≥ 1 | 150 | Read length |
| `--snpeff-db` | string |  |  |  |  |  | snpEff DB version. |
| `--star-index` | string (file or directory path) |  |  |  |  |  | Path to STAR index folder or compressed file (tar.gz) |
| `--vep-cache-version` | integer or string |  |  |  | ≥ 1 |  | VEP cache version. |
| `--vep-genome` | string |  |  |  |  |  | VEP genome. |
| `--vep-species` | string |  |  |  |  |  | VEP species. |

## umitools_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--umitools-bc-pattern` | string |  |  |  | matches ^[NXC]*$ |  | The UMI barcode pattern to use e.g. 'NNNNNN' indicates that the first 6 nucleotides of the read are from the UMI. |
| `--umitools-bc-pattern2` | string |  |  |  | matches ^[NXC]*$ |  | The UMI barcode pattern to use if the UMI is located in read 2. |
| `--umitools-extract-method` | string |  |  | `string`, `regex` |  | string | UMI pattern to use. Can be either 'string' (default) or 'regex'. |
| `--umitools-umi-separator` | string |  |  |  |  |  | The character that separates the UMI in the read name. Most likely a colon if you skipped the extraction with UMI-tools and used other software. |

## variant_annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bcftools-annotations` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz$ |  | A vcf file containing custom annotations to be used with bcftools annotate. Needs to be bgzipped. |
| `--bcftools-annotations-tbi` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz\.tbi$ |  | Index file for `bcftools_annotations` |
| `--bcftools-columns` | string |  |  |  |  |  | Optional text file with list of columns to use from `bcftools_annotations`, one name per row |
| `--bcftools-header-lines` | string |  |  |  |  |  | Text file with the header lines of `bcftools_annotations` |
| `--dbnsfp` | string (file path) |  |  |  | matches ^\S+\.gz$ |  | Path to dbNSFP processed file. |
| `--dbnsfp-consequence` | string |  |  |  |  |  | Consequence to annotate with |
| `--dbnsfp-fields` | string |  |  |  |  | rs_dbSNP,HGVSc_VEP,HGVSp_VEP,1000Gp3_EAS_AF,1000Gp3_AMR_AF,LRT_score,GERP++_RS,gnomAD_exomes_AF | Fields to annotate with |
| `--dbnsfp-tbi` | string (file path) |  |  |  | matches ^\S+\.tbi$ |  | Path to dbNSFP tabix indexed file. |
| `--outdir-cache` | string (directory path) |  | yes |  |  |  | The output directory where the cache will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--snpeff-cache` | string (directory path) |  |  |  |  | s3://annotation-cache/snpeff_cache/ | Path to snpEff cache. |
| `--spliceai-indel` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz$ |  | Path to spliceai raw scores indel file. |
| `--spliceai-indel-tbi` | string (file path) |  |  |  | matches ^\S+\.tbi$ |  | Path to spliceai raw scores indel tabix indexed file. |
| `--spliceai-snv` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz$ |  | Path to spliceai raw scores snv file. |
| `--spliceai-snv-tbi` | string (file path) |  |  |  | matches ^\S+\.tbi$ |  | Path to spliceai raw scores snv tabix indexed file. |
| `--vep-cache` | string (directory path) |  |  |  |  | s3://annotation-cache/vep_cache/ | Path to VEP cache. |
| `--vep-cache-preflight-check` | boolean |  |  |  |  |  | Force preflight check for local VEP cache download |
| `--vep-custom-args` | string |  |  |  |  | --everything --filter_common --per_gene --total_length --offline --format vcf | Add an extra custom argument to VEP. |
| `--vep-dbnsfp` | boolean |  |  |  |  |  | Enable the use of the VEP dbNSFP plugin. |
| `--vep-include-fasta` | boolean |  | yes |  |  |  | Allow usage of fasta file for annotation with VEP |
| `--vep-loftee` | boolean |  |  |  |  |  | Enable the use of the VEP LOFTEE plugin. |
| `--vep-out-format` | string |  | yes | `json`, `tab`, `vcf` |  | vcf | VEP output-file format. |
| `--vep-spliceai` | boolean |  |  |  |  |  | Enable the use of the VEP SpliceAI plugin. |
| `--vep-spliceregion` | boolean |  |  |  |  |  | Enable the use of the VEP SpliceRegion plugin. |
| `--vep-version` | string |  |  |  |  | 115.2-1 | Should reflect the VEP version used in the container. |

## variant_calling

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gatk-hc-call-conf` | integer |  |  |  | ≥ 0 | 20 | The minimum phred-scaled confidence threshold at which variants should be called. |
| `--gatk-interval-scatter-count` | integer |  |  |  | ≥ 1 | 25 | Number of times the gene interval list to be split in order to run GATK haplotype caller in parallel |
| `--generate-gvcf` | boolean |  |  |  |  |  | Enable generation of GVCFs by sample additionnaly to the VCFs. |
| `--no-intervals` | boolean |  |  |  |  |  | Do not use gene interval file during variant calling |

## variant_filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gatk-vf-cluster-size` | integer |  |  |  | ≥ 2 | 3 | The number of SNPs which make up a cluster. Must be at least 2. |
| `--gatk-vf-fs-filter` | number |  |  |  | ≥ 0 | 30 | Value to be used for the FisherStrand (FS) filter |
| `--gatk-vf-qd-filter` | number |  |  |  | ≥ 0 | 2 | Value to be used for the QualByDepth (QD) filter |
| `--gatk-vf-window-size` | integer |  |  |  | ≥ 0 | 35 | The window size (in bases) in which to evaluate clustered SNPs. |

<!-- Generated from nf-core/rnavar@a0e4641409eb7aed4b325e543d20577f9c08e437. Do not edit by hand. -->
