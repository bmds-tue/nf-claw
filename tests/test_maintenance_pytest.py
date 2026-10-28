"""Publication refuses incomplete reports and undeclared skipped coverage."""
import importlib.util
import platform
import subprocess
import sys
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


@pytest.mark.parametrize('module,reason', [
    ('tests.test_demo_fastqrepair', 'requires the audited fastqrepair 1.1.1 source'),
    ('tests.test_bactmap_corrections',
     'bactmap is no longer pinned at the audited commit 834642d8ac15')])
def test_obsolete_recipe_skip_is_scoped_to_exact_module_and_reason(tmp_path, module, reason):
    path = report(tmp_path, (module, 'test_bare_demo', reason))
    assert check(path)['skipped'][0]['reason'] == reason
    with pytest.raises(ValueError):
        check(report(tmp_path, ('tests.test_example', 'test_bare_demo', reason)))
    with pytest.raises(ValueError):
        check(report(tmp_path, (module, 'test_bare_demo',
                               'requires initialized pinned pipeline source')))
    with pytest.raises(ValueError):
        check(report(tmp_path, (module, 'test_bare_demo', 'requires audited bactmap source')))


def test_receipt_refuses_a_deleted_source_file_even_at_the_registered_pin(tmp_path, monkeypatch):
    def git(path, *args):
        return subprocess.check_output([
            'git', '-c', 'user.name=Audit test', '-c', 'user.email=audit@example.org',
            '-c', 'commit.gpgsign=false', '-c', 'protocol.file.allow=always', *args],
            cwd=path, text=True, stderr=subprocess.DEVNULL).strip()

    upstream, repo = tmp_path / 'upstream', tmp_path / 'repo'
    upstream.mkdir()
    repo.mkdir()
    git(upstream, 'init')
    (upstream / 'nextflow_schema.json').write_text('{}')
    git(upstream, 'add', '.')
    git(upstream, 'commit', '-m', 'source')
    git(repo, 'init')
    git(repo, 'submodule', 'add', str(upstream), 'pipelines/mini/upstream')
    git(repo, 'commit', '-am', 'pin')
    candidate = git(repo, 'rev-parse', 'HEAD')
    path = report(repo)
    output = repo / 'receipt.json'
    spec = importlib.util.spec_from_file_location('maintenance_pytest',
        ROOT / 'scripts/check_maintenance_pytest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(sys, 'argv', ['check', '--report', str(path), '--os',
        'ubuntu-latest' if platform.system() == 'Linux' else 'macos-latest', '--python',
        f'{sys.version_info.major}.{sys.version_info.minor}', '--candidate', candidate,
        '--output', str(output)])
    module.main()
    assert output.is_file()
    output.unlink()
    (repo / 'pipelines/mini/upstream/nextflow_schema.json').unlink()
    # Submodule status still reports the expected concrete HEAD with a leading space.
    assert git(repo, 'submodule', 'status').split()[0] == git(upstream, 'rev-parse', 'HEAD')
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 1
    assert not output.exists()
