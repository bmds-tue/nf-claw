---
name: sarek
version: 3.11.0
commit: 6e9b164daa2a54c98f7dda538645d340c561ac24
---

# sarek — full parameter reference

nf-core/sarek pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bcftools-annotations` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | A vcf file containing custom annotations to be used with bcftools annotate. Needs to be bgzipped. |
| `--bcftools-annotations-tbi` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz\.tbi$` |  | Index file for `bcftools_annotations` |
| `--bcftools-columns` | string |  |  |  |  |  | Optional text file with list of columns to use from `bcftools_annotations`, one name per row |
| `--bcftools-header-lines` | string |  |  |  |  |  | Text file with the header lines of `bcftools_annotations` |
| `--condel-config` | string (file path) |  |  |  |  |  | Path to Condel config file. |
| `--dbnsfp` | string (file path) |  |  |  | matches `^\S+\.gz$` |  | Path to dbNSFP processed file. |
| `--dbnsfp-consequence` | string |  |  |  |  |  | Consequence to annotate with |
| `--dbnsfp-fields` | string |  |  |  |  | `rs_dbSNP,HGVSc_VEP,HGVSp_VEP,1000Gp3_EAS_AF,1000Gp3_AMR_AF,LRT_score,GERP++_RS,gnomAD_exomes_AF` | Fields to annotate with |
| `--dbnsfp-tbi` | string (file path) |  |  |  | matches `^\S+\.gz\.(csi\|tbi)$` |  | Path to dbNSFP tabix indexed file. |
| `--mastermind-file` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | Path to Mastermind cited variants VCF file. |
| `--mastermind-mutations` | boolean |  |  |  |  |  | Mastermind plugin mutations parameter. |
| `--mastermind-url` | boolean |  |  |  |  |  | Mastermind plugin url parameter. |
| `--mastermind-var-iden` | boolean |  |  |  |  |  | Mastermind plugin var_iden parameter. |
| `--outdir-cache` | string (directory path) |  |  |  |  |  | The output directory where the cache will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--phenotypes-file` | string (file path) |  |  |  | matches `^\S+\.(gff\|gvf)(\.gz)?$` |  | Path to phenotype annotation GFF/GVF file. |
| `--phenotypes-file-tbi` | string (file path) |  |  |  | matches `^\S+\.(gff\|gvf)\.gz\.(csi\|tbi)$` |  | Path to phenotype annotation tabix indexed file. |
| `--phenotypes-include-types` | string |  |  |  | matches `^((Gene\|Variation\|QTL\|StructuralVariation\|SupportingStructuralVariation\|RegulatoryFeature)?&?)*(?<!&)$` |  | Phenotypes plugin feature types to include. |
| `--snpsift-databases` | string (file path) |  |  |  | matches `^\S+\.csv$` |  | Path to CSV samplesheet specifying SnpSift annotation databases. |
| `--spliceai-indel` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | Path to spliceai raw scores indel file. |
| `--spliceai-indel-tbi` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz\.(csi\|tbi)$` |  | Path to spliceai raw scores indel tabix indexed file. |
| `--spliceai-snv` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | Path to spliceai raw scores snv file. |
| `--spliceai-snv-tbi` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz\.(csi\|tbi)$` |  | Path to spliceai raw scores snv tabix indexed file. |
| `--vep-condel` | boolean |  |  |  |  |  | Enable the use of the VEP Condel plugin. |
| `--vep-custom-args` | string |  |  |  |  | `--everything --filter_common --per_gene --total_length --offline --format vcf` | Add an extra custom argument to VEP. |
| `--vep-dbnsfp` | boolean |  |  |  |  |  | Enable the use of the VEP dbNSFP plugin. |
| `--vep-include-fasta` | boolean |  |  |  |  |  | Allow usage of fasta file for annotation with VEP |
| `--vep-loftee` | boolean |  |  |  |  |  | Enable the use of the VEP LOFTEE plugin. |
| `--vep-mastermind` | boolean |  |  |  |  |  | Enable the use of the VEP Mastermind plugin. |
| `--vep-out-format` | string |  |  | `json`, `tab`, `vcf` |  | `vcf` | VEP output-file format. |
| `--vep-phenotypes` | boolean |  |  |  |  |  | Enable the use of the VEP Phenotypes plugin. |
| `--vep-spliceai` | boolean |  |  |  |  |  | Enable the use of the VEP SpliceAI plugin. |
| `--vep-spliceregion` | boolean |  |  |  |  |  | Enable the use of the VEP SpliceRegion plugin. |
| `--vep-version` | string |  |  |  |  | `116.3-0` | Should reflect the VEP version used in the container. |

## fastq_preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  | ≥ 0 | `0` | Remove bp from the 5' end of read 1 |
| `--clip-r2` | integer |  |  |  | ≥ 0 | `0` | Remove bp from the 5' end of read 2 |
| `--length-required` | integer |  |  |  | ≥ 1 | `15` | Minimum length of reads to keep |
| `--save-split-fastqs` | boolean |  |  |  |  |  | If set, publishes split FASTQ files. Intended for testing purposes. |
| `--save-trimmed` | boolean |  |  |  |  |  | Save trimmed FastQ file intermediates. |
| `--three-prime-clip-r1` | integer |  |  |  | ≥ 0 | `0` | Remove bp from the 3' end of read 1 |
| `--three-prime-clip-r2` | integer |  |  |  | ≥ 0 | `0` | Remove bp from the 3' end of read 2 |
| `--trim-fastq` | boolean |  |  |  |  |  | Run FastP for read trimming |
| `--trim-nextseq` | boolean |  |  |  |  |  | Removing poly-G tails. |

## general_reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--build-only-index` | boolean |  |  |  |  |  | Only built references. |
| `--download-cache` | boolean |  |  |  |  |  | Download annotation cache. |
| `--igenomes-base` | string |  |  |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  |  |  |  |  | Do not load the iGenomes reference config. |
| `--save-reference` | boolean |  |  |  |  |  | Save built references. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
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
| `--input` | string (file path) |  |  |  | matches `^\S+\.(csv\|tsv\|yaml\|yml\|json)$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--input-restart` | string (file path) |  | yes |  | matches `^\S+\.(csv\|tsv\|yaml\|yml\|json)$` |  | Automatic retrieval for restart |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--step` | string | yes |  | `mapping`, `markduplicates`, `prepare_recalibration`, `recalibrate`, `variant_calling`, `annotate` |  | `mapping` | Starting step |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |
| `--modules-testdata-base-path` | string |  | yes |  |  |  | Base path / URL for data used in the modules |
| `--seq-center` | string |  | yes |  |  |  | Sequencing center information to be added to read group (CN field). |
| `--seq-platform` | string |  | yes |  |  | `ILLUMINA` | Sequencing platform information to be added to read group (PL field). |
| `--test-data-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/sarek3` | Base path / URL for data used in the test profiles |

## main_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--intervals` | string (file path) |  |  |  | matches `\S+\.(bed\|interval_list)$` |  | Path to target bed file in case of whole exome or targeted sequencing or intervals file. |
| `--no-intervals` | boolean |  |  |  |  |  | Disable usage of intervals. |
| `--nucleotides-per-second` | integer |  |  |  | ≥ 1 | `200000` | Estimate interval size. |
| `--skip-tools` | string |  |  |  | matches `^((baserecalibrator\|baserecalibrator_report\|bcftools\|dnascope_filter\|documentation\|fastqc\|haplotypecaller_filter\|haplotyper_filter\|markduplicates\|markduplicates_report\|mosdepth\|multiqc\|samtools\|vcftools\|versions)?,?)*(?<!,)$` |  | Disable specified tools. |
| `--split-fastq` | integer |  |  |  |  | `50000000` | Specify how many reads each split of a FastQ file contains. Set 0 to turn off splitting at all. |
| `--tools` | string |  |  |  | matches `^((ascat\|bbsplit\|bcfann\|cnvkit\|controlfreec\|deepsomatic\|deepvariant\|freebayes\|haplotypecaller\|indexcov\|lofreq\|manta\|merge\|mpileup\|msisensor2\|msisensorpro\|muse\|mutect2\|ngscheckmate\|parabricks_deepsomatic\|parabricks_deepvariant\|parabricks_haplotypecaller\|sentieon_dedup\|sentieon_dnascope\|sentieon_haplotyper\|sentieon_tnscope\|snpeff\|snpsift\|strelka\|tiddit\|vep\|varlociraptor)?,?)*(?<!,)$` |  | Tools to use for contamination removal, duplicate marking, variant calling and/or for annotation. |
| `--wes` | boolean |  |  |  |  |  | Enable when exome or panel data is provided. |

