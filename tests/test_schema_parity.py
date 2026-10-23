import json
from pathlib import Path

import pytest

from runner import schema

REPO = Path(__file__).resolve().parent.parent
SAREK = REPO / "pipelines" / "sarek" / "upstream"
ALLOWLIST = Path(__file__).parent / "fixtures" / "golden" / "sarek_allowlist.txt"

# Flags that were CONTROLS in the legacy Sarek wrapper (not nf-core/sarek params);
# these are intentionally NOT in the pipeline schema.
WRAPPER_CONTROLS = {
    "check", "resume", "arm", "gpu", "spark_profile", "mutect_profile",
    "run_downstream", "downstream_skill", "profile", "nextflow_config",
    "pipeline_version", "pipeline_local", "params_file", "no_banner",
    "verbose", "extra_param",
}


def _declared_property_names(node) -> set[str]:
    """Every key under any `properties` object in the raw schema — a superset of the pipeline's
    parameter names. Used to tell an *upstream removal* (a legacy flag that no longer exists in the
    schema at all) apart from a *parser regression* (a param the schema still declares but that
    `load_param_schema` dropped). nf-claw wraps pipelines unmodified, so a param upstream deleted is
    correctly absent and must not fail this test; a param the schema still declares must not
    be lost.
    """
    names: set[str] = set()
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            names |= set(props)
        for value in node.values():
            names |= _declared_property_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= _declared_property_names(value)
    return names


@pytest.mark.skipif(not (SAREK / "nextflow_schema.json").exists(),
                    reason="sarek submodule not initialized")
def test_schema_covers_legacy_sarek_allowlist():
    legacy = {
        line.strip().lstrip("-").replace("-", "_")
        for line in ALLOWLIST.read_text().split()
        if line.strip()
    } - WRAPPER_CONTROLS
    known = schema.load_param_schema(SAREK).known_params()
    declared = _declared_property_names(
        json.loads((SAREK / "nextflow_schema.json").read_text(encoding="utf-8")))
    # A legacy flag missing from `known` is fine when upstream removed it from the schema entirely
    # (e.g. `hook_url`, dropped from the nf-core template). The regression this guards is the parser
    # dropping a param the pinned schema STILL declares — that intersection must be empty.
    parser_dropped = (legacy - known) & declared
    assert parser_dropped == set(), \
        ("schema declares these legacy sarek flags but the parser dropped "
         f"them: {sorted(parser_dropped)}")
