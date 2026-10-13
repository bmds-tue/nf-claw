---
name: funcscan
version: 4.0.0
commit: aee3dc965eb0c77267435544dda30da858763913
---

# funcscan — full parameter reference

nf-core/funcscan pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## amp_ampcombi2_cluster

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amp-ampcombi-cluster-coverage` | number |  |  |  |  | 0.8 | MMseqs2 alignment coverage. |
| `--amp-ampcombi-cluster-covmode` | number |  |  |  |  | 0 | MMseqs2 coverage mode. |
| `--amp-ampcombi-cluster-keepsingletons` | boolean |  |  |  |  |  | Keep any hits that form a single member cluster. |
| `--amp-ampcombi-cluster-minmembers` | integer |  |  |  |  | 0 | Remove clusters that don't have more AMP hits than this number. |
| `--amp-ampcombi-cluster-mode` | number |  |  |  |  | 1 | MMseqs2 clustering mode. |
| `--amp-ampcombi-cluster-sensitivity` | number |  |  |  |  | 4 | Remove hits that have no stop codon upstream and downstream of the AMP. |
| `--amp-ampcombi-cluster-seqid` | number |  |  |  |  | 0.4 | MMseqs2 sequence identity. |

## amp_ampcombi2_parsetables

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amp-ampcombi-db` | string |  |  |  |  |  | The path to the folder containing the reference database files. |
| `--amp-ampcombi-db-id` | string |  |  | `DRAMP`, `APD`, `UniRef100` |  | DRAMP | The name of the database used to classify the AMPs. |
| `--amp-ampcombi-parsetables-aalength` | integer |  |  |  |  | 120 | Filter out all amino acid fragments shorter than this number. |
| `--amp-ampcombi-parsetables-ampir` | string |  |  |  |  | .ampir.tsv | Assigns the file extension used to identify AMPIR output. |
| `--amp-ampcombi-parsetables-amplify` | string |  |  |  |  | .amplify.tsv | Assigns the file extension used to identify AMPLIFY output. |
| `--amp-ampcombi-parsetables-cutoff` | number |  |  |  |  | 0.6 | Specifies the prediction tools' cut-offs. |
| `--amp-ampcombi-parsetables-dbevalue` | number |  |  |  |  | 5 | Remove all DRAMP annotations that have an e-value greater than this value. |
| `--amp-ampcombi-parsetables-hmmevalue` | number |  |  |  |  | 0.06 | Retain HMM hits that have an e-value lower than this. |
| `--amp-ampcombi-parsetables-hmmsearch` | string |  |  |  |  | .hmmer_hmmsearch.txt | Assigns the file extension used to identify HMMER/HMMSEARCH output. |
| `--amp-ampcombi-parsetables-macrel` | string |  |  |  |  | .macrel.prediction | Assigns the file extension used to identify MACREL output. |
| `--amp-ampcombi-parsetables-removehitswostopcodons` | boolean |  |  |  |  |  | Remove hits that have no stop codon upstream and downstream of the AMP. |
| `--amp-ampcombi-parsetables-windowstopcodon` | integer |  |  |  |  | 60 | Assign the number of codons used to look for stop codons, upstream and downstream of the AMP hit. |
| `--amp-ampcombi-parsetables-windowtransport` | integer |  |  |  |  | 11 | Assign the number of CDSs upstream and downstream of the AMP to look for a transport protein. |

## amp_ampir

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amp-ampir-minlength` | integer |  |  |  |  | 10 | Specify minimum protein length for prediction calculation. |
| `--amp-ampir-model` | string |  |  | `precursor`, `mature` |  | precursor | Specify which machine learning classification model to use. |
| `--amp-skip-ampir` | boolean |  |  |  |  |  | Skip ampir during AMP screening. |

## amp_amplify

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amp-skip-amplify` | boolean |  |  |  |  |  | Skip AMPlify during AMP screening. |