## post_variant_calling

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bcftools-filter-criteria` | string |  |  |  |  | `-f PASS,.` | Filter criteria. Uses bcftools view filter options. To customize, follow instructions here: https://samtools.github.io/bcftools/bcftools.html#view |
| `--concatenate-vcfs` | boolean |  |  |  |  |  | Option for concatenating germline vcf-files. |
| `--consensus-min-count` | integer |  |  |  |  | `2` | Minimum number of variant callers calling a variant for consensus results |
| `--filter-vcfs` | boolean |  |  |  |  |  | Enable filtering of VCFs with bcftools view |
| `--normalize-vcfs` | boolean |  |  |  |  |  | Option for normalization of vcf-files. |
| `--snv-consensus-calling` | boolean |  |  |  |  |  | Enable consensus calling of multiple VCF files from one sample |
| `--varlociraptor-chunk-size` | integer |  | yes |  | ≥ 1 | `15` | Number of chunks to split the vcf-files for varlociraptor. Minimum 1, indicates no splitting |
| `--varlociraptor-events-germline` | string |  |  |  |  | `germline` | Events to consider for FDR filtering for germline samples, must match events described in scenario file. |
| `--varlociraptor-events-somatic` | string |  |  |  |  | `somatic_tumor_high somatic_tumor_low` | Events to consider for FDR filtering for somatic samples, must match events described in scenario file. |
| `--varlociraptor-events-tumor-only` | string |  |  |  |  | `somatic_tumor_high somatic_tumor_low` | Events to consider for FDR filtering for tumor only samples, must match events described in scenario file. |
| `--varlociraptor-fdr` | number |  |  |  |  | `0.05` | The probability to be a false discovery may not exceed the given threshold. |
| `--varlociraptor-scenario-germline` | string |  |  |  |  |  | Yte compatible scenario file for germline samples. Defaults to assets/varlociraptor_germline.yte.yaml |
| `--varlociraptor-scenario-somatic` | string |  |  |  |  |  | Yte compatible scenario file for somatic samples. Defaults to assets/varlociraptor_somatic.yte.yaml |
| `--varlociraptor-scenario-tumor-only` | string |  |  |  |  |  | Yte compatible scenario file for tumor only samples. Defaults to assets/varlociraptor_tumor_only.yte.yaml |

## preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `bwa-mem`, `bwa-mem2`, `dragmap`, `sentieon-bwamem`, `parabricks` |  | `bwa-mem` | Specify aligner to be used to map reads to reference genome. |
| `--markduplicates-pixel-distance` | integer |  |  |  |  |  |  |
| `--save-mapped` | boolean |  |  |  |  |  | Save mapped files. |
| `--save-output-as-bam` | boolean |  |  |  |  |  | Saves output from mapping (if `--save_mapped`), Markduplicates & Baserecalibration as BAM file instead of CRAM |
| `--sentieon-consensus` | boolean |  |  |  |  |  | Generate consensus reads with Sentieon dedup rather than choosing one best read. |
| `--use-gatk-spark` | string |  |  |  | matches `^((baserecalibrator\|markduplicates)?,?)*(?<!,)$` |  | Enable usage of GATK Spark implementation for duplicate marking and/or base quality score recalibration |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ascat-alleles` | string (file path) |  |  |  | matches `^\S+\.zip$` |  | Path to ASCAT allele zip file. |
| `--ascat-genome` | string |  |  | `hg19`, `hg38` |  |  | ASCAT genome. |
| `--ascat-loci` | string (file path) |  |  |  | matches `^\S+\.zip$` |  | Path to ASCAT loci zip file. |
| `--ascat-loci-gc` | string (file path) |  |  |  | matches `^\S+\.zip$` |  | Path to ASCAT GC content correction file. |
| `--ascat-loci-rt` | string (file path) |  |  |  | matches `^\S+\.zip$` |  | Path to ASCAT RT (replictiming) correction file. |
| `--bwa` | string (directory path) |  |  |  |  |  | Path to BWA mem indices. |
| `--bwamem2` | string (directory path) |  |  |  |  |  | Path to bwa-mem2 mem indices. |
| `--chr-dir` | string (file or directory path) |  |  |  |  |  | Path to chromosomes folder used with ControLFREEC. |
| `--dbsnp` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | Path to dbsnp file. |
| `--dbsnp-tbi` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz\.tbi$` |  | Path to dbsnp index. |
| `--dbsnp-vqsr` | string |  |  |  |  |  | Label string for VariantRecalibration (haplotypecaller joint variant calling). If you use AWS iGenomes, this has already been set for you appropriately. |
| `--dict` | string (file path) |  |  |  | matches `^\S+\.dict$` |  | Path to FASTA dictionary file. |
| `--dragmap` | string (directory path) |  |  |  |  |  | Path to dragmap indices. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--fasta-fai` | string (file path) |  |  |  |  |  | Path to FASTA reference index. |
| `--genome` | string |  |  |  |  | `GATK.GRCh38` | Name of iGenomes reference. |
| `--germline-resource` | string (file path) |  |  |  | matches `\S+\.vcf\.gz$` |  | Path to GATK Mutect2 Germline Resource File. |
| `--germline-resource-tbi` | string (file path) |  |  |  | matches `\S+\.vcf\.gz\.tbi$` |  | Path to GATK Mutect2 Germline Resource Index. |
| `--known-indels` | string (file path glob) |  |  |  |  |  | Path to known indels file. |
| `--known-indels-tbi` | string (file path glob) |  |  |  |  |  | Path to known indels file index. |
| `--known-indels-vqsr` | string |  |  |  |  |  | Label string for VariantRecalibration (haplotypecaller joint variant calling). If you use AWS iGenomes, this has already been set for you appropriately. |
| `--known-snps` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | Path to known snps file. |
| `--known-snps-tbi` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz\.tbi$` |  | Path to known snps file snps. |
| `--known-snps-vqsr` | string |  |  |  |  |  | Label string for VariantRecalibration (haplotypecaller joint variant calling).If you use AWS iGenomes, this has already been set for you appropriately. |
| `--mappability` | string (file path) |  |  |  | matches `^\S+\.gem$` |  | Path to Control-FREEC mappability file. |
| `--msisensor2-models` | string (file or directory path) |  |  |  |  |  | Path to models folder used with MSIsensor2. |
| `--msisensorpro-scan` | string (file or directory path) |  |  |  |  |  | Path to scan file used with MSIsensorPro. |
| `--ngscheckmate-bed` | string (file path) |  |  |  | matches `^\S+\.bed$` |  | Path to SNP bed file for sample checking with NGSCheckMate |
| `--sentieon-dnascope-model` | string (file path) |  |  |  | matches `^\S+\.model$` |  | Machine learning model for Sentieon Dnascope. |
| `--snpeff-cache` | string |  |  |  |  | `s3://annotation-cache/snpeff_cache/` | Path to snpEff cache. |
| `--snpeff-db` | string |  |  |  |  |  | snpEff DB version. |
| `--vep-cache` | string |  |  |  |  | `s3://annotation-cache/vep_cache/` | Path to VEP cache. |
| `--vep-cache-preflight-check` | boolean |  |  |  |  |  | Force preflight check for local VEP cache download |
| `--vep-cache-version` | string |  |  |  |  |  | VEP cache version. |
| `--vep-genome` | string |  |  |  |  |  | VEP genome. |
| `--vep-species` | string |  |  |  |  |  | VEP species. |

