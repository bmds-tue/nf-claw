---
name: proteinfold
version: 2.0.0
commit: 5338c24b2af62cc4c02dcd34bcc49912eebffb3a
---

# proteinfold — full parameter reference

nf-core/proteinfold pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alphafold2_dbs_and_parameters_link_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alphafold2-bfd-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/casp14_versions/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz` | Link to BFD dababase |
| `--alphafold2-mgnify-link` | string |  |  |  |  | `https://ftp.ebi.ac.uk/pub/databases/metagenomics/peptide_database/2024_04/mgy_clusters.fa.gz` | Link to the MGnify database |
| `--alphafold2-params-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar` | Link to the AlphaFold2 parameters |
| `--alphafold2-pdb70-link` | string |  |  |  |  | `https://wwwuser.gwdguser.de/~compbiol/data/hhsuite/databases/hhsuite_dbs/pdb70_from_mmcif_220313.tar.gz` | Link to the PDB70 database |
| `--alphafold2-pdb-mmcif-link` | string |  |  |  |  | `rsync.rcsb.org::ftp_data/structures/divided/mmCIF/` | Link to the PDB mmCIF database |
| `--alphafold2-pdb-obsolete-link` | string |  |  |  |  | `https://files.wwpdb.org/pub/pdb/data/status/obsolete.dat` | Link to the PDB obsolete database |
| `--alphafold2-pdb-seqres-link` | string |  |  |  |  | `https://files.wwpdb.org/pub/pdb/derived_data/pdb_seqres.txt` | Link to the PDB SEQRES database |
| `--alphafold2-small-bfd-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/reduced_dbs/bfd-first_non_consensus_sequences.fasta.gz` | Link to a reduced version of the BFD dababase |
| `--alphafold2-uniprot-sprot-link` | string |  |  |  |  | `https://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.fasta.gz` | Link to the SwissProt UniProt database |
| `--alphafold2-uniprot-trembl-link` | string |  |  |  |  | `https://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.fasta.gz` | Link to the TrEMBL UniProt database |
| `--alphafold2-uniref30-link` | string |  |  |  |  | `https://wwwuser.gwdguser.de/~compbiol/uniclust/2023_02/UniRef30_2023_02_hhsuite.tar.gz` | Link to the Uniclust30 database |
| `--alphafold2-uniref90-link` | string |  |  |  |  | `https://ftp.ebi.ac.uk/pub/databases/uniprot/uniref/uniref90/uniref90.fasta.gz` | Link to the UniRef90 database |

## alphafold2_dbs_and_parameters_paths_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alphafold2-bfd-path` | string |  |  |  |  | `null/bfd/*` | Path to BFD dababase |
| `--alphafold2-db` | string (file or directory path) |  |  |  |  |  | Specifies the DB and PARAMS path used by 'AlphaFold2' mode |
| `--alphafold2-mgnify-path` | string |  |  |  |  | `null/mgnify/*` | Path to the MGnify database |
| `--alphafold2-params-path` | string |  |  |  |  | `null/params/alphafold_params_2022-12-06/*` | Path to the AlphaFold2 parameters |
| `--alphafold2-pdb70-path` | string |  |  |  |  | `null/pdb70/**` | Path to the PDB70 database |
| `--alphafold2-pdb-mmcif-path` | string |  |  |  |  | `null/pdb_mmcif/mmcif_files` | Path to the PDB mmCIF database |
| `--alphafold2-pdb-obsolete-path` | string |  |  |  |  | `null/pdb_mmcif/obsolete.dat` | Path to the PDB obsolete file |
| `--alphafold2-pdb-seqres-path` | string |  |  |  |  | `null/pdb_seqres/*` | Path to the PDB SEQRES database |
| `--alphafold2-small-bfd-path` | string |  |  |  |  | `null/small_bfd/*` | Path to a reduced version of the BFD database |
| `--alphafold2-uniprot-path` | string |  |  |  |  | `null/uniprot/*` | Path to UniProt database containing the SwissProt and the TrEMBL databases |
| `--alphafold2-uniref30-path` | string |  |  |  |  | `null/uniref30/*` | Path to the Uniref30 database |
| `--alphafold2-uniref90-path` | string |  |  |  |  | `null/uniref90/*` | Path to the UniRef90 database |

