"""Acceptance must compile managed releases under the same bounded preparation lifecycle."""
import importlib.util
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / 'scripts/nextflow_preview.py'
COMMIT = '834642d8ac150ca10d705833223e7bcf15efc210'


def load():
    spec = importlib.util.spec_from_file_location('preview_stager', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def options(tmp_path, *, name='bactmap', commit=COMMIT):
    return SimpleNamespace(name=name, commit=commit, repo_root=tmp_path,
                           upstream=tmp_path / f'pipelines/{name}/upstream',
                           config=tmp_path / 'no-reports.config', outdir=tmp_path / 'out',
                           work=tmp_path / 'work', engine_log=tmp_path / 'engine.log',
                           scratch=tmp_path / 'scratch', version='24.10.5')


def test_ordinary_release_keeps_direct_preview_without_managed_preparation(tmp_path, monkeypatch):
    module = load()
    args = options(tmp_path, name='mini', commit='0' * 40)
    def forbidden(*a, **kw):
        pytest.fail('ordinary releases must retain their existing direct preview')
    monkeypatch.setattr(module.orchestration, 'run_pipeline', forbidden)
    command, env, cwd = module.prepare(args)
    assert command == ['nextflow', '-log', str(args.engine_log), 'run', str(args.upstream),
                       '-profile', 'test,docker', '-c', str(args.config), '--outdir',
                       str(args.outdir), '-work-dir', str(args.work), '-preview']
    assert env['NXF_VER'] == args.version
    assert cwd is None


def test_managed_preview_preserves_source_parameters_and_environment(tmp_path, monkeypatch):
    module = load()
    args = options(tmp_path)
    st = SimpleNamespace(commit=COMMIT, path=args.upstream)
    monkeypatch.setattr(module.submodule, 'resolve', lambda *a, **kw: st)
    corrected = args.scratch / 'nfclaw-check-x/pipeline'
    params = args.scratch / 'nfclaw-check-x/params.json'
    def check(name, **kw):
        assert name == 'bactmap'
        assert kw['check_only'] and kw['demo']
        assert kw['resolved_tree'] is st
        assert not kw.get('configs')
        assert kw['nxf_env']['NXF_WORK'] == str(args.work)
        return SimpleNamespace(command=f'nextflow run {corrected} -profile test,docker '
                               f'-params-file {params} -work-dir {args.work}',
                               env={'NXF_VER': args.version, 'NXF_SYNTAX_PARSER': 'v1'})
    monkeypatch.setattr(module.orchestration, 'run_pipeline', check)
    command, env, cwd = module.prepare(args)
    assert command[:3] == ['nextflow', '-log', str(args.engine_log)]
    assert command[command.index('run') + 1] == str(corrected)
    assert command[command.index('-params-file') + 1] == str(params)
    assert command[-5:] == ['-c', str(args.config), '--outdir', str(args.outdir), '-preview']
    assert env['NXF_SYNTAX_PARSER'] == 'v1'
    assert cwd == args.outdir


@pytest.mark.parametrize('change', ['commit', 'path'])
def test_managed_preparation_cannot_substitute_another_release(tmp_path, monkeypatch, change):
    module = load()
    args = options(tmp_path)
    st = SimpleNamespace(commit='0' * 40 if change == 'commit' else COMMIT,
                         path=tmp_path / 'other' if change == 'path' else args.upstream)
    monkeypatch.setattr(module.submodule, 'resolve', lambda *a, **kw: st)
    with pytest.raises(ValueError, match='(?i)(release|source|commit)'):
        module.prepare(args)


def test_preparation_refuses_instead_of_falling_back_to_uncorrected_preview(tmp_path, monkeypatch):
    module = load()
    args = options(tmp_path)
    monkeypatch.setattr(module.submodule, 'resolve', lambda *a, **kw:
                        SimpleNamespace(commit=COMMIT, path=args.upstream))
    def fail(*a, **kw):
        raise ValueError('changed source')
    monkeypatch.setattr(module.orchestration, 'run_pipeline', fail)
    with pytest.raises(ValueError, match='changed source'):
        module.prepare(args)


def test_term_during_preparation_stops_separately_sessioned_probe(tmp_path):
    # Run the real main/signal/probe boundary; the probe would write after cleanup if orphaned.
    ready = tmp_path / 'ready'
    marker = tmp_path / 'orphaned'
    bootstrap = tmp_path / 'bootstrap.py'
    bootstrap.write_text('''import importlib.util, sys
from runner.probes import capture
spec = importlib.util.spec_from_file_location('stager', sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def prepare(args):
    capture([sys.executable, '-c', sys.argv[2]], timeout=30)
m.prepare = prepare
m.main(sys.argv[3:])
''')
    child = (f'from pathlib import Path; import time; Path({str(ready)!r}).write_text("ready"); '
             f'time.sleep(2); Path({str(marker)!r}).write_text("orphaned"); time.sleep(20)')
    args = options(tmp_path)
    argv = [sys.executable, str(bootstrap), str(HELPER), child]
    for key, value in vars(args).items():
        argv += ['--' + key.replace('_', '-'), str(value)]
    env = {**os.environ, 'PYTHONPATH': str(ROOT), 'NFCLAW_SHUTDOWN_GRACE': '0.1'}
    proc = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), proc.communicate(timeout=2)
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=5)
        time.sleep(2.2)
        assert not marker.exists(), 'a preparation probe survived the acceptance timeout'
        assert proc.returncode != 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()


def test_handlers_are_restored_before_exec(tmp_path, monkeypatch):
    module = load()
    args = options(tmp_path)
    original = signal.getsignal(signal.SIGTERM)
    def prepare(options):
        assert signal.getsignal(signal.SIGTERM) != original
        return ['nextflow', '-preview'], {'NXF_SYNTAX_PARSER': 'v1'}, None
    monkeypatch.setattr(module, 'prepare', prepare)
    observed = []
    def execute(program, command, env):
        observed.append((program, command, env))
        assert signal.getsignal(signal.SIGTERM) == original
    monkeypatch.setattr(module.os, 'execvpe', execute)
    argv = []
    for key, value in vars(args).items():
        argv += ['--' + key.replace('_', '-'), str(value)]
    module.main(argv)
    assert observed[0][2]['NXF_SYNTAX_PARSER'] == 'v1'
