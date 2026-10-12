from pathlib import Path

from runner import schema

FIX = Path(__file__).parent / "fixtures"


def test_loads_params_and_refs():
    ps = schema.load_param_schema(FIX / "mini")
    assert {"input", "outdir", "fasta", "aligner"} <= ps.known_params()
    assert ps.reference_path_params() == {"input", "outdir", "fasta"}
    assert ps.params["aligner"].enum == ("star", "hisat2")
    assert ps.params["aligner"].default == "star"


def test_groups_present():
    ps = schema.load_param_schema(FIX / "mini")
    assert "reference_genome_options" in ps.groups()


def test_input_schema_columns():
    insch = schema.load_input_schema(FIX / "mini")
    cols = {c.name: c for c in insch.columns}
    assert {"sample", "fastq_1", "fastq_2"} <= set(cols)
    assert cols["fastq_1"].fmt == "file-path" and cols["fastq_1"].is_path is True
    assert cols["sample"].fmt is None and cols["sample"].is_path is False
    assert cols["sample"].required is True


def test_input_schema_captures_dependent_required_rules(tmp_path):
    import json
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(json.dumps({
        "items": {
            "properties": {
                "lane": {"type": "string"},
                "fastq_1": {"type": "string"},
                "fastq_2": {"type": "string"},
                "bam": {"type": "string"},
            },
            "dependentRequired": {"fastq_2": ["fastq_1"]},
            "anyOf": [
                {"dependentRequired": {"lane": ["fastq_1"]}},
                {"dependentRequired": {"lane": ["bam"]}},
            ],
        }
    }))
    insch = schema.load_input_schema(tmp_path)
    assert insch.dependent_required == (("fastq_2", ("fastq_1",)),)
    assert insch.any_of_dependent_required == (
        (("lane", ("fastq_1",)),),
        (("lane", ("bam",)),),
    )


def test_no_input_schema_returns_none():
    assert schema.load_input_schema(FIX / "mini_no_input") is None


def test_anyof_type_unioned(tmp_path):
    import json
    s = {"definitions": {"g": {"properties": {
        "lane": {"anyOf": [{"type": "integer"}, {"type": "string"}], "description": "lane"},
        "plain": {"type": "string"},
    }}}}
    (tmp_path / "nextflow_schema.json").write_text(json.dumps(s))
    ps = schema.load_param_schema(tmp_path)
    assert ps.params["lane"].type == "integer or string"   # was bare "string" before
    assert ps.params["plain"].type == "string"


def test_type_array_is_unioned(tmp_path):
    import json
    s = {"definitions": {"g": {"properties": {
        "help": {"type": ["boolean", "string"], "description": "h"}}}}}
    (tmp_path / "nextflow_schema.json").write_text(json.dumps(s))
    ps = schema.load_param_schema(tmp_path)
    assert ps.params["help"].type == "boolean or string"   # was Python repr "['boolean', 'string']"


def test_boolean_enum_default_are_json_literals(tmp_path):
    import json
    s = {"definitions": {"g": {"properties": {
        "flag": {"type": "boolean", "enum": [False], "default": True}}}}}
    (tmp_path / "nextflow_schema.json").write_text(json.dumps(s))
    ps = schema.load_param_schema(tmp_path)
    assert ps.params["flag"].enum == ("false",)            # JSON literal, not Python "False"
    assert ps.params["flag"].default is True               # raw value kept; rendered later
    assert schema.json_scalar(True) == "true" and schema.json_scalar(False) == "false"
    assert schema.json_scalar(0) == "0" and schema.json_scalar("x") == "x"   # non-bools via str()


def test_config_param_defaults_reads_the_params_block(tmp_path):
    # A required parameter the schema gives no default can still get one from nextflow.config
    # (differentialabundance's filtering_min_abundance = 1); nf-schema sees that value.
    (tmp_path / "nextflow.config").write_text(
        "// header // comment\n"
        "params {\n"
        "    // Options\n"
        "    filtering_min_abundance = 1       // trailing comment\n"
        "    fasta_file = \"s3://bucket/x.fa\"   // a URL is not a comment\n"
        "    method     = 'a,b//c'\n"
        "    genome     = null\n"
        "    nested { inner = 2 }\n"
        "}\n"
        "process { cpus = 4 }\n"
        "outside = 3\n")
    assert schema.config_param_defaults(tmp_path) == {
        "filtering_min_abundance": "1", "fasta_file": '"s3://bucket/x.fa"',
        "method": "'a,b//c'", "genome": "null"}


def test_config_param_defaults_without_a_config(tmp_path):
    assert schema.config_param_defaults(tmp_path) == {}


def test_input_schema_captures_what_samplesheet_generation_needs(tmp_path):
    # Generating a samplesheet from data files needs more of the schema than validating one: the
    # patterns a column accepts inside anyOf/oneOf branches (atacseq declares fastq_2's FastQ pattern
    # only there), defaults, required column alternatives and nf-schema's uniqueEntries.
    import json
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(json.dumps({
        "uniqueEntries": ["sample"],
        "allOf": [{"uniqueEntries": ["fastq_1"]}, {"uniqueEntries": ["sample", "run"]}],
        "items": {
            "properties": {
                "sample": {"type": "string", "pattern": "^\\S+$"},
                "run": {"type": "string"},
                "fastq_1": {"type": "string", "pattern": "^\\S+\\.f(ast)?q\\.gz$"},
                "fastq_2": {"anyOf": [{"type": "string", "pattern": "^\\S+\\.f(ast)?q\\.gz$"},
                                      {"type": "string", "maxLength": 0}]},
                "pbi": {"oneOf": [{"type": "string", "pattern": "^\\S+\\.bam\\.pbi$"},
                                  {"type": "string", "pattern": "^none$"}]},
                "strand": {"type": "string", "enum": ["yes", "no"], "default": "no"},
                "long_reads": {"type": "string", "format": "file-path"},
            },
            "required": ["sample", "strand"],
            "anyOf": [{"required": ["fastq_1"]}, {"required": ["long_reads"]},
                      {"dependentRequired": {"run": ["fastq_1"]}}],
        },
    }))
    insch = schema.load_input_schema(tmp_path)
    cols = {c.name: c for c in insch.columns}
    assert cols["fastq_2"].pattern is None
    assert cols["fastq_2"].alternatives == ("^\\S+\\.f(ast)?q\\.gz$",)
    assert cols["pbi"].alternatives == ("^\\S+\\.bam\\.pbi$", "^none$")
    assert cols["fastq_1"].alternatives == ()
    assert cols["strand"].default == "no" and cols["sample"].default is None
    assert insch.any_of_required == (("fastq_1",), ("long_reads",))
    assert insch.any_of_dependent_required == ((("run", ("fastq_1",)),),)
    assert insch.unique_entries == (("sample",), ("fastq_1",), ("sample", "run"))
