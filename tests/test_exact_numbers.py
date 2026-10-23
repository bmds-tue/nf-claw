"""Decimal text is an independent oracle for the JSON that Nextflow will actually read."""
import json
from decimal import Decimal, localcontext

import pytest

from runner import chain, exact_json, parameters, samplesheet, schema, submodule


TOKENS = ("9007199254740993.0", "9007199254740993e0", "100000000000000000000001e0", "1e-9999",
          "1e9999", "0.1000000000000000000001", "-0.1000000000000000000001", "1.25", "0.1",
          "2.2250738585072014e-308", "5e-324", "0.0", "-0.0")


@pytest.mark.parametrize("token", TOKENS)
def test_cli_numbers_and_serialized_json_preserve_decimal_value(tmp_path, token):
    parsed = schema.ParamSchema("test", "", {
        "choice": schema.Param("choice", "number", None, None, "", None, False, "")})
    value = parameters.coerce_to_schema({"choice": token}, parsed)
    assert not parameters.validate_params(value, parsed)
    target = tmp_path / "params.json"
    parameters.write_params_file(value, target)
    observed = json.loads(target.read_text(), parse_float=Decimal)
    assert observed["choice"] == Decimal(token)


@pytest.mark.parametrize("token", ["_1", "1__0", "1e+", ".", "not-a-number"])
def test_invalid_numeric_tokens_are_not_silently_reinterpreted(token):
    parsed = schema.ParamSchema("test", "", {
        "choice": schema.Param("choice", "number", None, None, "", None, False, "")})
    value = parameters.coerce_to_schema({"choice": token}, parsed)
    assert value["choice"] == token
    assert parameters.validate_params(value, parsed)


@pytest.mark.parametrize("value", [-(1 << 63) - 1, -(1 << 63), (1 << 63) - 1,
                                   1 << 63, (1 << 63) + 1, 10 ** 23])
def test_integer_wire_notation_avoids_native_signed_long_overflow(value):
    text = exact_json.dumps({"value": value, "decimal": Decimal(value)}, nextflow_compatible=True)
    observed = json.loads(text, parse_float=Decimal)
    assert observed["value"] == value
    assert observed["decimal"] == value
    assert isinstance(observed["decimal"], Decimal)
    assert isinstance(observed["value"], Decimal) == (not -(1 << 63) <= value < (1 << 63))
    record = exact_json.dumps({"value": value, "precise": Decimal("0.1000000000000000000001")})
    assert isinstance(json.loads(record)["value"], int)


@pytest.mark.parametrize("suffix", ["json", "yaml"])
def test_nested_parameter_records_preserve_precision_and_aliases(tmp_path, suffix):
    if suffix == "yaml":
        pytest.importorskip("yaml")
        text = ("values: &values [9007199254740993.0, 1.0e-9999, 0.1000000000000000000001]\n"
                "copy: *values\n")
    else:
        text = '{"values": [9007199254740993.0, 1e-9999, 0.1000000000000000000001]}'
    source = tmp_path / f"input.{suffix}"
    source.write_text(text)
    values = parameters.load_params_file(source)
    if suffix == "yaml":
        assert values["copy"] is values["values"]
    target = tmp_path / "params.json"
    parameters.write_params_file(values, target)
    observed = json.loads(target.read_text(), parse_float=Decimal)
    assert observed["values"] == [Decimal("9007199254740993"), Decimal("1e-9999"),
                                 Decimal("0.1000000000000000000001")]
    if suffix == "yaml":
        assert observed["copy"] == observed["values"]