## umi_processing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bbsplit-fasta-list` | string (file path) |  |  |  |  |  | Path to comma-separated file containing a list of reference genomes to filter reads against with BBSplit. You have to also explicitly set `--tools bbsplit` if you want to use BBSplit. |
| `--bbsplit-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built BBSplit index. |
| `--group-by-umi-strategy` | string |  |  | `Identity`, `Edit`, `Adjacency`, `Paired` |  | `Adjacency` | Default strategy for fgbio UMI-based consensus read generation |
| `--save-bbsplit-reads` | boolean |  |  |  |  |  | If this option is specified, FastQ files split by reference will be saved in the results directory. |
| `--umi-base-skip` | integer |  |  |  | ≥ 0 |  | Number of bases to skip after the UMI(s) in the read when extracting with fastp. |
| `--umi-in-read-header` | boolean |  |  |  |  |  | Move UMIs from fastq read headers to a tag prior to deduplication. |
| `--umi-length` | integer |  |  |  | ≥ 1 |  | Length of the UMI(s) in the read. |
| `--umi-location` | string |  |  | `read1`, `read2`, `per_read`, `index1`, `index2`, `per_index` |  |  | Location of the UMI(s) to be extracted with fastp. |
| `--umi-read-structure` | string |  |  |  |  |  | Specify UMI read structure for fgbio UMI consensus read generation |
| `--umi-tag` | string |  |  |  |  |  | Tag detailing where UMIs are present inside the bam/cram file (e.g. RX). |

## variant_calling

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ascat-min-base-qual` | integer |  |  |  | ≥ 0 | `20` | Overwrite Ascat min base quality required for a read to be counted. |
| `--ascat-min-counts` | integer |  |  |  | ≥ 0 | `10` | Overwrite Ascat minimum depth required in the normal for a SNP to be considered. |
| `--ascat-min-map-qual` | integer |  |  |  | ≥ 0 | `35` | Overwrite Ascat min mapping quality required for a read to be counted. |
| `--ascat-penalty` | number |  |  |  | ≥ 0 | `70` | Set the penalty for ASCAT segmentation. |
| `--ascat-ploidy` | number |  |  |  | ≥ 0 |  | Overwrite ASCAT ploidy. |
| `--ascat-purity` | number |  |  |  |  |  | Overwrite ASCAT purity. |
| `--cf-chrom-len` | string (file path) |  |  |  | matches `^\S+\.(fai\|len)$` |  | Specify a custom chromosome length file. |
| `--cf-coeff` | number |  |  |  |  | `0.05` | Overwrite Control-FREEC coefficientOfVariation |
| `--cf-contamination` | integer |  |  |  | ≥ 0 | `0` | Design known contamination value for Control-FREEC |
| `--cf-contamination-adjustment` | boolean |  |  |  |  |  | Overwrite Control-FREEC contaminationAdjustement |
| `--cf-mincov` | integer |  |  |  | ≥ 0 | `0` | Minimal read coverage for a position to be considered in BAF analysis. |
| `--cf-minqual` | integer |  |  |  | ≥ 0 | `0` | Minimal sequencing quality for a position to be considered in BAF analysis. |
| `--cf-ploidy` | string |  |  |  |  | `2` | Genome ploidy used by ControlFREEC |
| `--cf-window` | number |  |  |  |  |  | Overwrite Control-FREEC window size. |
| `--cnvkit-reference` | string (file path) |  |  |  | matches `^\S+\.cnn$` |  | Copy-number reference for CNVkit |
| `--freebayes-filter` | string |  |  |  |  | `30` | Filtering expression for vcflib/vcffilter |
| `--gatk-pcr-indel-model` | string |  |  |  |  | `CONSERVATIVE` |  |
| `--ignore-soft-clipped-bases` | boolean |  |  |  |  |  | Do not analyze soft clipped bases in the reads for GATK Mutect2. |
| `--joint-germline` | boolean |  |  |  |  |  | Turn on the joint germline variant calling for GATK haplotypecaller |
| `--joint-mutect2` | boolean |  |  |  |  |  | Runs Mutect2 in joint (multi-sample) mode for better concordance among variant calls of tumor samples from the same patient. Mutect2 outputs will be stored in a subfolder named with patient ID under `variant_calling/mutect2/` folder. Only a single normal sample per patient is allowed. Tumor-only mode is also supported. |
| `--only-paired-variant-calling` | boolean |  |  |  |  |  | If true, skips germline variant calling for matched normal to tumor sample. Normal samples without matched tumor will still be processed through germline variant calling tools. |
| `--pon` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz$` |  | Panel-of-normals VCF (bgzipped) for GATK Mutect2 |
| `--pon-tbi` | string (file path) |  |  |  | matches `^\S+\.vcf\.gz\.tbi$` |  | Index of PON panel-of-normals VCF. |
| `--sentieon-dnascope-emit-mode` | string |  |  |  | matches `^(all\|confident\|gvcf\|variant\|gvcf,all\|gvcf,confident\|gvcf,variant\|all,gvcf\|confident,gvcf\|variant,gvcf)(?<!,)$` | `variant` | Option for selecting output and emit-mode of Sentieon's Dnascope. |
| `--sentieon-dnascope-pcr-indel-model` | string |  |  |  | matches `^(NONE\|HOSTILE\|AGGRESSIVE\|CONSERVATIVE)(?<!,)$` | `CONSERVATIVE` | Option for selecting the PCR indel model used by Sentieon Dnascope. |
| `--sentieon-haplotyper-emit-mode` | string |  |  |  | matches `^(all\|confident\|gvcf\|variant\|gvcf,all\|gvcf,confident\|gvcf,variant\|all,gvcf\|confident,gvcf\|variant,gvcf)(?<!,)$` | `variant` | Option for selecting output and emit-mode of Sentieon's Haplotyper. |

<!-- Generated from nf-core/sarek@6e9b164daa2a54c98f7dda538645d340c561ac24. Do not edit by hand. -->
