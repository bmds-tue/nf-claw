"""Independent Git output is the oracle for source identity and tracked-file selection."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from runner import fastqrepair_compat, orchestration, provenance, replay_guard, submodule

# How long a real Nextflow run, replay or config resolution may take before the test calls it
# hung. It bounds a hang, not speed: under a loaded host and parallel test workers, one launch
# of a 25.10 engine took over 90 seconds.
NEXTFLOW_TIMEOUT = 300


@pytest.mark.parametrize('separator', ['\u2028', '\u2029', '\u0085', '\v', '\f', '\x1c', '\x1d',
                                       '\x1e', 'Å', '\n', '\r'])
def test_git_identity_uses_lf_records_and_preserves_parent_names(tmp_path, separator):
    repo = tmp_path / ('parent' + separator + 'part') / 'upstream'
    repo.mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    tracked = b'nextflow.enable.dsl=2\n'
    (repo / 'main.nf').write_bytes(tracked)
    subprocess.run(['git', '-C', str(repo), 'add', 'main.nf'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Audit',
                    '-c', 'user.email=audit@example.invalid', 'commit', '-q', '-m', 'fixture'],
                   check=True)
    expected = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                       text=True).strip()
    (repo / 'untracked-data.txt').write_bytes(b'not pipeline source\n')
    assert submodule._own_head(repo) == expected
    assert replay_guard.pipeline_head(repo) == expected
    assert replay_guard.hash_pipeline(repo) == {'main.nf': hashlib.sha256(tracked).hexdigest()}
    # A nested directory must never borrow the enclosing tree's source identity.
    nested = repo / 'nested'
    nested.mkdir()
    assert submodule._own_head(nested) is None
    assert replay_guard.pipeline_head(nested) is None


@pytest.mark.skipif(shutil.which('nextflow') is None, reason='requires a real Nextflow engine')
@pytest.mark.parametrize('engine', ['25.10.4', '26.04.0'])
@pytest.mark.parametrize('separator', ['\u2028', '\u0085', '\v', '\f'])
def test_native_git_revision_and_tracked_source_replay(tmp_path, engine, separator):
    root = tmp_path / ('library' + separator + 'part')
    repo = root / 'pipelines/fixture/upstream'
    repo.mkdir(parents=True)
    (repo.parent / 'skill.md').write_text('---\nname: fixture\n---\n')
    (repo / 'nextflow_schema.json').write_text(json.dumps({'properties': {
        'input': {'type': 'string', 'format': 'file-path', 'exists': True},
        'outdir': {'type': 'string', 'format': 'directory-path'}}}))
    (repo / 'nextflow.config').write_text('nextflow.enable.dsl=2\n')
    (repo / 'main.nf').write_text('''process DIGEST {
 publishDir params.outdir, mode: 'copy'
 input:
 path reads
 output:
 path 'digest.txt'
 script:
 """
 shasum -a 256 ${reads} > digest.txt
 """
}
workflow { DIGEST(file(params.input)) }
''')
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Audit',
                    '-c', 'user.email=audit@example.invalid', 'commit', '-q', '-m', 'fixture'],
                   check=True)
    subprocess.run(['git', '-C', str(repo), 'tag', '1.0.0'], check=True)
    expected = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                       text=True).strip()
    scratch = repo / 'untracked-data.txt'
    scratch.write_text('untracked scratch data\n')
    data = tmp_path / 'reads.fastq'
    payload = b'@R1\nACGT\n+\nIIII\n'
    data.write_bytes(payload)
    outdir = tmp_path / 'result'
    orchestration.run_pipeline('fixture', repo_root=root, input_path=data, outdir=outdir,
        profile='', params_file=None, cli_overrides={}, resume=False, demo=False,
        check_only=False, write_provenance=True, timeout_seconds=90, nxf_ver=engine)
    bundle = outdir / 'provenance'
    manifest = json.loads((bundle / 'run_manifest.json').read_text())
    assert manifest['commit'] == expected
    assert set(provenance.read_checksums(bundle / 'pipeline.sha256')) == {
        'main.nf', 'nextflow.config', 'nextflow_schema.json'}
    digest = hashlib.sha256(payload).hexdigest()
    assert (outdir / 'digest.txt').read_text().split()[0] == digest
    scratch.write_text('changed scratch, still not consumed or tracked\n')
    replay = tmp_path / 'replay'
    completed = subprocess.run(['bash', str(bundle / 'commands.sh'), str(replay)],
        capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (replay / 'digest.txt').read_text().split()[0] == digest
    environment = json.loads((replay / 'provenance' / 'environment_check.json').read_text())
    assert environment['status'] == 'unverified'
    assert any('containerless process evidence' in issue
               for issue in environment['unverified'])
    used = json.loads((replay / 'provenance' / 'pipeline-source.json').read_text())
    assert used == {'from': 'checkout', 'path': str(repo)}          # intact: the same directory
    # A working-tree source mutation cannot reach a replay: it runs the bundle's source archive.
    script = repo / 'main.nf'
    original_source = script.read_text()
    script.write_text(original_source + '\n// changed tracked source\n')
    again = tmp_path / 'again'
    rerun = subprocess.run(['bash', str(bundle / 'commands.sh'), str(again)],
        capture_output=True, text=True, timeout=NEXTFLOW_TIMEOUT)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert (again / 'digest.txt').read_text().split()[0] == digest
    assert (again / 'provenance' / 'pipeline' / 'main.nf').read_text() == original_source
    # An altered archive is refused before Nextflow starts.
    archive = bundle / provenance.PIPELINE_ARCHIVE
    archive.write_bytes(archive.read_bytes()[:-1])
    refused = tmp_path / 'refused'
    changed = subprocess.run(['bash', str(bundle / 'commands.sh'), str(refused)],
        capture_output=True, text=True, timeout=30)
    assert changed.returncode != 0
    assert 'changed' in changed.stdout + changed.stderr
    assert not (refused / '.nextflow').exists()


def test_separator_parent_preserves_pinned_fastqrepair_correction_selection(tmp_path, monkeypatch):
    # This checks source/path identity and compatibility selection, not engine availability.
    # Keep it runnable in the source-complete unit lane, where Nextflow is not installed.
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **_kw: [])
    source = Path(__file__).resolve().parents[1] / 'pipelines/fastqrepair/upstream'
    if submodule._own_head(source) is None:
        pytest.skip('requires the pinned fastqrepair source clone')
    root = tmp_path / 'library\u2028part'
    tree = root / 'pipelines/fastqrepair/upstream'
    tree.parent.mkdir(parents=True)
    subprocess.run(
        ['git', 'clone', '-q', '--shared', '--no-hardlinks', str(source), str(tree)], check=True)
    subprocess.run(
        ['git', '-C', str(tree), 'checkout', '-q', fastqrepair_compat.SUPPORTED_COMMIT], check=True)
    (tree.parent / 'skill.md').write_text('---\nname: fastqrepair\n---\n')
    reads = tmp_path / 'reads.fastq'
    reads.write_bytes(b'@R1\nACGT\n+\nIIII\n')
    sheet = tmp_path / 'samples.csv'
    sheet.write_text(f'sample,fastq_1\nS1,{reads}\n')
    out = tmp_path / 'result'
    result = orchestration.run_pipeline('fastqrepair', repo_root=root, input_path=sheet,
        outdir=out, profile='', params_file=None, cli_overrides={}, resume=False,
        demo=False, check_only=True, write_provenance=True, timeout_seconds=90, nxf_ver='25.10.4')
    try:
        resolved = submodule.resolve_at('fastqrepair', tree)
        assert resolved.commit == fastqrepair_compat.SUPPORTED_COMMIT
        assert any('recorded corrections for fastqrepair' in warning for warning in result.warnings)
        assert 'fastqrepair_compat.config' in result.command
        assert result.env['NXF_SYNTAX_PARSER'] == 'v1'
        assert not out.exists()
    finally:
        if result.staging:
            shutil.rmtree(result.staging)