## amp_hmmsearch

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amp-hmmsearch-models` | string |  |  |  |  |  | Specify path to the AMP hmm model file(s) to search against. Must have quotes if wildcard used. |
| `--amp-hmmsearch-savealignments` | boolean |  |  |  |  |  | Saves a multiple alignment of all significant hits to a file. |
| `--amp-hmmsearch-savedomains` | boolean |  |  |  |  |  | Save a simple tabular file summarising the per-domain output. |
| `--amp-hmmsearch-savetargets` | boolean |  |  |  |  |  | Save a simple tabular file summarising the per-target output. |
| `--amp-run-hmmsearch` | boolean |  |  |  |  |  | Run hmmsearch during AMP screening. |

## amp_macrel

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amp-skip-macrel` | boolean |  |  |  |  |  | Skip Macrel during AMP screening. |

## annotation_bakta

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-bakta-activate-plot` | boolean |  |  |  |  |  | Activate generation of circular genome plots. |
| `--annotation-bakta-complete` | boolean |  |  |  |  |  | Specify that all contigs are complete replicons. |
| `--annotation-bakta-compliant` | boolean |  |  |  |  |  | Clean the result annotations to standardise them to Genbank/ENA conventions. |
| `--annotation-bakta-crispr` | boolean |  |  |  |  |  | Activate CRISPR array detection & annotation. |
| `--annotation-bakta-db` | string |  |  |  |  |  | Specify a path to a local copy of a BAKTA database. |
| `--annotation-bakta-db-downloadtype` | string |  |  | `full`, `light` |  | full | Download full or light version of the Bakta database if not supplying own database. |
| `--annotation-bakta-gap` | boolean |  |  |  |  |  | Activate gap detection & annotation. |
| `--annotation-bakta-gram` | string |  |  | `+`, `-`, `?` |  | ? | Specify the type of bacteria to be annotated to detect signaling peptides. |
| `--annotation-bakta-hmms` | string |  |  |  |  |  | Supply a path of an HMM file of trusted hidden markov models in HMMER format for CDS annotation |
| `--annotation-bakta-mincontiglen` | integer |  |  |  | ≥ 1 | 1 | Specify the minimum contig size. |
| `--annotation-bakta-ncrna` | boolean |  |  |  |  |  | Activate ncRNA detection & annotation. |
| `--annotation-bakta-ncrnaregion` | boolean |  |  |  |  |  | Activate ncRNA region detection & annotation. |
| `--annotation-bakta-ori` | boolean |  |  |  |  |  | Activate oriC/oriT detection & annotation. |
| `--annotation-bakta-pseudo` | boolean |  |  |  |  |  | Activate pseudogene detection & annotation. |
| `--annotation-bakta-renamecontigheaders` | boolean |  |  |  |  |  | Changes the original contig headers. |
| `--annotation-bakta-rrna` | boolean |  |  |  |  |  | Activate rRNA detection & annotation. |
| `--annotation-bakta-singlemode` | boolean |  |  |  |  |  | Use the default genome-length optimised mode (rather than the metagenome mode). |
| `--annotation-bakta-skipcds` | boolean |  |  |  |  |  | Skip CDS detection & annotation. |
| `--annotation-bakta-skipsorf` | boolean |  |  |  |  |  | Skip sORF detection & annotation. |
| `--annotation-bakta-tmrna` | boolean |  |  |  |  |  | Activate tmRNA detection & annotation. |
| `--annotation-bakta-translationtable` | integer |  |  |  | ≥ 1; ≤ 25 | 11 | Specify the genetic code translation table. |
| `--annotation-bakta-trna` | boolean |  |  |  |  |  | Activate tRNA detection & annotation. |

## annotation_general_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-tool` | string |  |  | `prodigal`, `pyrodigal`, `prokka`, `bakta` |  | pyrodigal | Specify which annotation tool to use for some downstream tools. |
| `--save-annotations` | boolean |  |  |  |  |  | Specify whether to save gene annotations in the results directory. |