## alphafold2_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alphafold2-full-dbs` | boolean |  |  |  |  |  | If true uses the full version of the BFD database otherwise, otherwise it uses its reduced version, small bfd |
| `--alphafold2-max-template-date` | string |  |  |  | matches `^\d{4}-\d{2}-\d{2}$` | `2038-01-19` | Maximum date of the PDB templates used by 'AlphaFold2' mode |
| `--alphafold2-mode` | string |  |  | `standard`, `split_msa_prediction` |  | `split_msa_prediction` | Specifies the mode in which AlphaFold2 will be run |
| `--alphafold2-model-preset` | string |  |  | `monomer`, `monomer_casp14`, `monomer_ptm`, `multimer` |  | `monomer_ptm` | Model preset for 'AlphaFold2' mode |
| `--alphafold2-params-prefix` | string |  |  | `alphafold_params_2022-12-06`, `alphafold_params_2022-03-02`, `alphafold_params_2022-01-19`, `alphafold_params_2021-07-14` |  | `alphafold_params_2022-12-06` | Alphafold2 parameters version |
| `--alphafold2-random-seed` | integer |  |  |  |  |  | Random seed to control stochastic alphafold inference. |

## alphafold3_dbs_and_parameters_link_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alphafold3-db` | string (file or directory path) |  |  |  |  |  | Specifies the DB and PARAMS path used by 'AlphaFold3' mode |
| `--alphafold3-mgnify-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/mgy_clusters_2022_05.fa.zst` | Link to the MGnify database |
| `--alphafold3-nt-rna-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/nt_rna_2023_02_23_clust_seq_id_90_cov_80_rep_seq.fasta.zst` | Link to the nt_rna database |
| `--alphafold3-pdb-mmcif-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/pdb_2022_09_28_mmcif_files.tar.zst` | Link to the PDB mmCIF database |
| `--alphafold3-pdb-seqres-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/pdb_seqres_2022_09_28.fasta.zst` | Link to the PDB SEQRES database |
| `--alphafold3-rfam-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/rfam_14_9_clust_seq_id_90_cov_80_rep_seq.fasta.zst` | Link to the Rfam database |
| `--alphafold3-rnacentral-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/rnacentral_active_seq_id_90_cov_80_linclust.fasta.zst` | Link to the RNAcentral database |
| `--alphafold3-small-bfd-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/bfd-first_non_consensus_sequences.fasta.zst` | Link to a reduced version of the BFD dababase |
| `--alphafold3-uniprot-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/uniprot_all_2021_04.fa.zst` | Link to the UniProt database |
| `--alphafold3-uniref90-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/v3.0/uniref90_2022_05.fa.zst` | Link to the UniRef90 database |

## alphafold3_dbs_and_parameters_path_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alphafold3-mgnify-path` | string |  |  |  |  | `null/mgnify/*` | Path to the MGnify database |
| `--alphafold3-nt-rna-path` | string |  |  |  |  | `null/nt_rna/*` | Path to the nt_rna database |
| `--alphafold3-params-path` | string |  |  |  |  |  | Path to the Alphafold3 parameters |
| `--alphafold3-pdb-mmcif-path` | string |  |  |  |  | `null/pdb_mmcif/mmcif_files` | Path to the PDB mmCIF database |
| `--alphafold3-pdb-seqres-path` | string |  |  |  |  | `null/pdb_seqres/*` | Path to the PDB SEQRES database |
| `--alphafold3-rfam-path` | string |  |  |  |  | `null/rfam/*` | Path to the Rfam database |
| `--alphafold3-rnacentral-path` | string |  |  |  |  | `null/rnacentral/*` | Path to the RNAcentral database |
| `--alphafold3-small-bfd-path` | string |  |  |  |  | `null/small_bfd/*` | Path to the reduced version of the BFD database |
| `--alphafold3-uniprot-path` | string |  |  |  |  | `null/uniprot/*` | Path to UniProt database containing the SwissProt and the TrEMBL databases |
| `--alphafold3-uniref90-path` | string |  |  |  |  | `null/uniref90/*` | Path to the UniRef90 database |

