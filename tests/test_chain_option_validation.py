"""Malformed chain run options fail at the boundary, before preparing any stage."""
import pytest

from runner import chain, resources
from runner.errors import NfclawError


@pytest.mark.parametrize('stage', [False, True], ids=['chain', 'stage'])
@pytest.mark.parametrize('key,value', [
    ('nxf_env', 1), ('nxf_env', [1]), ('nxf_env', False), ('nxf_env', ''),
    ('nxf_env', []), ('nxf_env', ['NXF_OFFLINE=true']),
    ('nxf_ver', False), ('nxf_ver', 0), ('nxf_ver', ''),
    ('limits', {'memory': 12}), ('limits', {'memory': False}),
    ('limits', {'time': 12}), ('limits', {'time': []}),
    ('config', ['']), ('config', ['   ']),
])
def test_invalid_options_are_reported_as_chain_spec_errors(stage, key, value):
    data = {'stages': [{'pipeline': 'mini'}]}
    (data['stages'][0] if stage else data)[key] = value
    with pytest.raises(NfclawError, match='chain spec:'):
        chain.parse_spec(data)


@pytest.mark.parametrize('key', ['nxf_env', 'nxf_ver', 'limits', 'config'])
def test_null_chain_options_keep_the_default(key):
    spec = chain.parse_spec({'stages': [{'pipeline': 'mini'}], key: None})
    assert spec.nxf_env == {} and spec.nxf_ver is None and spec.limits is None
    assert spec.configs == ()


def test_cli_environment_assignments_still_accept_lists_of_strings():
    assert resources.parse_nxf_env(['NXF_OFFLINE=true']) == {'NXF_OFFLINE': 'true'}


@pytest.mark.parametrize('value', [True, 1.5, '4', [], {}])
def test_cpu_limits_reject_noninteger_types(value):
    with pytest.raises(NfclawError, match='--limit-cpus'):
        resources.parse(value, None, None)


@pytest.mark.parametrize('field', ['memory', 'time'])
@pytest.mark.parametrize('value', [False, 12, [], {}])
def test_resource_limits_reject_nonstring_units(field, value):
    with pytest.raises(NfclawError, match=f'--limit-{field}'):
        resources.parse(None, value if field == 'memory' else None,
                        value if field == 'time' else None)


@pytest.mark.parametrize('option', [{'nxf_ver': False}, {'limits': {'memory': 12}}])
def test_cli_refuses_invalid_chain_options_without_writing_outputs(tmp_path, capsys, option):
    import json

    from runner import cli

    spec = tmp_path / 'spec.json'
    spec.write_text(json.dumps({'stages': [{'pipeline': 'mini'}], **option}))
    outdir = tmp_path / 'results'
    assert cli.main(['chain', 'run', str(spec), '--outdir', str(outdir), '--check']) == 1
    error = capsys.readouterr().err
    assert '[params_invalid]' in error and 'Traceback' not in error
    assert not outdir.exists()