## annotation_prodigal

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-prodigal-closed` | boolean |  |  |  |  |  | Does not allow partial genes on contig edges. |
| `--annotation-prodigal-forcenonsd` | boolean |  |  |  |  |  | Forces Prodigal to scan for motifs. |
| `--annotation-prodigal-singlemode` | boolean |  |  |  |  |  | Specify whether to use Prodigal's single-genome mode for long sequences. |
| `--annotation-prodigal-transtable` | integer |  |  |  |  | 11 | Specifies the translation table used for gene annotation. |

## annotation_prokka

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-prokka-addgenes` | boolean |  |  |  |  |  | Add the gene features for each CDS hit. |
| `--annotation-prokka-cdsrnaolap` | boolean |  |  |  |  |  | Allow transfer RNA (trRNA) to overlap coding sequences (CDS). |
| `--annotation-prokka-compliant` | boolean |  |  |  |  | true | Force contig name to Genbank/ENA/DDJB naming rules. |
| `--annotation-prokka-coverage` | integer |  |  |  | ≥ 0; ≤ 100 | 80 | Set the assigned minimum coverage. |
| `--annotation-prokka-evalue` | number |  |  |  |  | 1e-06 | E-value cut-off. |
| `--annotation-prokka-gcode` | integer |  |  |  | ≥ 0; ≤ 25 | 11 | Specify the translation table used to annotate the sequences. |
| `--annotation-prokka-kingdom` | string |  |  | `Archaea`, `Bacteria`, `Mitochondria`, `Viruses` |  | Bacteria | Specify the kingdom that the input represents. |
| `--annotation-prokka-mincontiglen` | integer |  |  |  |  | 1 | Minimum contig size required for annotation (bp). |
| `--annotation-prokka-rawproduct` | boolean |  |  |  |  |  | Suppress the default clean-up of the gene annotations. |
| `--annotation-prokka-retaincontigheaders` | boolean |  |  |  |  |  | Retains contig names. |
| `--annotation-prokka-rnammer` | boolean |  |  |  |  |  | Use RNAmmer for rRNA prediction. |
| `--annotation-prokka-singlemode` | boolean |  |  |  |  |  | Use the default genome-length optimised mode (rather than the metagenome mode). |

## annotation_pyrodigal

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-pyrodigal-closed` | boolean |  |  |  |  |  | Does not allow partial genes on contig edges. |
| `--annotation-pyrodigal-forcenonsd` | boolean |  |  |  |  |  | Forces Pyrodigal to scan for motifs. |
| `--annotation-pyrodigal-singlemode` | boolean |  |  |  |  |  | Specify whether to use Pyrodigal's single-genome mode for long sequences. |
| `--annotation-pyrodigal-transtable` | integer |  |  |  |  | 11 | Specifies the translation table used for gene annotation. |
| `--annotation-pyrodigal-usespecialstopcharacter` | boolean |  |  |  |  |  | This forces Pyrodigal to append asterisks (`*`) as stop codon indicators. Do not use when running AMP workflow. |

## arg_abricate

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-abricate-db` | string |  |  |  |  |  | Path to user-defined local ABRicate database directory for using custom databases. |
| `--arg-abricate-db-id` | string |  |  |  |  | ncbi | Specify the name of the ABRicate database to use. Names of non-default databases can be supplied if `--arg_abricate_db` provided. |
| `--arg-abricate-mincov` | integer |  |  |  | ≥ 1; ≤ 100 | 80 | Minimum percent coverage of alignment required for a hit to be considered. |
| `--arg-abricate-minid` | integer |  |  |  | ≥ 1; ≤ 100 | 80 | Minimum percent identity of alignment required for a hit to be considered. |
| `--arg-skip-abricate` | boolean |  |  |  |  |  | Skip ABRicate during the ARG screening. |

## arg_amrfinderplus

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-amrfinderplus-coveragemin` | number |  |  |  | ≥ 0; ≤ 1 | 0.5 | Minimum coverage of the reference protein. |
| `--arg-amrfinderplus-db` | string |  |  |  |  |  | Specify the path to a local version of the ARMFinderPlus database. |
| `--arg-amrfinderplus-identmin` | number |  |  |  |  | -1 | Minimum percent identity to reference sequence. |
| `--arg-amrfinderplus-name` | boolean |  |  |  |  |  | Add identified column to AMRFinderPlus output. |
| `--arg-amrfinderplus-plus` | boolean |  |  |  |  |  | Add the plus genes to the report. |
| `--arg-amrfinderplus-translationtable` | integer |  |  |  | ≥ 1; ≤ 33 | 11 | Specify which NCBI genetic code to use for translated BLAST. |
| `--arg-skip-amrfinderplus` | boolean |  |  |  |  |  | Skip AMRFinderPlus during the ARG screening. |

## arg_argnorm

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-skip-argnorm` | boolean |  |  |  |  |  | Skip argNorm during ARG screening. |