## boltz_dbs_and_model_links_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--boltz2-aff-link` | string |  |  |  |  | `https://huggingface.co/boltz-community/boltz-2/resolve/main/boltz2_aff.ckpt` | Link to download boltz affinity file |
| `--boltz2-conf-link` | string |  |  |  |  | `https://huggingface.co/boltz-community/boltz-2/resolve/main/boltz2_conf.ckpt` | Link to download boltz-2 conf file |
| `--boltz2-mols-link` | string |  |  |  |  | `https://huggingface.co/boltz-community/boltz-2/resolve/main/mols.tar` | Link to download boltz-2 mols |
| `--boltz-ccd-link` | string |  |  |  |  | `https://huggingface.co/boltz-community/boltz-1/resolve/main/ccd.pkl` | Link to download CCD file |
| `--boltz-model-link` | string |  |  |  |  | `https://huggingface.co/boltz-community/boltz-1/resolve/main/boltz1_conf.ckpt` | Link to download model file |

## boltz_dbs_and_parameters_paths_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--boltz2-aff-path` | string |  |  |  |  | `null/params/boltz2_aff.ckpt` | Path to boltz affinity file |
| `--boltz2-conf-path` | string |  |  |  |  | `null/params/boltz2_conf.ckpt` | Path to boltz-2 conf file |
| `--boltz2-mols-path` | string |  |  |  |  | `null/params/mols/` | Path to boltz-2 mols |
| `--boltz-ccd-path` | string |  |  |  |  | `null/params/ccd.pkl` | Path to CCD file |
| `--boltz-db` | string |  |  |  |  |  | Path to boltz databases |
| `--boltz-model-path` | string |  |  |  |  | `null/params/boltz1_conf.ckpt` | Path to boltz Model file |

## boltz_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--boltz-model` | string |  |  |  |  |  | Sets the model to use for prediction. Default is boltz2 |
| `--boltz-use-kernels` | boolean |  |  |  |  | `true` | Use optimized Triton-based CUDA kernels for Boltz inference |
| `--boltz-use-potentials` | boolean |  |  |  |  |  | run Boltz-2 using inference time potentials |

## colabfold_dbs_and_parameters_link_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--colabfold-alphafold2-params-link` | string |  |  |  |  |  | Link to the Alphafold2 parameters for Colabfold |
| `--colabfold-db-link` | string |  |  |  |  | `https://opendata.mmseqs.org/colabfold/colabfold_envdb_202108.db.tar.gz` | Link to the ColabFold database |
| `--colabfold-uniref30-link` | string |  |  |  |  | `https://opendata.mmseqs.org/colabfold/uniref30_2302.db.tar.gz` | Link to the UniRef30 database |

## colabfold_dbs_and_parameters_paths_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--colabfold-alphafold2-params-path` | string |  |  |  |  |  | Link to the Alphafold2 parameters for Colabfold |
| `--colabfold-alphafold2-params-tags` | object |  |  |  |  |  | Dictionary with Alphafold2 parameters tags |
| `--colabfold-db` | string (file or directory path) |  |  |  |  |  | Specifies the PARAMS and DB path used by 'colabfold' mode |
| `--colabfold-envdb-path` | string |  |  |  |  | `null/colabfold_envdb/*` | Link to the ColabFold database |
| `--colabfold-uniref30-path` | string |  |  |  |  | `null/colabfold_uniref30/*` | Link to the UniRef30 database |

## colabfold_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--colabfold-create-index` | boolean |  |  |  |  |  | Create databases indexes when running colabfold_local mode |
| `--colabfold-db-load-mode` | integer |  |  | `0`, `1`, `2`, `3` |  |  | Specify the way that MMSeqs2 will load the required databases in memory |
| `--colabfold-model-preset` | string |  |  | `alphafold2_ptm`, `alphafold2_multimer_v1`, `alphafold2_multimer_v2`, `alphafold2_multimer_v3` |  | `alphafold2_ptm` | Model preset for 'colabfold' mode |
| `--colabfold-num-recycles` | integer |  |  |  | ≥ 1; ≤ 20 | `3` | Number of recycles for ColabFold |
| `--colabfold-use-amber` | boolean |  |  |  |  | `true` | Use Amber minimization to refine the predicted structures |
| `--colabfold-use-gpu-relax` | boolean |  |  |  |  | `false` | Use GPU for Amber relaxation in ColabFold |
| `--colabfold-use-templates` | boolean |  |  |  |  | `false` | Use PDB templates |

## esmfold_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--esmfold-model-preset` | string |  |  | `monomer`, `multimer` |  | `monomer` | Specifies whether is a 'monomer' or 'multimer' prediction |
| `--esmfold-num-recycles` | integer |  |  |  | ≥ 1; ≤ 20 | `4` | Specifies the number of recycles used by ESMFold |

