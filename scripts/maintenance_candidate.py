#!/usr/bin/env python3
"""Bind maintenance gates to one generated commit; standard-library only."""
from __future__ import annotations

import argparse
import csv
import configparser
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

SHA = re.compile(r'[0-9a-f]{40}')
TITLES = {'update': 'chore: bump pipelines + regenerate context',
          'discover': 'feat: add discovered nf-core pipelines + generated context'}


def git(*args: str, env: dict | None = None) -> str:
    return subprocess.run(['git', *args], env=env, check=True, text=True,
                          capture_output=True).stdout.strip()


def tree(revision: str) -> dict[str, tuple[str, str]]:
    output = subprocess.run(['git', 'ls-tree', '-rz', revision], check=True,
                            capture_output=True).stdout
    result = {}
    for item in output.split(b'\0'):
        if item:
            descriptor, path = item.decode('utf-8').split('\t', 1)
            mode, _, sha = descriptor.split()
            result[path] = (mode, sha)
    return result


def inventory(base: str, sha: str, kind: str) -> dict[str, str]:
    before, after = tree(base), tree(sha)
    pins = {}
    for path in before.keys() | after.keys():
        if before.get(path) == after.get(path):
            continue
        allowed = path in {'catalog.json', 'catalog.md', '.gitmodules'} or (
            kind == 'discover' and path == 'sources.tsv')
        match = re.fullmatch(r'pipelines/([a-z0-9][a-z0-9_-]*)/(upstream|skill\.md|reference\.md)',
                             path)
        if not allowed and not match:
            raise ValueError(f'Unexpected maintenance path: {path!r}')
        entry = after.get(path)
        if entry is None or entry[0] != ('160000' if match and match[2] == 'upstream'
                                       else '100644'):
            raise ValueError('Unsupported deletion, source conversion or generated file mode')
        if before.get(path) and before[path][0] != entry[0]:
            raise ValueError('Maintenance cannot convert an existing path type')
        if match and match[2] == 'upstream':
            entry = after.get(path)
            if not entry or entry[0] != '160000':
                raise ValueError('A changed pipeline must retain a pinned gitlink')
            pins[match[1]] = entry[1]
    old_policies = registrations(base, before)
    new_policies = registrations(sha, after)
    if any(new_policies.get(name) != policy for name, policy in old_policies.items()):
        raise ValueError('Existing source tracking policies must remain unchanged')
    if any(policy != 'latest-release' for name, policy in new_policies.items()
           if name not in old_policies):
        raise ValueError('Discovered sources must track released versions')
    if any(new_policies[name] != 'latest-release' for name in pins):
        raise ValueError('Maintenance cannot change a manually pinned source')
    return dict(sorted(pins.items()))


def registrations(sha: str, entries: dict) -> dict[str, str]:
    """Only canonical nf-core gitlinks are initialized by candidate validation jobs."""
    expected = {}
    for path, (mode, _) in entries.items():
        if mode == '160000':
            match = re.fullmatch(r'pipelines/([a-z0-9][a-z0-9_-]*)/upstream', path)
            if not match:
                raise ValueError('Unapproved submodule path')
            expected[match[1]] = f'https://github.com/nf-core/{match[1]}.git'
    for path in ('.gitmodules', 'sources.tsv'):
        if entries.get(path, (None,))[0] != '100644':
            raise ValueError('Maintenance requires regular source-registration files')
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.read_string(git('show', f'{sha}:.gitmodules'))
    registered = {}
    if config.defaults():
        raise ValueError('Unsupported submodule defaults')
    for section in config.sections():
        match = re.fullmatch(r'submodule "pipelines/([a-z0-9][a-z0-9_-]*)/upstream"', section)
        if not match or set(config[section]) != {'path', 'url'}:
            raise ValueError('Unapproved submodule registration')
        name = match[1]
        if config[section]['path'] != f'pipelines/{name}/upstream':
            raise ValueError('Submodule registration has another path')
        registered[name] = config[section]['url']
    sources, policies = {}, {}
    for line in git('show', f'{sha}:sources.tsv').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        fields = line.split('\t')
        if (len(fields) != 3 or fields[0] in sources or not fields[2]
                or fields[2].strip() != fields[2]):
            raise ValueError('Unsupported or duplicate source registration')
        sources[fields[0]] = fields[1]
        policies[fields[0]] = fields[2]
    if registered != expected or sources != expected:
        raise ValueError('Gitlinks, source registrations and approved URLs must agree exactly')
    return policies


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'Duplicate JSON key: {key}')
        value[key] = item
    return value