## arg_deeparg

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-deeparg-alignmentevalue` | number |  |  |  |  | 1e-10 | Specify E-value cutoff under which hits are discarded. |
| `--arg-deeparg-alignmentidentity` | integer |  |  |  |  | 50 | Specify percent identity cutoff for sequence alignment under which hits are discarded. |
| `--arg-deeparg-alignmentoverlap` | number |  |  |  |  | 0.8 | Specify alignment read overlap. |
| `--arg-deeparg-db` | string |  |  |  |  |  | Specify the path to the DeepARG database. |
| `--arg-deeparg-db-version` | integer |  |  |  |  | 2 | Specify the numeric version number of a user supplied DeepaRG database. |
| `--arg-deeparg-minprob` | number |  |  |  |  | 0.8 | Specify minimum probability cutoff under which hits are discarded. |
| `--arg-deeparg-model` | string |  |  | `LS`, `SS` |  | LS | Specify which model to use (short or long sequences). |
| `--arg-deeparg-numalignmentsperentry` | integer |  |  |  |  | 1000 | Specify minimum number of alignments per entry for DIAMOND step of DeepARG. |
| `--arg-skip-deeparg` | boolean |  |  |  |  |  | Skip DeepARG during the ARG screening. |

## arg_fargene

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-fargene-hmmmodel` | string |  |  |  | matches ^(class_a\|class_b_1_2\|class_b_3\|class_c\|class_d_1\|class_d_2\|qnr\|tet_efflux\|tet_rpg\|tet_enzyme)(,(class_a\|class_b_1_2\|class_b_3\|class_c\|class_d_1\|class_d_2\|qnr\|tet_efflux\|tet_rpg\|tet_enzyme))*$ | class_a,class_b_1_2,class_b_3,class_c,class_d_1,class_d_2,qnr,tet_efflux,tet_rpg,tet_enzyme | Specify comma-separated list of which pre-defined HMM models to screen against |
| `--arg-fargene-minorflength` | integer |  |  |  | ≥ 1; ≤ 100 | 90 | The minimum length of a predicted ORF retrieved from annotating the nucleotide sequences. |
| `--arg-fargene-orffinder` | boolean |  |  |  |  |  | Defines which ORF finding algorithm to use. |
| `--arg-fargene-savetmpfiles` | boolean |  |  |  |  |  | Specify to save intermediate temporary files to results directory. |
| `--arg-fargene-score` | number |  |  |  |  |  | The threshold score for a sequence to be classified as a (almost) complete gene. |
| `--arg-fargene-translationformat` | string |  |  |  |  | pearson | The translation table/format to use for sequence annotation. |
| `--arg-skip-fargene` | boolean |  |  |  |  |  | Skip fARGene during the ARG screening. |

## arg_hamronization

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-hamronization-summarizeformat` | string |  |  | `interactive`, `tsv`, `json` |  | tsv | Specifies summary output format. |

## arg_rgi

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arg-rgi-alignmenttool` | string |  |  | `BLAST`, `DIAMOND` |  | BLAST | Specify the alignment tool to be used. |
| `--arg-rgi-data` | string |  |  | `NA`, `wgs`, `plasmid`, `chromosome` |  | NA | Specify a more specific data-type of input (e.g. plasmid, chromosome). |
| `--arg-rgi-db` | string |  |  |  |  |  | Path to user-defined local CARD database. |
| `--arg-rgi-includeloose` | boolean |  |  |  |  |  | Include all of loose, strict and perfect hits (i.e. more than 95% identity) found by RGI. |
| `--arg-rgi-includenudge` | boolean |  |  |  |  |  | Suppresses the default behaviour of RGI with `--arg_rgi_includeloose`. |
| `--arg-rgi-lowquality` | boolean |  |  |  |  |  | Include screening of low quality contigs for partial genes. |
| `--arg-rgi-removetemporaryfiles` | boolean |  |  |  |  |  | Specify to trigger RGI's internal cleanup of intermediate files. |
| `--arg-rgi-savejson` | boolean |  |  |  |  |  | Save RGI output .json file. |
| `--arg-rgi-savetmpfiles` | boolean |  |  |  |  |  | Specify to save intermediate temporary files in the results directory. |
| `--arg-rgi-split-prodigal-jobs` | boolean |  |  |  |  | true | Run multiple prodigal jobs simultaneously for contigs in a fasta file. |
| `--arg-skip-rgi` | boolean |  |  |  |  |  | Skip RGI during the ARG screening. |

