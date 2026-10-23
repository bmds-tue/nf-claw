import json
import sys

import pytest

from runner import parameters, schema


def load(tmp_path, property_schema):
    (tmp_path / 'nextflow_schema.json').write_text(
        json.dumps({'properties': {'choice': property_schema}}))
    return schema.load_param_schema(tmp_path)


@pytest.mark.parametrize('definition,accepted,rejected', [
    ({'type': 'string', 'enum': ['1', 'true']}, ['1', 'true'], [1, True]),
    ({'type': 'number', 'enum': [9007199254740993]}, [9007199254740993], [9007199254740992.0]),
    ({'type': 'boolean', 'enum': [True]}, [True], ['true', 1]),
    ({'type': 'integer', 'enum': [1]}, [1, 1.0], [True, '1', 1.5]),
    ({'enum': ['auto', 1, True]}, ['auto', 1, 1.0, True], ['1', 'true', 2]),
    ({'enum': [{'x': [True, 2]}]}, [{'x': [True, 2.0]}], [{'x': [1, 2]}]),
    ({'type': 'string', 'enum': [1]}, [], [1, '1']),
    ({'type': 'string', 'enum': ['bad'], 'pattern': '^good$'}, [], ['bad']),
    ({'type': 'number', 'enum': [2], 'maximum': 1}, [], [2]),
    ({'enum': []}, [], ['anything', 1, True]),
    ({'type': 'array', 'enum': ['1', [1]]}, [[1.0]], ['1', 1]),
    ({'type': 'object', 'enum': ['1', {'x': True}]}, [{'x': True}], ['1', {'x': 1}]),
])
def test_typed_enum_and_independent_constraints(tmp_path, definition, accepted, rejected):
    parsed = load(tmp_path, definition)
    for value in accepted:
        assert parameters.validate_params({'choice': value}, parsed) == []
    for value in rejected:
        assert parameters.validate_params({'choice': value}, parsed)


def test_cli_coercion_precedes_typed_enum_validation(tmp_path):
    parsed = load(tmp_path, {'type': 'boolean', 'enum': [True]})
    coerced = parameters.coerce_to_schema({'choice': 'true'}, parsed)
    assert parameters.validate_params(coerced, parsed) == []


def test_number_cli_integer_token_retains_all_digits(tmp_path):
    parsed = load(tmp_path, {'type': 'number', 'enum': [9007199254740993]})
    coerced = parameters.coerce_to_schema({'choice': '9007199254740993'}, parsed)
    assert coerced == {'choice': 9007199254740993}
    assert isinstance(coerced['choice'], int)
    assert parameters.validate_params(coerced, parsed) == []


def test_enum_comparison_handles_shared_nested_values_without_expansion(tmp_path):
    parsed = load(tmp_path, {'enum': [[[1], [1]]]})
    shared = [1]
    assert parameters.validate_params({'choice': [shared, shared]}, parsed) == []


def test_number_cli_integer_digit_limit_reports_validation_error(tmp_path):
    limit = sys.get_int_max_str_digits()
    if not limit:
        pytest.skip('Python integer digit limit is disabled')
    token = '1' * (limit + 1)
    parsed = load(tmp_path, {'type': 'number'})
    coerced = parameters.coerce_to_schema({'choice': token}, parsed)
    assert coerced == {'choice': token}
    assert any('expects a number' in issue for issue in parameters.validate_params(coerced, parsed))