## esmfold_parameters_link_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--esm2-t36-3B-UR50D` | string |  |  |  |  | `https://dl.fbaipublicfiles.com/fair-esm/models/esm2_t36_3B_UR50D.pt` | Link to the ESMFold t36-3B-UR50D model |
| `--esm2-t36-3B-UR50D-contact-regression` | string |  |  |  |  | `https://dl.fbaipublicfiles.com/fair-esm/regression/esm2_t36_3B_UR50D-contact-regression.pt` | Link to the ESMFold t36-3B-UR50D-contact-regression model |
| `--esmfold-3B-v1` | string |  |  |  |  | `https://dl.fbaipublicfiles.com/fair-esm/models/esmfold_3B_v1.pt` | Link to the ESMFold 3B-v1 model |

## esmfold_parameters_paths_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--esmfold-db` | string (file or directory path) |  |  |  |  |  | Specifies the PARAMS path used by 'esmfold' mode |
| `--esmfold-params-path` | string |  |  |  |  | `null/params/*` | Link to the ESMFold parameters |

## foldseek_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--foldseek-db` | string |  |  |  |  |  | The ID of Foldseek databases |
| `--foldseek-db-path` | string (file or directory path) |  |  |  |  |  | Specifies the path to foldseek databases used by 'foldseek'. |
| `--foldseek-easysearch-arg` | string |  |  |  |  |  | Specifies the arguments to be passed to foldseek easysearch command |
| `--skip-foldseek` | boolean |  |  |  |  | `true` | Skip foldseek structural similarity search. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
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

## helixfold3_dbs_and_parameters_link_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--helixfold3-bfd-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/casp14_versions/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz` | Link to BFD database for HelixFold3 |
| `--helixfold3-ccd-preprocessed-link` | string |  |  |  |  | `https://paddlehelix.bd.bcebos.com/HelixFold3/CCD/ccd_preprocessed_etkdg.pkl.gz` | Link to CCD preprocessed file for HelixFold3 |
| `--helixfold3-init-models-link` | string |  |  |  |  | `https://paddlehelix.bd.bcebos.com/HelixFold3/params/HelixFold3-params-240814.zip` | Link to HelixFold3 init models |
| `--helixfold3-maxit-src-link` | string |  |  |  |  | `https://proteinfold-dataset.s3.amazonaws.com/test-data/db/helixfold3/maxit-v11.200-prod-src.tar.gz` | Link to Maxit Suite for HelixFold3 |
| `--helixfold3-mgnify-link` | string |  |  |  |  | `https://ftp.ebi.ac.uk/pub/databases/metagenomics/peptide_database/2024_04/mgy_clusters.fa.gz` | Link to MGnify database for HelixFold3 |
| `--helixfold3-obsolete-link` | string |  |  |  |  | `https://files.rcsb.org/pub/pdb/data/status/obsolete.dat` | Link to obsolete PDB file for HelixFold3 |
| `--helixfold3-pdb-mmcif-link` | string |  |  |  |  | `rsync.rcsb.org::ftp_data/structures/divided/mmCIF/` | Link to PDB mmCIF database for HelixFold3 |
| `--helixfold3-pdb-seqres-link` | string |  |  |  |  | `https://files.wwpdb.org/pub/pdb/derived_data/pdb_seqres.txt` | Link to PDB SEQRES database for HelixFold3 |
| `--helixfold3-rfam-link` | string |  |  |  |  | `https://paddlehelix.bd.bcebos.com/HelixFold3/MSA/Rfam-14.9_rep_seq.fasta` | Link to Rfam database for HelixFold3 |
| `--helixfold3-small-bfd-link` | string |  |  |  |  | `https://storage.googleapis.com/alphafold-databases/reduced_dbs/bfd-first_non_consensus_sequences.fasta.gz` | Link to reduced BFD database for HelixFold3 |
| `--helixfold3-uniclust30-link` | string |  |  |  |  | `https://wwwuser.gwdguser.de/~compbiol/uniclust/2023_02/UniRef30_2023_02_hhsuite.tar.gz` | Link to UniRef30 database for HelixFold3 |
| `--helixfold3-uniprot-sprot-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.fasta.gz` | Link to UniProt SwissProt database for HelixFold3 |
| `--helixfold3-uniprot-trembl-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.fasta.gz` | Link to UniProt TrEMBL database for HelixFold3 |
| `--helixfold3-uniref90-link` | string |  |  |  |  | `ftp://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref90/uniref90.fasta.gz` | Link to UniRef90 database for HelixFold3 |

