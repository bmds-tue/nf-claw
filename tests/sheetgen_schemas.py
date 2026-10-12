"""Samplesheet schemas modelled on pinned releases, for the samplesheet-generation tests.

Each is trimmed to the columns and rules that exercise a generation decision, with the patterns,
formats, metadata and composition keywords exactly as the release declares them. `make_pipeline`
lays one out the way a pinned tree does (`nextflow_schema.json` + `assets/schema_input.json`).
"""
import json
from pathlib import Path

FASTQ_GZ = "^([\\S\\s]*\\/)?[^\\s\\/]+\\.f(ast)?q\\.gz$"
FASTQ_ANY = "^([\\S\\s]*\\/)?[^\\s\\/]+\\.f(ast)?q(\\.gz)?$"
FASTQ_LEGACY = "^\\S+\\.f(ast)?q\\.gz$"


def _fastq(pattern=FASTQ_GZ, **extra):
    return {"type": "string", "format": "file-path", "exists": True, "pattern": pattern, **extra}


RNASEQ = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "mimetype": "text/csv",
              "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": ["string", "integer"], "pattern": "^\\S+$", "meta": ["id"]},
        "fastq_1": _fastq(FASTQ_ANY),
        "fastq_2": _fastq(FASTQ_ANY),
        "strandedness": {"type": "string", "enum": ["forward", "reverse", "unstranded", "auto"],
                         "meta": ["strandedness"]},
        "seq_platform": {"type": "string", "pattern": "^\\S+$", "meta": ["seq_platform"]},
        "genome_bam": {"type": "string", "format": "file-path", "exists": True,
                       "pattern": "^([\\S\\s]*\\/)?[^\\s\\/]+\\.(bam|BAM)$"},
        "percent_mapped": {"type": "number", "meta": "percent_mapped"},
    }, "required": ["sample", "fastq_1", "strandedness"]}},
}

# atacseq 2.1.2: no path format on its FastQ columns, fastq_2's pattern only inside anyOf, and an
# integer replicate whose pattern must never be mistaken for a file type. No `schema` key on --input.
ATACSEQ = {
    "input": {"type": "string", "format": "file-path", "exists": True, "mimetype": "text/csv",
              "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": "string", "pattern": "^\\S+$"},
        "fastq_1": {"type": "string", "pattern": FASTQ_LEGACY},
        "fastq_2": {"anyOf": [{"type": "string", "pattern": FASTQ_LEGACY},
                              {"type": "string", "maxLength": 0}]},
        "replicate": {"type": "integer", "pattern": "^[1-9][0-9]*$"},
        "control": {"type": "string", "pattern": "^\\S+$"},
    }, "required": ["sample", "fastq_1", "replicate"]}},
}

SAREK = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json",
              "pattern": "^\\S+\\.(csv|tsv|yaml|yml|json)$"},
    "sheet": {"items": {"type": "object", "properties": {
        "patient": {"type": "string", "pattern": "^\\S+$", "meta": ["patient"]},
        "sample": {"type": "string", "pattern": "^\\S+$", "meta": ["sample"]},
        "sex": {"type": "string", "enum": ["XX", "XY", "NA"], "default": "NA", "meta": ["sex"]},
        "status": {"type": "integer", "enum": [0, 1], "default": 0, "meta": ["status"]},
        "lane": {"pattern": "^\\S+$", "meta": ["lane"],
                 "anyOf": [{"type": "integer"}, {"type": "string"}]},
        "fastq_1": _fastq(),
        "fastq_2": _fastq(),
        "cram": {"type": "string", "format": "file-path", "exists": True,
                 "pattern": "^\\S+\\.cram$"},
        "crai": {"type": "string", "format": "file-path", "exists": True,
                 "pattern": "^\\S+\\.crai$"},
        "bam": {"type": "string", "format": "file-path", "exists": True, "pattern": "^\\S+\\.bam$"},
        "bai": {"type": "string", "format": "file-path", "exists": True, "pattern": "^\\S+\\.bai$"},
        "vcf": {"type": "string", "format": "file-path", "exists": True,
                "pattern": "^\\S+\\.vcf(\\.gz)?$"},
        "variantcaller": {"type": "string"},
    }, "required": ["patient", "sample"],
        "anyOf": [{"dependentRequired": {"lane": ["fastq_1"]}},
                  {"dependentRequired": {"lane": ["bam"]}}],
        "dependentRequired": {"fastq_2": ["fastq_1"]}}},
}

MAG = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "run": {"type": ["string", "integer"], "pattern": "^\\S+$", "meta": ["run"]},
        "group": {"type": ["string", "integer"], "pattern": "^\\S+$", "meta": ["group"]},
        "short_reads_1": _fastq(FASTQ_LEGACY),
        "short_reads_2": _fastq(FASTQ_LEGACY),
        "short_reads_platform": {"type": "string", "enum": ["ILLUMINA", "BGISEQ", "ELEMENT"],
                                 "meta": ["sr_platform"]},
        "long_reads": _fastq(FASTQ_LEGACY),
        "long_reads_platform": {"type": "string", "enum": ["OXFORD_NANOPORE", "PACBIO_HIFI"],
                                "meta": ["lr_platform"]},
    }, "required": ["sample", "group"],
        "anyOf": [{"required": ["short_reads_1"]}, {"required": ["long_reads"]}],
        "dependentRequired": {"short_reads_2": ["short_reads_1"],
                              "short_reads_1": ["short_reads_platform"],
                              "long_reads": ["long_reads_platform"]}},
        "uniqueEntries": ["sample", "run"]},
}

