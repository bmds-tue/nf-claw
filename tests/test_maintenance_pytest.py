"""Publication refuses incomplete reports and undeclared skipped coverage."""
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def check(path, os_name='ubuntu-latest', python='3.12'):
    spec = importlib.util.spec_from_file_location('maintenance_pytest',
        ROOT / 'scripts/check_maintenance_pytest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_report(path, os_name, python)


def report(tmp_path, skip=None, *, error=None):
    root = ET.Element('testsuites')
    suite = ET.SubElement(root, 'testsuite')
    for index in range(3001):
        ET.SubElement(suite, 'testcase', classname='tests.test_example', name=f'test_{index}')
    if skip:
        classname, name, reason = skip
        case = ET.SubElement(suite, 'testcase', classname=classname, name=name)
        ET.SubElement(case, 'skipped', message=reason)
    if error:
        ET.SubElement(suite[0], error, message='unsuccessful test')
    path = tmp_path / 'report.xml'
    ET.ElementTree(root).write(path)
    return path


def test_complete_report_records_executed_count_and_explicit_obsolete_audit_skip(tmp_path):
    path = report(tmp_path, ('tests.test_legacy_sheet_paths',
        'test_audited_schema_roles_match_the_pins_and_capture_each_data_cell[rnasplice]',
        'rnasplice is no longer pinned at the audited commit 1d0494f3255c'))
    value = check(path)
    assert value['passed'] == 3001
    assert value['skipped'][0]['reason'].startswith('rnasplice is no longer pinned')


@pytest.mark.parametrize('reason', ['requires initialized pinned pipeline source',
    'requires a real Nextflow engine',
    'needs node and the website dependencies (`npm ci` in website/)',
    "could not import 'h5py': No module named 'h5py'"])
def test_missing_declared_dependencies_cannot_look_like_a_full_matrix(tmp_path, reason):
    path = report(tmp_path, ('tests.test_example', 'test_depends_on_source', reason))
    with pytest.raises(ValueError):
        check(path)


@pytest.mark.parametrize('error', ['failure', 'error'])
def test_failed_report_is_refused_even_if_its_job_claimed_success(tmp_path, error):
    with pytest.raises(ValueError):
        check(report(tmp_path, error=error))


def test_empty_or_truncated_suite_cannot_be_accepted(tmp_path):
    path = tmp_path / 'report.xml'
    path.write_text('<testsuites><testsuite><testcase name="only-one"/></testsuite></testsuites>')
    with pytest.raises(ValueError):
        check(path)


def test_linux_only_skip_is_allowed_only_in_the_macos_lane(tmp_path):
    path = report(tmp_path, ('tests.test_execution',
                             'test_teardown_kills_a_task_that_outlives_sigterm',
                             'reads process state from /proc'))
    assert check(path, 'macos-latest')['passed'] == 3001
    with pytest.raises(ValueError):
        check(path)


def test_h5ad_exception_applies_only_to_macos_python315_and_its_module(tmp_path):
    path = report(tmp_path, ('tests.test_scientific_h5ad', '',
                             "could not import 'h5py': No module named 'h5py'"))
    assert check(path, 'macos-latest', '3.15')['passed'] == 3001
    with pytest.raises(ValueError):
        check(path, 'macos-latest', '3.14')
    with pytest.raises(ValueError):
        check(path, 'ubuntu-latest', '3.15')