## helixfold3_dbs_and_parameters_paths_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--helixfold3-bfd-path` | string |  |  |  |  | `null/bfd/*` | Path to BFD database for HelixFold3 |
| `--helixfold3-ccd-preprocessed-path` | string |  |  |  |  | `null/params/ccd_preprocessed_etkdg.pkl.gz` | Path to CCD preprocessed file for HelixFold3 |
| `--helixfold3-db` | string |  |  |  |  |  | Path to HelixFold3 database |
| `--helixfold3-init-models-path` | string |  |  |  |  | `null/params/HelixFold3-240814.pdparams` | Path to HelixFold3 init models |
| `--helixfold3-maxit-src-path` | string |  |  |  |  | `null/maxit-v11.200-prod-src` | Path to Maxit Suite for HelixFold3 |
| `--helixfold3-mgnify-path` | string |  |  |  |  | `null/mgnify/*` | Path to MGnify database for HelixFold3 |
| `--helixfold3-obsolete-path` | string |  |  |  |  | `null/pdb_mmcif/obsolete.dat` | Path to obsolete PDB file for HelixFold3 |
| `--helixfold3-pdb-mmcif-path` | string |  |  |  |  | `null/pdb_mmcif/mmcif_files` | Path to PDB mmCIF database for HelixFold3 |
| `--helixfold3-pdb-seqres-path` | string |  |  |  |  | `null/pdb_seqres/*` | Path to PDB SEQRES database for HelixFold3 |
| `--helixfold3-rfam-path` | string |  |  |  |  | `null/rfam/Rfam-14.9_rep_seq.fasta` | Path to Rfam database for HelixFold3 |
| `--helixfold3-small-bfd-path` | string |  |  |  |  | `null/small_bfd/*` | Path to reduced BFD database for HelixFold3 |
| `--helixfold3-uniclust30-path` | string |  |  |  |  | `null/uniref30/*` | Path to UniRef30 database for HelixFold3 |
| `--helixfold3-uniprot-path` | string |  |  |  |  | `null/uniprot/*` | Path to UniProt database for HelixFold3 |
| `--helixfold3-uniref90-path` | string |  |  |  |  | `null/uniref90/*` | Path to UniRef90 database for HelixFold3 |

## helixfold3_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--helixfold3-infer-times` | integer |  |  |  | ≥ 1 | `4` | Number of independent predictions made with the HelixFold3 model |
| `--helixfold3-max-template-date` | string |  |  |  |  | `2038-01-19` | No PDB template released after this date will be used to guide predictions. |
| `--helixfold3-precision` | string |  |  | `bf16`, `fp32` |  | `bf16` | The numerical precision used by the HelixFold3 model. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--db` | string (directory path) |  |  |  |  |  | The directory where reference data is stored. Individual methods can be overwritten with method-specific paths. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--full-dbs` | boolean |  |  |  |  |  | Global toggle for full database usage. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--mode` | string |  |  |  | matches `^(alphafold2\|alphafold3\|colabfold\|esmfold\|rosettafold_all_atom\|helixfold3\|boltz\|rosettafold2na\|)(,(alphafold2\|alphafold3\|colabfold\|esmfold\|rosettafold_all_atom\|helixfold3\|boltz\|rosettafold2na)?,?)*(?<!,)$` | `alphafold2` | Specifies the mode in which the pipeline will be run. mode can be any combination of ['alphafold2', 'alphafold3', 'colabfold', 'esmfold', 'rosettafold_all_atom', 'boltz', 'helixfold3', 'rosettafold2na'] separated by a comma (',') with no spaces. |
| `--msa-server-url` | string |  |  |  |  |  | Specify your custom MMSeqs2 API server url |
| `--multiqc-title` | string |  |  |  | length ≤ 100 |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-intermediates` | boolean |  |  |  |  |  | Keep raw intermediate files |
| `--split-fasta` | boolean |  |  |  |  |  | Split input multi-fasta file in separated fasta files each of them containing one sequence to be folded |
| `--uniref30-prefix` | string |  |  | `UniRef30_2023_02`, `UniRef30_2022_02`, `UniRef30_2021_03` |  | `UniRef30_2023_02` | UniRef major release |
| `--use-gpu` | boolean |  |  |  |  |  | Run on CPUs (default) or GPUs |
| `--use-msa-server` | boolean |  |  |  |  |  | Use the cloud MSA server |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-visualisation` | boolean |  |  |  |  |  | Skip visualisation reports. |

## rosettafold2na_dbs_and_parameters_link_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rfam-cm-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/Rfam.cm.gz` |  |
| `--rfam-full-region-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/Rfam/CURRENT/Rfam.full_region.gz` |  |
| `--rnacentral-id-mapping-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/id_mapping.tsv.gz` |  |
| `--rnacentral-rfam-annotations-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/rfam/rfam_annotations.tsv.gz` |  |
| `--rnacentral-sequences-link` | string |  |  |  |  | `ftp://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/sequences/rnacentral_species_specific_ids.fasta.gz` |  |
| `--rosettafold2na-bfd-link` | string |  |  |  |  | `https://bfd.mmseqs.com/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz` |  |
| `--rosettafold2na-pdb100-link` | string |  |  |  |  | `https://files.ipd.uw.edu/pub/RoseTTAFold/pdb100_2021Mar03.tar.gz` |  |
| `--rosettafold2na-uniref30-link` | string |  |  |  |  | `http://wwwuser.gwdg.de/~compbiol/uniclust/2020_06/UniRef30_2020_06_hhsuite.tar.gz` |  |
| `--rosettafold2na-weights-link` | string |  |  |  |  | `https://files.ipd.uw.edu/dimaio/RF2NA_apr23.tgz` |  |