## bgc_antismash

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bgc-antismash-cbgeneral` | boolean |  |  |  |  |  | Turn on clusterblast comparison against database of antiSMASH-predicted clusters. |
| `--bgc-antismash-cbknownclusters` | boolean |  |  |  |  |  | Turn on clusterblast comparison against known gene clusters from the MIBiG database. |
| `--bgc-antismash-cbsubclusters` | boolean |  |  |  |  |  | Turn on clusterblast comparison against known subclusters responsible for synthesising precursors. |
| `--bgc-antismash-ccmibig` | boolean |  |  |  |  |  | Turn on ClusterCompare comparison against known gene clusters from the MIBiG database. |
| `--bgc-antismash-clusterhmmer` | boolean |  |  |  |  |  | Run antiSMASH with --clusterhmmer mode with Pfam profiles |
| `--bgc-antismash-contigminlength` | integer |  |  |  |  | 3000 | Minimum length a contig must have to be screened with antiSMASH. |
| `--bgc-antismash-db` | string |  |  |  |  |  | Path to user-defined local antiSMASH database. |
| `--bgc-antismash-fullhmmer` | boolean |  |  |  |  |  | Run antiSMASH with --fullhmmer mode with Pfam profiles |
| `--bgc-antismash-hmmdetectionstrictness` | string |  |  | `relaxed`, `strict`, `loose` |  | relaxed | Defines which level of strictness to use for HMM-based cluster detection. |
| `--bgc-antismash-pfam2go` | boolean |  |  |  |  |  | Run Pfam to Gene Ontology mapping module. |
| `--bgc-antismash-rre` | boolean |  |  |  |  |  | Run RREFinder precision mode on all RiPP gene clusters. |
| `--bgc-antismash-smcogtrees` | boolean |  |  |  |  |  | Generate phylogenetic trees of secondary metabolite group orthologs. |
| `--bgc-antismash-taxon` | string |  |  | `bacteria`, `fungi` |  | bacteria | Specify which taxonomic classification of input sequence to use. |
| `--bgc-antismash-tfbs` | boolean |  |  |  |  |  | Run TFBS finder on all gene clusters. |
| `--bgc-antismash-tigrfam` | boolean |  |  |  |  |  | Run antiSMASH with --tigrfam annotation activated |
| `--bgc-skip-antismash` | boolean |  |  |  |  |  | Skip antiSMASH during the BGC screening. |

## bgc_bigslice

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bgc-bigslice-complete` | boolean |  |  |  |  |  | Run BiG-SLiCE in complete mode, re-clustering all BGCs into GCFs from scratch. |
| `--bgc-bigslice-db` | string |  |  |  |  |  | Path to the pre-downloaded BiG-SLiCE HMM database directory. |
| `--bgc-bigslice-exporttsv` | boolean |  |  |  |  |  | Export BiG-SLiCE results as TSV files in addition to the SQLite database. |
| `--bgc-bigslice-nranks` | integer |  |  |  |  | 1 | Number of best GCF hits to report for each BGC membership assignment. |
| `--bgc-bigslice-threshold` | number |  |  |  |  | 0.4 | Jaccard index threshold for considering a BGC as a member of a GCF. |
| `--bgc-bigslice-thresholdpct` | number |  |  |  |  | -1 | Percentage-based BGC-to-GCF membership threshold. |
| `--bgc-run-bigslice` | boolean |  |  |  |  |  | Run BiG-SLiCE to cluster detected BGCs into gene cluster families (GCFs). |

