"""Exact-source workflow corrections, copied and recorded independently of upstream trees."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from runner import budget, replay_guard, submodule
from runner.errors import ErrorCode, NfclawError
from runner.probes import capture
from runner.submodule import SubmoduleStatus

try:
    import fcntl
except ImportError:
    fcntl = None


@dataclass(frozen=True)
class Recipe:
    pipeline: str
    commit: str
    identifier: str
    path: str
    original_sha256: str
    edits: tuple[tuple[bytes, bytes], ...]

    def identity(self) -> dict:
        content = {'version': 1, 'pipeline': self.pipeline, 'upstream_commit': self.commit,
                   'recipe': self.identifier, 'path': self.path,
                   'original_sha256': self.original_sha256,
                   'edits': [[old.decode(), new.decode()] for old, new in self.edits]}
        fingerprint = hashlib.sha256(json.dumps(content, sort_keys=True,
                                                 separators=(',', ':')).encode()).hexdigest()
        return {'version': 1, 'pipeline': self.pipeline, 'upstream_commit': self.commit,
                'recipe': self.identifier, 'fingerprint': fingerprint}


_RECIPES = (
    Recipe('createtaxdb', 'b01a0f8ed96a5990d15470828dfa92a22cf08bba',
           'createtaxdb-sourmash-copy-sort-v1', 'subworkflows/local/sourmash_create/main.nf',
           'd4bba56bd872f0d99dbe96998f781338458cdca6b02cf2ed61fbef6e1c168cc5',
           ((b'.sort()', b'.sort(false)'),)),
    Recipe('funcscan', 'aee3dc965eb0c77267435544dda30da858763913',
           'funcscan-hmm-metadata-v1', 'subworkflows/local/amp.nf',
           'da0910b19617ffe05551968930acf181ede17e8af21b4b52d0548d66342738cf',
           ((b"def meta_new = [:]\r\n                meta_new['id'] = meta_faa['id']\r\n"
             b"                meta_new['hmm_id'] = meta_hmm['id']",
             b'def meta_new = meta_faa + [hmm_id: meta_hmm.id]'),
            (b'[[id: meta.id], file]',
             b"[meta.findAll { key, value -> key != 'hmm_id' }, file]"))),
)


def _error(message: str) -> NfclawError:
    return NfclawError(ErrorCode.ENVIRONMENT, message,
                      fix='Preserve the changed source or cache for inspection; use an unchanged '
                          'release and a fresh valid source-cache location.')


def recipe_identity(name: str, commit: str) -> dict | None:
    """A static recipe fingerprint for chain definitions; no filesystem writes or network."""
    recipe = next((entry for entry in _RECIPES
                   if (entry.pipeline, entry.commit) == (name, commit)), None)
    return recipe.identity() if recipe else None


@dataclass(frozen=True)
class SourcePlan:
    source: Path
    recipe_id: str
    upstream_commit: str
    fingerprint: str
    identity: dict
    original_files: dict[str, str]
    expected_files: dict[str, str]
    expected_modes: dict[str, int]
    patched_files: dict[str, bytes]


@dataclass(frozen=True)
class WorkingSource:
    path: Path
    metadata: dict
    git_head: None = None


def _source_modes(source: Path, files: dict) -> dict[str, int]:
    modes = {}
    for relative in files:
        info = (source / relative).lstat()
        if not stat.S_ISREG(info.st_mode):
            raise _error(f'Corrected source requires regular tracked files: {source / relative}')
        # Match Git's executable/nonexecutable file convention, independently of checkout umask.
        modes[relative] = 0o755 if info.st_mode & 0o111 else 0o644
    return modes


def _check_untracked(source: Path) -> None:
    if replay_guard.pipeline_head(source) is None:
        return
    result = capture(['git', '-C', str(source), 'ls-files', '--others', '--directory', '-z'],
                     timeout=30, env=submodule._git_env())
    result.check_returncode()
    if result.stdout:
        raise _error('Corrected source cannot silently omit untracked or ignored files: '
                     f'{source}. Preserve them outside this release checkout first.')


def plan(st: SubmoduleStatus) -> SourcePlan | None:
    """Plan bounded edits after the caller validates the original selected release identity."""
    recipe = next((entry for entry in _RECIPES
                   if (entry.pipeline, entry.commit) == (st.name, st.commit)), None)
    if recipe is None:
        return None
    try:
        _check_untracked(st.path)
        original = replay_guard.hash_pipeline(st.path)
        if original.get(recipe.path) != recipe.original_sha256:
            raise _error(f'The source checksum does not match correction {recipe.identifier}: '
                         f'{st.path / recipe.path}')
        content = (st.path / recipe.path).read_bytes()
        if hashlib.sha256(content).hexdigest() != recipe.original_sha256:
            raise _error(f'The source changed while reading correction {recipe.identifier}.')
        for old, new in recipe.edits:
            if content.count(old) != 1:
                raise _error(f'The source edit is ambiguous for correction {recipe.identifier}.')
            content = content.replace(old, new)
        expected = {**original, recipe.path: hashlib.sha256(content).hexdigest()}
        identity = recipe.identity()
        return SourcePlan(st.path.resolve(), recipe.identifier, st.commit,
                          identity['fingerprint'], identity, original, expected,
                          _source_modes(st.path, original), {recipe.path: content})
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise _error(f'Cannot plan the corrected source: {exc}') from exc


def _record(plan: SourcePlan, path: Path) -> dict:
    return {**plan.identity, 'kind': 'corrected_working_copy', 'origin_path': str(plan.source),
            'path': str(path), 'files': dict(plan.expected_files),
            'modes': dict(plan.expected_modes), 'mode_policy': 'regular-files-644-755-v1',
            'changes': [{'path': relative, 'before': plan.original_files[relative],
                         'after': plan.expected_files[relative]}
                        for relative in sorted(plan.patched_files)]}


RECORD_FILE = 'working-source.json'


def cache_destination(plan: SourcePlan) -> Path:
    """An overrideable user cache keeps source correction independent of checkout writability."""
    base = os.environ.get('NFCLAW_SOURCE_CACHE')
    if not base:
        base = str(Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') /
                   'nfclaw/working-sources')
    return (Path(base).expanduser().resolve() / plan.identity['pipeline'] /
            plan.upstream_commit / plan.fingerprint)


def resume_source(outdir: Path, planned: SourcePlan | None) -> WorkingSource | None:
    """Never continue a corrected cache without the exact earlier recipe and working source."""
    record_path = outdir / 'provenance' / RECORD_FILE
    if planned is None and not os.path.lexists(record_path):
        return None
    try:
        if record_path.is_symlink() or not record_path.is_file():
            raise ValueError('the earlier correction record is missing or is a symlink')
        record = json.loads(record_path.read_text())
        if planned is None:
            raise ValueError('the earlier correction recipe no longer applies')
        path = Path(record['path'])
        if not path.is_absolute() or record != _record(planned, path):
            raise ValueError('the earlier correction recipe or source inventory differs')
        working = WorkingSource(path, record)
        verify(working)
        return working
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _error(f'Cannot resume the recorded source correction: {exc}') from exc


def write_record(working: WorkingSource, staging: Path) -> Path:
    """Minimum resume identity, retained even when the caller opts out of a final bundle."""
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / RECORD_FILE
    data = (json.dumps(working.metadata, sort_keys=True, indent=2) + '\n').encode()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != data:
            raise _error(f'The recorded source correction changed: {path}') from None
    else:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
    return path


def verify(working: WorkingSource) -> None:
    """Validate every actual byte, file identity and recorded file mode without the origin."""
    try:
        replay_guard.check_corrected_source(working.path, working.metadata)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _error(f'Cannot verify corrected source {working.path}: {exc}') from exc


def _original_unchanged(plan: SourcePlan) -> None:
    _check_untracked(plan.source)
    if (replay_guard.hash_pipeline(plan.source) != plan.original_files or
            _source_modes(plan.source, plan.original_files) != plan.expected_modes):
        raise _error(f'The original source changed after correction planning: {plan.source}')


@contextmanager
def _writer(destination: Path, parent_fd: int):
    if fcntl is None:
        raise _error('Corrected source publication requires POSIX file locking.')
    lock = f'.{destination.name}.nfclaw-source.lock'
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink != 1:
            raise _error('Corrected source lock must be an independent regular file.')
        while True:
            budget.check()
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def _publish(plan: SourcePlan, destination: Path, parent_fd: int) -> None:
    """Build through held directories; failures remove only entries created by this attempt."""
    os.mkdir(destination.name, 0o700, dir_fd=parent_fd)
    identity = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
    directories = {}
    written = []
    created = []
    try:
        directories['.'] = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                   dir_fd=parent_fd)
        if not os.path.samestat(identity, os.fstat(directories['.'])):
            raise _error('Corrected source directory changed during creation.')
        for relative, digest in sorted(plan.original_files.items()):
            budget.check()
            parts = Path(relative).parts
            parent = '.'
            for part in parts[:-1]:
                child = part if parent == '.' else f'{parent}/{part}'
                if child not in directories:
                    os.mkdir(part, mode=0o700, dir_fd=directories[parent])
                    child_info = os.stat(part, dir_fd=directories[parent], follow_symlinks=False)
                    created.append((directories[parent], part, child_info))
                    directories[child] = os.open(
                        part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directories[parent])
                    if not os.path.samestat(child_info, os.fstat(directories[child])):
                        raise _error('Corrected source directory changed during creation.')
                parent = child
            content = (plan.source / relative).read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise _error(f'The original source changed while copying: {relative}')
            fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directories[parent])
            written.append((directories[parent], parts[-1], os.fstat(fd)))
            with os.fdopen(fd, 'wb') as stream:
                stream.write(plan.patched_files.get(relative, content))
                os.fchmod(stream.fileno(), plan.expected_modes[relative])
        _original_unchanged(plan)
        verify(WorkingSource(destination, _record(plan, destination)))
        if not os.path.samestat(identity, os.stat(destination.name, dir_fd=parent_fd,
                                                 follow_symlinks=False)):
            raise _error(f'The corrected source directory changed during publication: '
                         f'{destination}')
    except BaseException:
        for fd, name, entry in reversed(written):
            try:
                if os.path.samestat(entry, os.stat(name, dir_fd=fd, follow_symlinks=False)):
                    os.unlink(name, dir_fd=fd)
            except FileNotFoundError:
                pass
        for directory_fd, name, entry in reversed(created):
            try:
                if os.path.samestat(entry, os.stat(
                        name, dir_fd=directory_fd, follow_symlinks=False)):
                    os.rmdir(name, dir_fd=directory_fd)
            except OSError:
                pass
        try:
            if os.path.samestat(identity, os.stat(destination.name, dir_fd=parent_fd,
                                                 follow_symlinks=False)):
                os.rmdir(destination.name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        for fd in reversed(list(directories.values())):
            os.close(fd)


def materialize(plan: SourcePlan, destination: Path) -> WorkingSource:
    """Publish or verify a private derived copy; never edit or overwrite an existing source."""
    destination = Path(destination).expanduser().absolute()
    try:
        if destination.is_symlink():
            raise _error(f'The corrected source destination is a symlink: {destination}')
        destination = destination.parent.resolve() / destination.name
        if (destination.is_relative_to(plan.source) or plan.source.is_relative_to(destination)):
            raise _error('Corrected source publication cannot write into or contain '
                         'original source.')
        working = WorkingSource(destination, _record(plan, destination))
        with replay_guard.open_source_directory(destination.parent, create=True) as parent_fd:
            _original_unchanged(plan)
            with _writer(destination, parent_fd):
                with replay_guard.open_source_directory(destination.parent) as named:
                    if not os.path.samestat(os.fstat(named), os.fstat(parent_fd)):
                        raise _error('Corrected source cache parent changed before publication.')
                if os.path.lexists(destination):
                    verify(working)
                else:
                    _publish(plan, destination, parent_fd)
                return working
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise _error(f'Cannot materialize corrected source {destination}: {exc}') from exc
