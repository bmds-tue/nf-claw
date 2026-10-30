# Prepare DRAMP for Funcscan 4.0.0

The pinned Funcscan release uses AMPcombi 3.0.0. Its DRAMP downloader passes pandas
NaN values from missing sequence cells to a string regex and crashes. APD is unaffected.
An explicit prepared reference avoids this downloader and records the database actually used.
The pinned pipeline and container code remain unchanged.

---

## Navigation

[Overview](#overview) • [Download Dataset](#downloading-the-general-amp-dataset) • [Prepare Reference](#preparing-the-reference-directory) • [Build Index](#building-the-mmseqs2-index) • [Run with Funcscan](#execution-with-funcscan)

---

## Overview

Download the complete official general-AMP TSV and retain it beside your records. The endpoint
is mutable: its URL is not a version or a checksum.

## Downloading the general AMP dataset

For example, with a recent curl:

```bash
curl --fail --location --http1.1 --remove-on-error --connect-timeout 15 --max-time 300 \
  --output general_amps.txt \
  'https://dramp.cpu-bioinfor.org/downloads/download.php?filename=download_data/DRAMP3.0_new/general_amps.txt'
```

Check the transfer succeeded and the response length/checksum against your intended snapshot.
Do not prepare a partial download. The server validation snapshot on 2026-10-27 was 13,221,293
bytes, SHA-256 `4e044b3a4d9fcfc24cff81cbcf9fdb48184b41d8773837c697a2f205c1ab9dd5`.
That snapshot contains no missing sequences, so its downloader succeeds today; an explicit
blank-cell control reproduces the latent failure in the actual released container.

## Preparing the reference directory

Use a fresh destination under an existing parent:

```bash
nfclaw prepare-dramp /data/general_amps.txt --outdir /refs/amp_DRAMP_database
```

This standalone command needs no pipeline checkout or optional Python packages. It writes
`general_amps.fasta`, `general_amps.txt` and `preparation.json`, and prints the JSON record.
The directory is private (0700), its files are private (0600), and existing destinations are
refused. Its name must contain the case-sensitive substring `DRAMP`: AMPcombi selects its
annotation parser from that name.

The explicit `identified-uppercase-canonical-20-v1` policy retains a row only when it has a
DRAMP identifier and a nonempty sequence made entirely of uppercase `ACDEFGHIKLMNPQRSTVWY`.
It preserves the exact retained sequence, identifier, every annotation value, column and row
order. It never trims, uppercases, renames or imputes data. Missing identifiers/sequences and
other sequences are excluded with reason counts and bounded example IDs. This is compatibility
with the consumer's canonical-sequence criterion; other peptides can be biologically valid.
Unsafe or duplicate nonempty IDs, malformed/duplicate/missing columns and no retained sequences
cause refusal. The held raw input is hashed before and after parsing; changed input is refused
before publication. These snapshots do not prove continuous immutability.

The validation snapshot contains 12,784 rows: **10,564 retained**, 2,219 noncanonical sequences
and 1 missing identifier excluded. All retained annotation values and FASTA identifiers/sequences
were independently checked against the complete raw file. The raw file is not overwritten.
Review the counts for your own snapshot rather than assuming these numbers stay current.

## Building the MMseqs2 index

Build the reference index **before** analysis. The preparation record describes the earlier
FASTA/annotation stage and explicitly says its index is not built. Use the tested image digest:

```bash
docker run --rm --network none --user "$(id -u):$(id -g)" \
  --mount type=bind,src=/refs/amp_DRAMP_database,dst=/ref \
  quay.io/biocontainers/ampcombi@sha256:53a73be7a84bb1e921c2bbbd81d6d48453b0b3ab5d0ae1e6709c0d6dd662c237 \
  sh -eu -c 'mkdir /ref/.mmseqs2-building
    mmseqs createdb /ref/general_amps.fasta /ref/.mmseqs2-building/ref_DB -v 0
    mv /ref/.mmseqs2-building /ref/mmseqs2'
```

Run this once on a freshly prepared reference, with no concurrent writer. If it fails, do not
supply the incomplete directory to analysis: AMPcombi treats the existence of `mmseqs2` as proof
that indexing is done. Require the command to succeed and the eight nonempty index files:
`ref_DB`, `ref_DB.dbtype`, `ref_DB.index`, `ref_DB.lookup`, `ref_DB.source`, `ref_DB_h`,
`ref_DB_h.dbtype`, `ref_DB_h.index` under `mmseqs2/`.

## Execution with Funcscan

Supply your normal input and screening options, selecting DRAMP explicitly:

```bash
nfclaw run funcscan --input /data/samplesheet.csv --outdir /results/funcscan \
  --nxf-ver 25.10.4 --amp-ampcombi-db-id DRAMP \
  --amp-ampcombi-db /refs/amp_DRAMP_database --run-amp-screening true
```

The standard bundled demo selects APD. To test DRAMP with demo input, pass these same database
options with `--demo`. AMP predictors, ARG/BGC/CAZyme/taxonomy branches and their databases remain
separate choices. A completed selected AMP branch does not validate every Funcscan branch.

The pinned container built the complete index and recovered an 84-residue known-answer query
as the exact DRAMP00222 sequence with its annotation. That consumer check left the full prebuilt
reference unchanged. It establishes reference ingestion/search/annotation behavior, not biological
AMP prediction accuracy. Normal run provenance checksums the supplied directory including indexes;
keep those files available and unchanged for guarded replay.