## bgc_deepbgc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bgc-deepbgc-classifierscore` | number |  |  |  |  | 0.5 | DeepBGC classification score threshold for assigning classes to BGCs. |
| `--bgc-deepbgc-db` | string |  |  |  |  |  | Path to local DeepBGC database folder. |
| `--bgc-deepbgc-mergemaxnuclgap` | integer |  |  |  |  | 0 | Merge detected BGCs within given number of nucleotides. |
| `--bgc-deepbgc-mergemaxproteingap` | integer |  |  |  |  | 0 | Merge detected BGCs within given number of proteins. |
| `--bgc-deepbgc-minbiodomains` | integer |  |  |  |  | 0 | Minimum number of known biosynthetic (as defined by antiSMASH) protein domains in a BGC. |
| `--bgc-deepbgc-mindomains` | integer |  |  |  |  | 1 | Minimum number of protein domains in a BGC. |
| `--bgc-deepbgc-minnucl` | integer |  |  |  |  | 1 | Minimum BGC nucleotide length. |
| `--bgc-deepbgc-minproteins` | integer |  |  |  |  | 1 | Minimum number of proteins in a BGC. |
| `--bgc-deepbgc-prodigalsinglemode` | boolean |  |  |  |  |  | Run DeepBGC's internal Prodigal step in `single` mode to restrict detecting genes to long contigs |
| `--bgc-deepbgc-score` | number |  |  |  |  | 0.5 | Average protein-wise DeepBGC score threshold for extracting BGC regions from Pfam sequences. |
| `--bgc-skip-deepbgc` | boolean |  |  |  |  |  | Skip DeepBGC during the BGC screening. |

## bgc_gecco

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bgc-gecco-cds` | integer |  |  |  |  | 3 | The minimum number of coding sequences a valid cluster must contain. |
| `--bgc-gecco-convertformat` | string |  |  | `gff`, `bigslice`, `fna`, `faa` |  | gff | Specify output format for GECCO convert. |
| `--bgc-gecco-convertmode` | string |  |  | `clusters`, `gbk` |  | clusters | Specify conversion mode for GECCO convert. |
| `--bgc-gecco-edgedistance` | integer |  |  |  |  | 0 | The minimum number of annotated genes that must separate a cluster from the edge. |
| `--bgc-gecco-mask` | boolean |  |  |  |  |  | Enable unknown region masking to prevent genes from stretching across unknown nucleotides. |
| `--bgc-gecco-pfilter` | number |  |  |  |  | 1e-09 | The p-value cutoff for protein domains to be included. |
| `--bgc-gecco-runconvert` | boolean |  |  |  |  |  | Enable GECCO file conversion to formats for downstream analysis. |
| `--bgc-gecco-threshold` | number |  |  |  |  | 0.8 | The probability threshold for cluster detection. |
| `--bgc-skip-gecco` | boolean |  |  |  |  |  | Skip GECCO during the BGC screening. |

## bgc_general_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bgc-mincontiglength` | integer |  |  |  |  | 3000 | Specify the minimum length of contigs that go into BGC screening. |
| `--bgc-savefilteredcontigs` | boolean |  |  |  |  |  | Specify to save the length-filtered (unannotated) FASTAs used for BGC screening. |

## bgc_hmmsearch

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bgc-hmmsearch-models` | string |  |  |  |  |  | Specify path to the BGC hmm model file(s) to search against. Must have quotes if wildcard used. |
| `--bgc-hmmsearch-savealignments` | boolean |  |  |  |  |  | Saves a multiple alignment of all significant hits to a file. |
| `--bgc-hmmsearch-savedomains` | boolean |  |  |  |  |  | Save a simple tabular file summarising the per-domain output. |
| `--bgc-hmmsearch-savetargets` | boolean |  |  |  |  |  | Save a simple tabular file summarising the per-target output. |
| `--bgc-run-hmmsearch` | boolean |  |  |  |  |  | Run hmmsearch during BGC screening. |

## cazyme_dbcan

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cazyme-dbcan-db` | string |  |  |  |  |  | Path to local dbCAN database folder. |
| `--cazyme-skip-dbcan` | boolean |  |  |  |  |  | Skip dbCAN during the CAZyme screening. |
| `--dbcan-skip-cgc` | boolean |  |  |  |  |  | Skip CGC during the dbCAN screening. |
| `--dbcan-skip-substrate` | boolean |  |  |  |  |  | Skip substrate prediction during the dbCAN screening. |