AMPLISEQ = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json",
              "pattern": "^\\S+\\.(tsv|csv|yml|yaml|txt)$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": "string", "pattern": "^[a-zA-Z][a-zA-Z0-9_]+$", "meta": ["sample"]},
        "fastq_1": _fastq(),
        "fastq_2": _fastq(),
        "run": {"type": ["string", "integer"], "pattern": "^\\S+$", "default": "1",
                "meta": ["run"]},
    }, "required": ["sample", "fastq_1"]}, "uniqueEntries": ["sample"]},
}

CREATEPANELREFS = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "bam": {"type": "string", "format": "file-path", "exists": True, "pattern": "^\\S+\\.bam$"},
        "bai": {"type": "string", "format": "file-path", "exists": True, "pattern": "^\\S+\\.bai$"},
        "cram": {"type": "string", "format": "file-path", "exists": True,
                 "pattern": "^\\S+\\.cram$"},
        "crai": {"type": "string", "format": "file-path", "exists": True,
                 "pattern": "^\\S+\\.crai$"},
    }, "required": ["sample"], "oneOf": [{"required": ["bam"]}, {"required": ["cram"]}]}},
}

SCNANOSEQ = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "fastq": _fastq(),
        "cell_count": {"type": "integer"},
    }, "required": ["sample", "fastq", "cell_count"]}},
}

TAXPROFILER = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample": {"type": ["string", "integer"], "pattern": "^[^\\s]+$", "meta": ["id"]},
        "run_accession": {"type": ["string", "integer"], "pattern": "^[^\\s]+$"},
        "instrument_platform": {"type": "string",
                                "enum": ["ILLUMINA", "OXFORD_NANOPORE", "PACBIO_SMRT"]},
        "fastq_1": _fastq(FASTQ_LEGACY),
        "fastq_2": _fastq(FASTQ_LEGACY),
        "fasta": {"type": "string", "format": "file-path", "exists": True,
                  "pattern": "^\\S+\\.(fasta|fas|fna|fa)\\.gz?$"},
    }, "required": ["sample", "run_accession", "instrument_platform"]},
        "allOf": [{"uniqueEntries": ["fastq_1"]}, {"uniqueEntries": ["fastq_2"]},
                  {"uniqueEntries": ["fasta"]}, {"uniqueEntries": ["sample", "run_accession"]}]},
}

BAMTOFASTQ = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.csv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample_id": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "mapped": {"type": "string", "format": "file-path", "exists": True,
                   "pattern": "^\\S+\\.(bam|cram)$"},
        "index": {"type": "string", "format": "file-path", "exists": True,
                  "pattern": "^\\S+\\.(bai|crai)$"},
        "file_type": {"type": "string", "enum": ["bam", "cram"], "meta": ["filetype"]},
    }, "required": ["sample_id", "mapped", "file_type"]}},
}

# airrflow's read columns name files without declaring a file type: nothing to match files against.
AIRRFLOW = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.tsv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "sample_id": {"type": ["string", "number"], "pattern": "^\\S+$", "meta": ["id"]},
        "filename_R1": {"type": "string", "pattern": "^\\S+$"},
        "filename_R2": {"type": "string", "pattern": "^\\S+$"},
    }, "required": ["sample_id"]}},
}

# drop: a required column with a schema default, written as a TSV.
DROP = {
    "input": {"type": "string", "format": "file-path", "exists": True,
              "schema": "assets/schema_input.json", "pattern": "^\\S+\\.tsv$"},
    "sheet": {"items": {"type": "object", "properties": {
        "RNA_ID": {"type": ["string", "integer"], "pattern": "^\\S+$", "meta": ["id"]},
        "RNA_BAM_FILE": {"type": "string", "format": "file-path", "exists": True,
                         "pattern": "^\\S+\\.(bam|cram)$"},
        "RNA_BAI_FILE": {"type": "string", "format": "file-path", "exists": True,
                         "pattern": "^\\S+\\.(bam|cram)\\.(bai|crai)$"},
        "STRAND": {"type": "string", "enum": ["yes", "no", "reverse"], "default": "no",
                   "meta": ["strand"]},
    }, "required": ["RNA_ID", "STRAND"]}},
}

# rangeland: --input is a directory of images, not a samplesheet — never generated.
NO_SHEET = {
    "input": {"type": "string", "format": "path", "exists": True},
    "sheet": None,
}


def make_pipeline(root: Path, spec: dict, name: str = "pipe") -> Path:
    """Lay out `spec` as the pinned tree `root/pipelines/<name>/upstream` and return that tree."""
    up = root / "pipelines" / name / "upstream"
    (up / "assets").mkdir(parents=True, exist_ok=True)
    (up / "nextflow_schema.json").write_text(json.dumps({
        "title": f"nf-core/{name}", "definitions": {"io": {"properties": {
            "input": spec["input"], "outdir": {"type": "string", "format": "directory-path"}},
            "required": ["input", "outdir"]}}}))
    if spec["sheet"] is not None:
        (up / "assets" / "schema_input.json").write_text(json.dumps(spec["sheet"]))
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    (up.parent / "skill.md").write_text(f"---\nname: {name}\n---\n")
    return up