def test_precise_schema_enum_and_boundaries_compare_emitted_numbers(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text('''{"properties": {
      "choice": {"type": "number", "enum": [0.1000000000000000000001]},
      "limit": {"type": "number", "maximum": 0.1000000000000000000001}}}''')
    parsed = schema.load_param_schema(tmp_path)
    assert not parameters.validate_params({"choice": Decimal("0.1000000000000000000001")}, parsed)
    assert parameters.validate_params({"choice": 0.1}, parsed)
    assert not parameters.validate_params({"limit": 0.1}, parsed)
    assert parameters.validate_params({"limit": Decimal("0.1000000000000000000002")}, parsed)
    assert not parameters.validate_params({"limit": Decimal("0.1000000000000000000000")}, parsed)


def test_structured_schema_values_do_not_expose_python_decimal_representation():
    value = {"nested": [Decimal("0.1000000000000000000001"), True, None]}
    rendered = schema.json_scalar(value)
    assert json.loads(rendered, parse_float=Decimal) == value
    assert "Decimal" not in rendered
    assert schema.json_scalar(None) == "null"


def test_precise_integral_decimal_has_json_schema_integer_type():
    parsed = schema.ParamSchema("test", "", {
        "choice": schema.Param("choice", "integer", None, None, "", None, False, "")})
    assert not parameters.validate_params({"choice": Decimal("9007199254740993.0")}, parsed)
    assert parameters.validate_params({"choice": Decimal("1.0000000000000000000001")}, parsed)


@pytest.mark.parametrize("value", ["9007199254740993.0", "9007199254740993e0", "1e23",
                                   1e23, Decimal("9007199254740993.0"), Decimal("1e999999999")])
def test_integer_coercion_preserves_emitted_decimal_and_compact_extreme_exponents(tmp_path, value):
    parsed = schema.ParamSchema("test", "", {
        "choice": schema.Param("choice", "integer", None, None, "", None, False, "")})
    values = parameters.coerce_to_schema({"choice": value}, parsed)
    assert not parameters.validate_params(values, parsed)
    target = tmp_path / "params.json"
    parameters.write_params_file(values, target)
    observed = json.loads(target.read_text(), parse_float=Decimal)
    assert observed["choice"] == Decimal(str(value))
    assert target.stat().st_size < 100  # no expansion of the extreme exponent into digits


def test_numeric_samplesheet_boundary_is_not_rounded(tmp_path):
    column = schema.Column("value", "number", False, None,
                           maximum=Decimal("0.1000000000000000000001"))
    assert not samplesheet.value_problems(column, "0.1")
    assert samplesheet.value_problems(column, "0.1000000000000000000002")
    path = tmp_path / "samples.csv"
    path.write_text("value\n0.1000000000000000000002\n")
    assert any("must be <=" in issue
               for issue in samplesheet.validate(path, schema.InputSchema((column,))))


def test_yaml_sample_scalar_and_sexagesimal_formats_retain_precision(tmp_path):
    pytest.importorskip("yaml")
    source = tmp_path / "samples.yaml"
    source.write_text("- value: 9007199254740993.0\n  fraction: 0.1000000000000000000001\n")
    row = samplesheet.serialized_rows(source)[0]
    assert row["value"] == Decimal("9007199254740993")
    assert row["fraction"] == Decimal("0.1000000000000000000001")
    source = tmp_path / "params.yaml"
    source.write_text("positive: 1:00.1000000000000000000001\n"
                      "negative: -1:00.1000000000000000000001\n")
    params = parameters.load_params_file(source)
    assert params["positive"] == Decimal("60.1000000000000000000001")
    assert params["negative"] == Decimal("-60.1000000000000000000001")


def test_invalid_explicit_yaml_float_is_a_preflight_error(tmp_path):
    pytest.importorskip("yaml")
    path = tmp_path / "params.yaml"
    path.write_text("choice: !!float not-a-number\n")
    with pytest.raises(parameters.NfclawError, match="not valid YAML"):
        parameters.load_params_file(path)


@pytest.mark.parametrize("token", ["0.1000000000000000000001", "100000000000000000000000",
                                   "1e23", "100000000000000000000001e0"])
def test_chain_records_and_fingerprints_preserve_decimal_parameters(tmp_path, token):
    path = tmp_path / "chain.json"
    path.write_text('{"stages":[{"pipeline":"fixture","params":{"choice":'+token+'}}]}')
    spec = chain.load_spec(path)
    stage = spec.stages[0]
    planned = chain.Planned(
        stage, submodule.SubmoduleStatus("fixture", tmp_path, True, True, "test", "test", ()), None,
        None, stage.params)
    value = stage.params["choice"]
    assert exact_json.decimal(value) == Decimal(token)
    normalized = chain.normalized(spec, [planned])
    saved = chain._write_json(tmp_path / "saved.json", normalized)
    recovered = chain.load_spec(saved)
    assert recovered.stages[0].params["choice"] == value
    recovered_plan = chain.Planned(recovered.stages[0], planned.tree, None, None,
                                   recovered.stages[0].params)
    assert chain.fingerprint(recovered_plan, recovered) == chain.fingerprint(planned, spec)
    rounded = chain.Planned(stage, planned.tree, None, None, {"choice": 0.1})
    assert chain.fingerprint(planned, spec) != chain.fingerprint(rounded, spec)


@pytest.mark.parametrize("indent", [None, 0, 2, "\t"])
@pytest.mark.parametrize("separators", [None, (",", ":")])
def test_decimal_encoder_keeps_standard_json_structure_and_escaping(indent, separators):
    ordinary = {"b": [0.5, None, True, "line\nquote\"\\\u2028"], "a": {"nested": []}}
    precise = {"b": [Decimal("0.5"), None, True, "line\nquote\"\\\u2028"], "a": {"nested": []}}
    options = dict(indent=indent, sort_keys=True, separators=separators, ensure_ascii=False)
    assert exact_json.dumps(precise, **options) == json.dumps(ordinary, **options)


def test_precision_does_not_depend_on_decimal_arithmetic_context():
    with localcontext() as context:
        context.prec = 2
        for token in TOKENS:
            text = exact_json.dumps(exact_json.number(token))
            assert json.loads(text, parse_float=Decimal) == Decimal(token)


@pytest.mark.parametrize(
    "value", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_nonfinite_decimals_cannot_be_validated_or_written(tmp_path, value):
    parsed = schema.ParamSchema("test", "", {
        "choice": schema.Param("choice", "number", None, None, "", None, False, "")})
    assert any("finite" in error for error in parameters.validate_params({"choice": value}, parsed))
    with pytest.raises(ValueError):
        exact_json.dumps({"choice": value})
    with pytest.raises(parameters.NfclawError):
        parameters.write_params_file({"choice": value}, tmp_path / "params.json")
    assert not (tmp_path / "params.json").exists()


def test_decimal_serialization_preserves_shared_values_and_refuses_cycles():
    shared = [Decimal("0.1000000000000000000001")]
    decoded = json.loads(exact_json.dumps([shared, shared]), parse_float=Decimal)
    assert decoded == [shared, shared]
    shared.append(shared)
    with pytest.raises(ValueError, match="Circular"):
        exact_json.dumps(shared)


def test_decimal_json_serialization_round_trips_many_magnitudes():
    tokens = [f"{coefficient}e{exponent}" for coefficient in
              ("1.0000000000000000000001", "-9007199254740993.1", "0.1", "1.25")
              for exponent in (-9999, -324, -308, -17, -1, 0, 1, 17, 308, 9999)]
    text = exact_json.dumps([exact_json.number(token) for token in tokens])
    assert json.loads(text, parse_float=Decimal) == [Decimal(token) for token in tokens]
