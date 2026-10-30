---
name: rnadnavar
version: 1.0.0
commit: 8e8debdb0e7208218a4a2f852de7c741a69ca448
---

# rnadnavar — full parameter reference

nf-core/rnadnavar pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `bwa-mem`, `bwa-mem2`, `dragmap` |  | `bwa-mem` | Specify aligner to be used to map reads to reference genome. |
| `--bam-csi-index` | boolean |  |  |  |  |  | Create a CSI index for BAM files instead of the traditional BAI index. This will be required for genomes with larger chromosome sizes. |
| `--save-align-intermeds` | boolean |  |  |  |  |  | Save the intermediate BAM files from the alignment step. |
| `--save-unaligned` | boolean |  |  |  |  |  | Where possible, save unaligned reads from aligner to the results directory. |

## annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dbnsfp` | string |  | yes |  |  |  | Path to dbNSFP processed file. |
| `--dbnsfp-consequence` | string |  | yes |  |  |  | Consequence to annotate with |
| `--dbnsfp-fields` | string |  | yes |  |  | `rs_dbSNP,HGVSc_VEP,HGVSp_VEP,1000Gp3_EAS_AF,1000Gp3_AMR_AF,LRT_score,GERP++_RS,gnomAD_exomes_AF` | Fields to annotate with |
| `--dbnsfp-tbi` | string |  | yes |  |  |  | Path to dbNSFP tabix indexed file. |
| `--igenomes-base` | string |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--outdir-cache` | string (directory path) |  | yes |  |  |  | The output directory where the cache will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--spliceai-indel` | string |  | yes |  |  |  | Path to spliceai raw scores indel file. |
| `--spliceai-indel-tbi` | string |  | yes |  |  |  | Path to spliceai raw scores indel tabix indexed file. |
| `--spliceai-snv` | string |  | yes |  |  |  | Path to spliceai raw scores snv file. |
| `--spliceai-snv-tbi` | string |  | yes |  |  |  | Path to spliceai raw scores snv tabix indexed file. |
| `--vep-cache` | string |  | yes |  |  |  | Path to VEP cache. |
| `--vep-custom-args` | string |  | yes |  |  | `--no_progress --offline --shift_hgvs 1 --check_existing --tsl --domains --total_length --allele_number --no_escape --xref_refseq --failed 1 --flag_pick_allele --pick_order canonical,tsl,biotype,rank,ccds,length --format vcf --biotype --force_overwrite --sift p --polyphen p --variant_class --regulatory --allele_number --af_gnomad --af_gnomadg --gene_phenotype --hgvs --hgvsg --max_af` | Add an extra custom argument to VEP. |
| `--vep-dbnsfp` | boolean |  | yes |  |  |  | Enable the use of the VEP dbNSFP plugin. |
| `--vep-include-fasta` | boolean |  | yes |  |  |  | Allow usage of fasta file for annotation with VEP |
| `--vep-loftee` | boolean |  | yes |  |  |  | Enable the use of the VEP LOFTEE plugin. |
| `--vep-out-format` | string |  | yes | `json`, `tab`, `vcf` |  | `vcf` | VEP output-file format. |
| `--vep-spliceai` | boolean |  | yes |  |  |  | Enable the use of the VEP SpliceAI plugin. |
| `--vep-spliceregion` | boolean |  | yes |  |  |  | Enable the use of the VEP SpliceRegion plugin. |

## fastq_preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  | yes |  |  | `0` | Remove bp from the 5' end of read 1 |
| `--clip-r2` | integer |  | yes |  |  | `0` | Remove bp from the 5' end of read 2 |
| `--save-split-fastqs` | boolean |  | yes |  |  |  | If set, publishes split FASTQ files. Intended for testing purposes. |
| `--save-trimmed` | boolean |  | yes |  |  |  | Save trimmed FastQ file intermediates. |
| `--three-prime-clip-r1` | integer |  | yes |  |  | `0` | Remove bp from the 3' end of read 1 |
| `--three-prime-clip-r2` | integer |  | yes |  |  | `0` | Remove bp from the 3' end of read 2 |
| `--trim-fastq` | boolean |  |  |  |  |  | Run FastP for read trimming |
| `--trim-nextseq` | integer |  | yes |  |  | `0` | Removing poly-G tails. |

## filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--blacklist` | string |  |  |  |  |  | Path to BED file with positions to blacklist during filtering (e.g. regions difficult to map) |
| `--chain` | string |  |  |  |  |  | Chain file to do liftover - only if `secondary_pon` is provided |
| `--reference-name` | string |  |  |  |  |  | RNA filtering - name of the primary reference being used (e.g. hg38) |
| `--reference-pon` | string |  |  |  |  |  | Path to the primary RNA PoN used for RNA-specific filtering (see DOI: 10.1016/j.cels.2018.03.002) |
| `--rnaedits` | string |  |  |  |  |  | Path to BED files with RNA editing sites, comma separated if more than one |
| `--secondary-pon` | string |  |  |  |  |  | Path to the optional secondary RNA PoN used for RNA-specific filtering (see DOI: 10.1016/j.cels.2018.03.002) |
| `--secondary-reference-fasta` | string |  |  |  |  |  | Path to the optional secondary reference FASTA - only if `secondary_pon` is provided |
| `--secondary-reference-name` | string |  |  |  |  |  | RNA filtering - name of the secondary reference being used (e.g. hg19) - only if `secondary_pon` is provided |
| `--whitelist` | string |  |  |  |  |  | Path to BED file with variants to whitelist during filtering |

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
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dna` | boolean |  |  |  |  | `true` | True if there are DNA samples to be analysed |
| `--input` | string | yes |  |  |  |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--input-restart` | string (file path) |  | yes |  | matches `^\S+\.csv$` |  | Automatic retrieval for restart |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--rna` | boolean |  |  |  |  | `true` | True if there are RNA samples to be analysed |
| `--save-bam-mapped` | boolean |  |  |  |  |  | Save mapped BAMs. |
| `--save-mapped` | boolean |  |  |  |  |  | Save mapped files. |
| `--save-output-as-bam` | boolean |  |  |  |  |  | Saves output from Markduplicates & Baserecalibration as BAM file instead of CRAM |
| `--split-fastq` | integer |  |  |  |  | `50000000` | Specify how many reads each split of a FastQ file contains. Set 0 to turn off splitting at all. |
| `--step` | string |  |  | `mapping`, `markduplicates`, `splitncigar`, `prepare_recalibration`, `recalibrate`, `variant_calling`, `norm`, `consensus`, `annotate`, `filtering`, `rna_filtering`, `realignment` |  | `mapping` | Starting step |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |
| `--modules-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/` | Base path / URL for data used in the modules |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/rnadnavar/` | Base path / URL for data used in the test profiles |
| `--seq-center` | string |  | yes |  |  |  | Sequencing center information to be added to read group (CN field). |
| `--seq-platform` | string |  | yes |  |  | `ILLUMINA` | Sequencing platform information to be added to read group (PL field). |