## database_downloading_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-db` | boolean |  |  |  |  |  | Specify whether to save pipeline-downloaded databases in your results directory. |

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
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing sample names and paths to corresponding FASTA files, and optional annotation files. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
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

## protein_annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--protein-annotation-interproscan-applications` | string |  |  |  | matches ^\w+(,\w+)* | PANTHER,ProSiteProfiles,ProSitePatterns,Pfam | Assigns the database(s) to be used to annotate the coding regions. |
| `--protein-annotation-interproscan-db` | string |  |  |  |  |  | Path to pre-downloaded InterProScan database. |
| `--protein-annotation-interproscan-db-url` | string |  |  |  |  | https://ftp.ebi.ac.uk/pub/software/unix/iprscan/5/5.72-103.0/interproscan-5.72-103.0-64-bit.tar.gz | Change the database version used for annotation. |
| `--protein-annotation-interproscan-enableprecalc` | boolean |  |  |  |  |  | Pre-calculates residue mutual matches. |
| `--protein-annotation-tool` | string |  |  | `InterProScan` |  | InterProScan | Specifies the tool used for further protein annotation. |
| `--run-protein-annotation` | boolean |  |  |  |  |  | Activates the functional annotation of annotated coding regions to provide more information about the codon regions classified. |

## screening_type_activation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--run-amp-screening` | boolean |  |  |  |  |  | Activate antimicrobial peptide genes screening tools. |
| `--run-arg-screening` | boolean |  |  |  |  |  | Activate antimicrobial resistance gene screening tools. |
| `--run-bgc-screening` | boolean |  |  |  |  |  | Activate biosynthetic gene cluster screening tools. |
| `--run-cazyme-screening` | boolean |  |  |  |  |  | Activate CAZyme and CAZyme gene cluster screening tools. |

## taxonomic_classification_general_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--run-taxa-classification` | boolean |  |  |  |  |  | Activates the taxonomic classification of input nucleotide sequences. |
| `--taxa-classification-mmseqs-compressed` | boolean |  |  |  |  |  | If MMseqs2 is chosen as taxonomic classification tool: Specifies if the output of all MMseqs2 subcommands shall be compressed. |
| `--taxa-classification-tool` | string |  |  | `mmseqs2` |  | mmseqs2 | Specifies the tool used for taxonomic classification. |

## taxonomic_classification_mmseqs2_databases

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--taxa-classification-mmseqs-db` | string |  |  |  |  |  | Specify a path to MMseqs2-formatted database. |
| `--taxa-classification-mmseqs-db-id` | string |  |  |  |  | Kalamari | Specify the label of the database to be used. |
| `--taxa-classification-mmseqs-db-savetmp` | boolean |  |  |  |  |  | Specify whether the temporary files should be saved. |

## taxonomic_classification_mmseqs2_taxonomy

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--taxa-classification-mmseqs-taxonomy-lcamode` | integer |  |  |  |  | 3 | Specify the mode to assign the taxonomy. |
| `--taxa-classification-mmseqs-taxonomy-lcaranks` | string |  |  |  |  | kingdom,phylum,class,order,family,genus,species | Specify the taxonomic levels to display in the result table. |
| `--taxa-classification-mmseqs-taxonomy-orffilters` | number |  |  |  |  | 2 | Specify the ORF search sensitivity in the prefilter step. |
| `--taxa-classification-mmseqs-taxonomy-savetmp` | boolean |  |  |  |  |  | Specify whether to save the temporary files. |
| `--taxa-classification-mmseqs-taxonomy-searchtype` | integer |  |  |  |  | 2 | Specify the alignment type between database and query. |
| `--taxa-classification-mmseqs-taxonomy-sensitivity` | number |  |  |  |  | 5 | Specify the speed and sensitivity for taxonomy assignment. |
| `--taxa-classification-mmseqs-taxonomy-taxlineage` | integer |  |  |  |  | 1 | Specify whether to include or remove the taxonomic lineage. |
| `--taxa-classification-mmseqs-taxonomy-votemode` | integer |  |  |  |  | 1 | Specify the weights of the taxonomic assignment. |

<!-- Generated from nf-core/funcscan@aee3dc965eb0c77267435544dda30da858763913. Do not edit by hand. -->