def read_json(path: Path) -> dict:
    if (not stat.S_ISREG(path.lstat().st_mode)
            or path.stat().st_size > 4 * 1024 * 1024):
        raise ValueError(f'Expected regular evidence file: {path}')
    value = json.loads(path.read_text(), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError(f'Expected JSON object: {path}')
    return value


def emit(**values):
    text = ''.join(f'{key}={value}\n' for key, value in values.items())
    print(text, end='')
    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a') as stream:
            stream.write(text)


def prepare(directory: Path, base: str, kind: str) -> None:
    if not SHA.fullmatch(base) or git('rev-parse', 'HEAD') != base or kind not in TITLES:
        raise ValueError('Invalid maintenance base/kind')
    if directory.exists() or directory.is_symlink():
        raise ValueError('Candidate destination already exists')
    # An isolated index preserves staging and excludes unrelated untracked build output.
    with tempfile.TemporaryDirectory(prefix='nfclaw-candidate-') as scratch:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(scratch) / 'index')}
        git('read-tree', base, env=env)
        paths = ['pipelines', 'catalog.json', 'catalog.md', '.gitmodules']
        if kind == 'discover':
            paths.append('sources.tsv')
        excludes = [f':(exclude){path}' for path in paths]
        if subprocess.run(['git', 'diff', '--quiet', base, '--', '.', *excludes]).returncode:
            raise ValueError('Unexpected tracked changes outside generated paths')
        git('add', '--', *paths, env=env)
        candidate_tree = git('write-tree', env=env)
        if candidate_tree == git('rev-parse', f'{base}^{{tree}}'):
            emit(changed='false')
            return
        sha = git('-c', 'user.name=github-actions[bot]', '-c',
                  'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                  'commit-tree', candidate_tree, '-p', base, '-m', TITLES[kind], env=env)
    pins = inventory(base, sha, kind)
    directory.mkdir(mode=0o700)
    reference = f'refs/nfclaw/candidates/{sha}'
    git('update-ref', reference, sha)
    try:
        git('bundle', 'create', str(directory / 'candidate.bundle'), f'{base}..{reference}')
    finally:
        git('update-ref', '-d', reference, sha)
    metadata = {'version': 1, 'base': base, 'sha': sha, 'kind': kind, 'pipelines': pins}
    (directory / 'candidate.json').write_text(json.dumps(metadata, indent=2) + '\n')
    emit(changed='true', base=base, sha=sha, pipelines=json.dumps(list(pins)))


def load(directory: Path, base: str, sha: str, kind: str | None = None) -> dict:
    if not SHA.fullmatch(base) or not SHA.fullmatch(sha):
        raise ValueError('Expected concrete base/candidate commits')
    metadata = read_json(directory / 'candidate.json')
    if (set(metadata) != {'version', 'base', 'sha', 'kind', 'pipelines'}
            or type(metadata['version']) is not int or metadata['version'] != 1
            or metadata['base'] != base or metadata['sha'] != sha
            or metadata['kind'] not in TITLES or (kind is not None and metadata['kind'] != kind)):
        raise ValueError('Candidate metadata differs from the required identity')
    bundle = directory / 'candidate.bundle'
    if not stat.S_ISREG(bundle.lstat().st_mode):
        raise ValueError('Candidate bundle must be a regular file')
    git('fetch', '--no-tags', '--', str(bundle), f'refs/nfclaw/candidates/{sha}')
    if git('rev-parse', 'FETCH_HEAD') != sha or git('show', '-s', '--format=%P', sha) != base:
        raise ValueError('Candidate is not the exact single-parent validated commit')
    if git('show', '-s', '--format=%s', sha) != TITLES[metadata['kind']]:
        raise ValueError('Candidate kind differs from its commit')
    if metadata['pipelines'] != inventory(base, sha, metadata['kind']):
        raise ValueError('Candidate changed-pipeline inventory differs from its tree')
    if tree(base) == tree(sha):
        raise ValueError('Empty candidate commit')
    return metadata


def authorize(metadata: dict, validation: str | None, drift: str | None,
              native: str | None) -> None:
    if validation != 'success' or drift != 'success':
        raise ValueError('The full Python/site/integration matrix and drift must succeed')
    expected_native = 'success' if metadata['pipelines'] else 'skipped'
    if native != expected_native:
        raise ValueError('Every changed pipeline must complete real tasks before publication')


def native_record(metadata: dict, pipeline: str, analysis: Path, output: Path | None) -> dict:
    pin = metadata['pipelines'].get(pipeline)
    if not pin:
        raise ValueError('Native job is not at its required candidate/pipeline')
    manifest_path = analysis / 'provenance/run_manifest.json'
    manifest = read_json(manifest_path)
    stability = manifest.get('dependency_stability')
    if (manifest.get('pipeline') != pipeline or manifest.get('commit') != pin
            or manifest.get('outcome') != 'success'
            or not isinstance(stability, dict) or stability.get('status') != 'unchanged'
            or not re.fullmatch(r'nextflow version \d+\.\d+\.\d+(?: build \d+)?',
                                manifest.get('nextflow', ''))
            or any(manifest.get(key) for key in ('stub_profiles', 'stub_configs',
                                                'completion_caveats'))):
        raise ValueError('Native manifest has failed, changed, stubbed or incomplete evidence')
    traces = list((analysis / 'pipeline_info').glob('execution_trace*.txt'))
    if (len(traces) != 1 or not stat.S_ISREG(traces[0].lstat().st_mode)
            or traces[0].stat().st_size > 32 * 1024 * 1024):
        raise ValueError('Expected exactly one regular native execution trace')
    trace = traces[0]
    with trace.open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        fields = reader.fieldnames or []
        if (len(fields) != len(set(fields))
                or not {'task_id', 'name', 'status', 'exit'} <= set(fields)):
            raise ValueError('Trace lacks unambiguous task completion evidence')
        tasks = []
        seen = set()
        for row in reader:
            if (None in row or any(row.get(key) is None for key in fields)
                    or not row['task_id'] or row['task_id'] in seen or not row['name']
                    or row['status'] != 'COMPLETED' or row['exit'] != '0'):
                raise ValueError('Trace has duplicate, cached, failed, ignored or incomplete tasks')
            seen.add(row['task_id'])
            tasks.append({key: row[key] for key in ('task_id', 'name', 'status', 'exit')})
    if not tasks:
        raise ValueError('No real completed tasks were recorded')
    record = {'version': 1, 'candidate': metadata['sha'], 'base': metadata['base'],
              'pipeline': pipeline, 'pin': pin, 'checked_at': datetime.now(UTC).isoformat(),
              'platform': platform.platform(), 'engine': manifest['nextflow'], 'tasks': tasks,
              'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              'trace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest()}
    if output is not None:
        with output.open('x') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'restore', 'authorize', 'native', 'engine'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--sha')
    parser.add_argument('--kind', choices=list(TITLES))
    parser.add_argument('--validation-result')
    parser.add_argument('--drift-result')
    parser.add_argument('--native-result')
    parser.add_argument('--pipeline')
    parser.add_argument('--native-evidence', type=Path)
    parser.add_argument('--matrix-evidence', type=Path)
    parser.add_argument('--analysis', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            prepare(args.directory, args.base, args.kind)
            return
        metadata = load(args.directory, args.base, args.sha or '', args.kind)
        if args.command == 'restore':
            git('checkout', '--detach', args.sha)
        elif args.command == 'authorize':
            authorize(metadata, args.validation_result, args.drift_result, args.native_result)
            from check_maintenance_pytest import check_report
            lanes = [(os_name, version) for os_name in ('ubuntu-latest', 'macos-latest')
                     for version in ('3.11', '3.12', '3.13', '3.14', '3.15')]
            if args.matrix_evidence is None or not args.matrix_evidence.is_dir():
                raise ValueError('Missing raw full-matrix evidence')
            expected = {f'{os_name}-{version}' for os_name, version in lanes}
            children = list(args.matrix_evidence.iterdir())
            if ({path.name for path in children} != expected
                    or any(path.is_symlink() or not path.is_dir() for path in children)):
                raise ValueError('The raw Python lane inventory is incomplete or unexpected')
            for os_name, version in lanes:
                lane = args.matrix_evidence / f'{os_name}-{version}'
                actual = {'version': 1, 'candidate': args.sha, 'os': os_name, 'python': version,
                          **check_report(lane / 'report.xml', os_name, version)}
                if read_json(lane / 'record.json') != actual:
                    raise ValueError('Raw matrix report differs from its exact-candidate record')
            if metadata['pipelines']:
                if args.native_evidence is None or not args.native_evidence.is_dir():
                    raise ValueError('Missing raw native evidence for changed pipelines')
                children = list(args.native_evidence.iterdir())
                if ({path.name for path in children} != set(metadata['pipelines'])
                        or any(path.is_symlink() or not path.is_dir() for path in children)):
                    raise ValueError('Raw native artifact inventory differs from changed pipelines')
                for pipeline in metadata['pipelines']:
                    location = args.native_evidence / pipeline
                    fresh = native_record(metadata, pipeline, location, None)
                    receipt = read_json(location / 'native.json')
                    for field in ('version', 'candidate', 'base', 'pipeline', 'pin', 'engine',
                                  'tasks', 'manifest_sha256', 'trace_sha256'):
                        if receipt.get(field) != fresh[field]:
                            raise ValueError('Raw native evidence differs from its receipt')
            print(args.sha)
        elif args.command == 'native':
            if not args.pipeline or args.analysis is None or args.output is None:
                raise ValueError('Native evidence requires pipeline, analysis and output')
            if git('rev-parse', 'HEAD') != args.sha:
                raise ValueError('Native evidence requires the exact candidate checkout')
            native_record(metadata, args.pipeline, args.analysis, args.output)
        else:
            if args.pipeline not in metadata['pipelines'] or git('rev-parse', 'HEAD') != args.sha:
                raise ValueError('Engine selection requires the exact changed pipeline candidate')
            config = Path('pipelines') / args.pipeline / 'upstream/nextflow.config'
            match = re.search(r'''nextflowVersion\s*=\s*['"]!?\s*>=\s*(\d+\.\d+\.\d+)['"]''',
                              config.read_text())
            if not match:
                raise ValueError('Unclear engine constraint; manual review required')
            version = match[1]
            if tuple(map(int, version.split('.'))) < (24, 4, 0):
                version = '24.10.5'  # Java 17 and resource-limit support for legacy releases.
            print(version)
    except (OSError, ValueError, subprocess.CalledProcessError, TypeError,
            configparser.Error, ET.ParseError) as exc:
        parser.exit(1, f'Maintenance candidate refused: {exc}\n')


if __name__ == '__main__':
    main()