## pipeline_stage_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-tools` | string |  |  |  | matches `^((contamination\|learnreadorientation\|baserecalibrator\|baserecalibrator_report\|bcftools\|documentation\|fastqc\|markduplicates\|markduplicates_report\|mosdepth\|multiqc\|samtools\|vcftools\|versions\|splitncigar\|realignment\|filtering\|variant_calling\|rescue)*(,)*)*$` |  | Disable specified tools. |
| `--tools` | string |  |  |  | matches `^((manta\|sage\|mutect2\|strelka\|vep\|consensus\|filtering\|norm\|rna_filtering\|vcf2maf\|preprocessing\|realignment\|rescue)*,?)*$` |  | Tools to use for variant calling and/or for annotation. |
| `--wes` | boolean |  |  |  |  |  | Enable when exome or panel data is provided. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--build-only-index` | boolean |  |  |  |  |  | Only built references. |
| `--bwa` | string |  | yes |  |  |  | Path to BWA mem indices. |
| `--bwamem2` | string |  | yes |  |  |  | Path to bwa-mem2 mem indices. |
| `--dbsnp` | string |  | yes |  |  |  | Path to dbsnp file. |
| `--dbsnp-tbi` | string |  | yes |  |  |  | Path to dbsnp index. |
| `--dict` | string |  | yes |  |  |  | Path to FASTA dictionary file. |
| `--download-cache` | boolean |  |  |  |  |  | Download annotation cache. |
| `--dragmap` | string |  | yes |  |  |  | Path to dragmap indices. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--fasta-fai` | string |  |  |  |  |  | Path to FASTA reference index. |
| `--genome` | string |  |  |  |  | `GRCh38` | Name of iGenomes reference. |
| `--germline-resource` | string |  | yes |  |  |  | Path to GATK Mutect2 Germline Resource File. |
| `--germline-resource-tbi` | string |  | yes |  |  |  | Path to GATK Mutect2 Germline Resource Index. |
| `--gff` | string |  |  |  |  |  | Path to GFF3 annotation file. |
| `--gtf` | string |  |  |  |  |  | Path to GTF annotation file. |
| `--hisat2-build-memory` | string |  |  |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `200.GB` | Minimum memory required to use splice sites and exons in the HiSAT2 index build process. |
| `--hisat2-index` | string |  |  |  |  |  | Path to STAR index folder or compressed file (tar.gz) |
| `--igenomes-ignore` | boolean |  | yes |  |  | `false` | Do not load the iGenomes reference config. |
| `--known-indels` | string |  | yes |  |  |  | Path to known indels file. |
| `--known-indels-tbi` | string |  | yes |  |  |  | Path to known indels file index. |
| `--known-snps` | string |  |  |  |  |  | If you use AWS iGenomes, this has already been set for you appropriately. Path to known snps file. |
| `--known-snps-tbi` | string |  |  |  |  |  | Path to known snps file snps. |
| `--nucleotides-per-second` | number |  |  |  |  | `200000.0` | Estimate interval size. |
| `--read-length` | number |  |  |  |  | `76.0` | Read length |
| `--save-reference` | boolean |  |  |  |  |  | Save built references. |
| `--splicesites` | string (file path) |  |  |  |  |  | Splice sites file required for HISAT2. |
| `--star-ignore-sjdbgtf` | boolean |  |  |  |  |  | Do not use GTF file during STAR index buidling step |
| `--star-index` | string |  |  |  |  |  | Path to STAR index folder or compressed file (tar.gz) |
| `--star-max-collapsed-junc` | integer |  |  |  |  | `1000000` | Specifies the maximum number of collapsed junctions |
| `--star-max-memory-bamsort` | integer |  |  |  |  | `0` | Option to limit RAM when sorting BAM file. Value to be specified in bytes. If 0, will be set to the genome index size. |
| `--star-twopass` | boolean |  |  |  |  |  | Enable STAR 2-pass mapping mode. |
| `--vep-cache-version` | number |  | yes |  |  |  | VEP cache version. |
| `--vep-genome` | string |  | yes |  |  |  | VEP genome. |
| `--vep-species` | string |  | yes |  |  |  | VEP species. |

## variant_calling

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--default-variant-callers` | string |  |  |  |  | `sage,strelka,mutect2` | Variant callers used to generate calls |
| `--ignore-soft-clipped-bases` | boolean |  | yes |  |  |  | Do not analyze soft clipped bases in the reads for GATK Mutect2. |
| `--intervals` | string |  |  |  |  |  | Path to target bed file in case of whole exome or targeted sequencing or intervals file. |
| `--joint-mutect2` | boolean |  |  |  |  |  | Runs Mutect2 in joint (multi-sample) mode for better concordance among variant calls of tumor samples from the same patient. Mutect2 outputs will be stored in a subfolder named with patient ID under `variant_calling/mutect2/` folder. Only a single normal sample per patient is allowed. Tumor-only mode is also supported. |
| `--mutect2-alleles` | string |  | yes |  |  |  | Bgzipped VCF of alleles to force-call with GATK Mutect2. |
| `--mutect2-alleles-tbi` | string |  | yes |  |  |  | Tabix index for the Mutect2 force-call alleles VCF. |
| `--no-intervals` | boolean |  |  |  |  |  | Disable usage of intervals. |
| `--pon` | string |  | yes |  |  |  | Panel-of-normals VCF (bgzipped) for GATK Mutect2 |
| `--pon-tbi` | string |  | yes |  |  |  | Index of PON panel-of-normals VCF. |
| `--sage-actionable-panel` | string |  | yes |  |  |  | Bed file with ac actionable list of variants used as input in Sage variant caller |
| `--sage-custom-args` | string |  | yes |  |  |  | Custom parameters for SAGE |
| `--sage-ensembl-dir` | string |  | yes |  |  |  | Directory or tar.gz to ensembl cache for SAGE |
| `--sage-high-confidence` | string |  | yes |  |  |  | Bed file with known high confidence used as input in Sage variant caller |
| `--sage-known-hotspots` | string |  | yes |  |  |  | Known hotspots used as input in Sage variant caller |

<!-- Generated from nf-core/rnadnavar@8e8debdb0e7208218a4a2f852de7c741a69ca448. Do not edit by hand. -->