## rosettafold2na_dbs_and_parameters_path_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rosettafold2na-bfd-path` | string |  |  |  |  | `null/bfd/*` |  |
| `--rosettafold2na-pdb100-path` | string |  |  |  |  | `null/pdb100/*` |  |
| `--rosettafold2na-rna-path` | string |  |  |  |  | `null/RNA/*` | Path to the RNA folder containing all necessary RNA databases for RF2NA |
| `--rosettafold2na-uniref30-path` | string |  |  |  |  | `null/UniRef30_2020_06/*` |  |
| `--rosettafold2na-weights-path` | string |  |  |  |  | `null/params/network/weights/RF2NA_apr23.pt` |  |

## rosettafold2na_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rosettafold2na-db` | string (file or directory path) |  |  |  |  |  | Specifies the DB and PARAMS path used by 'RosettaFold2NA' mode |

## rosettafold_all_atom_dbs_and_parameters_links_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rosettafold-all-atom-bfd-link` | string |  |  |  |  | `https://bfd.mmseqs.com/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz` | Link to the BFD database for RoseTTAFold All Atom |
| `--rosettafold-all-atom-paper-weights-link` | string |  |  |  |  | `http://files.ipd.uw.edu/pub/RF-All-Atom/weights/RFAA_paper_weights.pt` | Link to the RoseTTAFold All Atom paper weights |
| `--rosettafold-all-atom-pdb100-link` | string |  |  |  |  | `https://files.ipd.uw.edu/pub/RoseTTAFold/pdb100_2021Mar03.tar.gz` | Link to the PDB100 database for RoseTTAFold All Atom |
| `--rosettafold-all-atom-uniref30-link` | string |  |  |  |  | `https://wwwuser.gwdguser.de/~compbiol/uniclust/2023_02/UniRef30_2023_02_hhsuite.tar.gz` | Link to the UniRef30 database for RoseTTAFold All Atom |

## rosettafold_all_atom_dbs_and_parameters_paths_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rosettafold-all-atom-bfd-path` | string |  |  |  |  | `null/bfd/*` | Path to BFD database for RoseTTAFold All Atom |
| `--rosettafold-all-atom-db` | string |  |  |  |  |  | Path to RoseTTAFold All Atom database |
| `--rosettafold-all-atom-paper-weights-path` | string |  |  |  |  | `null/params/RFAA_paper_weights.pt` | Path to RoseTTAFold All Atom paper weights |
| `--rosettafold-all-atom-pdb100-path` | string |  |  |  |  | `null/pdb100/*` | Path to PDB100 database for RoseTTAFold All Atom |
| `--rosettafold-all-atom-uniref30-path` | string |  |  |  |  | `null/uniref30/*` | Path to UniRef30 database for RoseTTAFold All Atom |

<!-- Generated from nf-core/proteinfold@5338c24b2af62cc4c02dcd34bcc49912eebffb3a. Do not edit by hand. -->
