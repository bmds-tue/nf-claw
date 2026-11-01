"""Versioned source namespace snapshots; also copied beside the standalone replay guard.

Only the root .git administration entry is excluded. Files outside Git's index are source
dependencies too. Internal relative symlinks and hard links retain their topology. Escaping
links, outside hard-link aliases and special objects are refused rather than dereferenced.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import re
import stat
import tarfile
from contextlib import contextmanager
from pathlib import Path

VERSION = 2
RECORD = 'pipeline-source-identity.json'
POLICY = 'posix-namespace-private-archive-root-v1'


def _mode(value):
    return type(value) is int and 0 <= value <= 0o7777


def _name(value):
    if (not isinstance(value, str) or not value or '\x00' in value
            or any(part in ('', '.', '..') for part in value.split('/'))
            or value.split('/')[0] == '.git'):
        raise ValueError('invalid pipeline source entry path')
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('pipeline source entry paths must be UTF-8') from exc


def inventory(record):
    """Validate portable metadata before using any of its paths or archive link targets."""
    if (not isinstance(record, dict) or type(record.get('version')) is not int
            or record['version'] != VERSION or record.get('mode_policy') != POLICY
            or not _mode(record.get('root_mode')) or not isinstance(record.get('entries'), dict)
            or record.keys() != {'version', 'mode_policy', 'root_mode', 'entries'}):
        raise ValueError('invalid pipeline source identity version or mode policy')
    entries = record['entries']
    for name, item in entries.items():
        _name(name)
        if not isinstance(item, dict) or not _mode(item.get('mode')):
            raise ValueError(f'invalid pipeline source mode: {name}')
        kind = item.get('type')
        fields = {'type', 'mode'}
        if kind == 'file':
            if item['mode'] & 0o6000:
                raise ValueError('privileged executable permission bits in pipeline source: '
                                 f'{name}')
            fields.add('sha256')
            if not isinstance(item.get('sha256'), str) or not re.fullmatch(
                    r'[a-f0-9]{64}', item['sha256']):
                raise ValueError(f'invalid pipeline source checksum: {name}')
            if 'hardlink_to' in item:
                fields.add('hardlink_to')
                target = entries.get(item['hardlink_to']) if isinstance(
                    item['hardlink_to'], str) else None
                if (not isinstance(target, dict) or target.get('type') != 'file'
                        or 'hardlink_to' in target or item['hardlink_to'] >= name
                        or (target.get('mode'), target.get('sha256')) !=
                        (item['mode'], item['sha256'])):
                    raise ValueError(f'invalid pipeline source hard link: {name}')
        elif kind == 'symlink':
            fields.add('target')
            target = item.get('target')
            if (not isinstance(target, str) or not target or '\x00' in target
                    or target.startswith('/')):
                raise ValueError(f'pipeline source symlink is not relative: {name}')
        elif kind != 'directory':
            raise ValueError(f'unsupported pipeline source entry type: {name}')
        if item.keys() != fields:
            raise ValueError(f'invalid pipeline source entry fields: {name}')
        for parent in Path(name).parents:
            if parent.as_posix() != '.':
                ancestor = entries.get(parent.as_posix())
                if not isinstance(ancestor, dict) or ancestor.get('type') != 'directory':
                    raise ValueError(f'pipeline source entry has a non-directory ancestor: {name}')
    # Resolve using the recorded namespace, never the host's mutable filesystem.
    for name, item in entries.items():
        if item['type'] != 'symlink':
            continue
        pending = [*Path(name).parent.parts, *item['target'].split('/')]
        resolved, hops = [], 0
        while pending:
            part, pending = pending[0], pending[1:]
            if part in ('', '.'):
                continue
            if part == '..':
                if not resolved:
                    raise ValueError(f'pipeline source symlink escapes its tree: {name}')
                resolved.pop()
                continue
            key = '/'.join([*resolved, part])
            if key.split('/')[0] == '.git':
                raise ValueError(f'pipeline source symlink enters excluded Git metadata: {name}')
            node = entries.get(key, {})
            if node.get('type') == 'symlink':
                hops += 1
                if hops > 40:
                    raise ValueError(f'pipeline source symlink cycle or excessive chain: {name}')
                pending = [*node['target'].split('/'), *pending]
            else:
                resolved.append(part)
    return entries


def files(record):
    return {name: item['sha256'] for name, item in inventory(record).items()
            if item['type'] == 'file'}


@contextmanager
def _directory(path):
    canonical = path.resolve(strict=True)
    fd = os.open(canonical.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in canonical.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
        if path.resolve(strict=True) != canonical or not os.path.samestat(
                os.fstat(fd), canonical.stat()):
            raise ValueError('pipeline source directory changed during inspection')
    finally:
        os.close(fd)


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def snapshot(path):
    """Capture bytes, permissions, directories and links without following namespace aliases."""
    path = Path(path)
    entries, hardlinks = {}, {}

    def walk(fd, relative):
        before = os.fstat(fd)
        names = sorted(n for n in os.listdir(fd) if relative or n != '.git')
        for name in names:
            key = f'{relative}/{name}' if relative else name
            _name(key)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            mode = stat.S_IMODE(info.st_mode)
            if not _mode(mode):
                raise ValueError(f'unsupported special permission bits in pipeline source: {key}')
            if stat.S_ISDIR(info.st_mode):
                entries[key] = {'type': 'directory', 'mode': mode}
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    if not os.path.samestat(info, os.fstat(child)):
                        raise ValueError(f'pipeline source directory changed: {key}')
                    walk(child, key)
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                if mode & 0o6000:
                    raise ValueError(f'privileged executable permission bits in source: {key}')
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    opened = os.fstat(child)
                    if _stamp(opened) != _stamp(info):
                        raise ValueError(f'pipeline source file changed before reading: {key}')
                    digest = hashlib.sha256()
                    while block := os.read(child, 1024 * 1024):
                        digest.update(block)
                    if _stamp(opened) != _stamp(os.fstat(child)):
                        raise ValueError(f'pipeline source file changed during reading: {key}')
                    entries[key] = {'type': 'file', 'mode': mode, 'sha256': digest.hexdigest()}
                    aliases = hardlinks.setdefault((info.st_dev, info.st_ino), [])
                    aliases.append((key, info.st_nlink))
                finally:
                    os.close(child)
            elif stat.S_ISLNK(info.st_mode):
                entries[key] = {'type': 'symlink', 'mode': mode,
                                'target': os.readlink(name, dir_fd=fd)}
            else:
                raise ValueError(f'unsupported special object in pipeline source: {key}')
            if _stamp(info) != _stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)):
                raise ValueError(f'pipeline source entry changed during inspection: {key}')
        after = os.fstat(fd)
        if (names != sorted(n for n in os.listdir(fd) if relative or n != '.git')
                or _stamp(before) != _stamp(after)):
            raise ValueError('pipeline source directory changed during inspection: '
                             f'{relative or "."}')

    with _directory(path) as root:
        root_mode = stat.S_IMODE(os.fstat(root).st_mode)
        walk(root, '')
    for names in hardlinks.values():
        if any(count != len(names) for _, count in names):
            raise ValueError('pipeline source has a hard-link alias outside its tree: '
                             f'{names[0][0]}')
        first = min(name for name, _ in names)
        for name, _ in names:
            if name != first:
                entries[name]['hardlink_to'] = first
    record = {'version': VERSION, 'mode_policy': POLICY, 'root_mode': root_mode,
              'entries': dict(sorted(entries.items()))}
    inventory(record)
    return record


def check(path, record, *, private_root=False):
    inventory(record)
    current = snapshot(Path(path))
    expected = {**record, 'root_mode': 0o700} if private_root else record
    if current != expected:
        changed = sorted(name for name in current['entries'].keys() | record['entries'].keys()
                         if current['entries'].get(name) != record['entries'].get(name))
        raise ValueError('pipeline source namespace, permissions or content changed: '
                         + ', '.join(changed[:5] or ['root directory permissions']))


@contextmanager
def _file(root, name):
    """Hold every ancestor while opening a recorded regular file; links cannot redirect reads."""
    parent = os.dup(root)
    child = None
    try:
        for part in Path(name).parts[:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = fd
        child = os.open(Path(name).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(child, 'rb') as stream:
            child = None
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError(f'pipeline source entry is no longer a regular file: {name}')
            yield stream
    finally:
        if child is not None:
            os.close(child)
        os.close(parent)


class _HashReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        block = self.stream.read(size)
        self.digest.update(block)
        return block


def write_archive(path, record, destination):
    """Deterministic source archive, retaining permissions, links and source read restrictions."""
    entries = inventory(record)
    check(path, record)
    mode = 0o666
    modes = [(record['root_mode'], True), *((item['mode'], item['type'] == 'directory')
             for item in entries.values() if item['type'] != 'symlink')]
    for read, execute, access in ((0o040, 0o010, 0o060), (0o004, 0o001, 0o006)):
        if any(not permissions & read or directory and not permissions & execute
               for permissions, directory in modes):
            mode &= ~access
    while True:
        temporary = destination.with_name(f'.pipeline-source-{os.urandom(8).hex()}.tmp')
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            break
        except FileExistsError:
            continue
    try:
        with os.fdopen(fd, 'wb') as raw, _directory(Path(path)) as root:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tar:
                    order = {'directory': 0, 'file': 1, 'hardlink': 2, 'symlink': 3}
                    def priority(name):
                        item = entries[name]
                        return order['hardlink' if 'hardlink_to' in item else item['type']], name
                    names = sorted(entries, key=priority)
                    for name in names:
                        item = entries[name]
                        info = tarfile.TarInfo(name)
                        info.mode, info.mtime = item['mode'], 0
                        if item['type'] == 'directory':
                            info.type = tarfile.DIRTYPE
                        elif item['type'] == 'symlink':
                            info.type, info.linkname = tarfile.SYMTYPE, item['target']
                        elif 'hardlink_to' in item:
                            info.type, info.linkname = tarfile.LNKTYPE, item['hardlink_to']
                        else:
                            with _file(root, name) as stream:
                                before = os.fstat(stream.fileno())
                                info.size = before.st_size
                                reader = _HashReader(stream)
                                tar.addfile(info, reader)
                                if (reader.digest.hexdigest() != item['sha256']
                                        or _stamp(before) != _stamp(os.fstat(stream.fileno()))):
                                    raise ValueError('pipeline source changed while archiving: '
                                                     f'{name}')
                            continue
                        tar.addfile(info)
        check(path, record)
        digest = hashlib.sha256()
        with temporary.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        os.replace(temporary, destination)
        return digest.hexdigest()
    finally:
        temporary.unlink(missing_ok=True)


def _check_archive(archive, record, destination=None):
    """Check every entry before execution; extract only into a new private directory."""
    entries = inventory(record)
    if destination is not None:
        destination.mkdir(parents=True, mode=0o700)
        for name, item in sorted(entries.items(), key=lambda pair: (pair[0].count('/'), pair[0])):
            if item['type'] == 'directory':
                (destination / name).mkdir(mode=0o700)
    seen = set()
    with tarfile.open(archive, mode='r:gz') as tar:
        for member in tar:
            name = member.name
            item = entries.get(name)
            if item is None or name in seen or member.mode != item['mode']:
                raise ValueError(f'unexpected pipeline source archive entry or mode: {name!r}')
            target = destination / name if destination is not None else None
            if item['type'] == 'directory':
                valid = member.isdir()
            elif item['type'] == 'symlink':
                valid = member.issym() and member.linkname == item['target']
                if valid and target is not None:
                    target.symlink_to(item['target'])
                    if stat.S_IMODE(target.lstat().st_mode) != item['mode']:
                        if not hasattr(os, 'lchmod'):
                            raise ValueError('this host cannot restore recorded symlink mode: '
                                             f'{name}')
                        os.lchmod(target, item['mode'])
            elif 'hardlink_to' in item:
                valid = (member.islnk() and member.linkname == item['hardlink_to']
                         and item['hardlink_to'] in seen)
                if valid and target is not None:
                    os.link(destination / item['hardlink_to'], target, follow_symlinks=False)
            else:
                valid = member.isreg()
                if valid:
                    digest = hashlib.sha256()
                    stream = tar.extractfile(member)
                    output = target.open('xb') if target is not None else None
                    try:
                        while block := stream.read(1024 * 1024):
                            digest.update(block)
                            if output is not None:
                                output.write(block)
                        if output is not None:
                            os.fchmod(output.fileno(), item['mode'])
                    finally:
                        stream.close()
                        if output is not None:
                            output.close()
                    valid = digest.hexdigest() == item['sha256']
            if not valid:
                raise ValueError(f'pipeline source archive differs from its identity: {name}')
            seen.add(name)
    if seen != entries.keys():
        raise ValueError('pipeline source archive inventory is incomplete')
    if destination is not None:
        for name, item in sorted(entries.items(), reverse=True):
            if item['type'] == 'directory':
                os.chmod(destination / name, item['mode'])
        check(destination, record, private_root=True)


def check_archive(archive, record, destination=None):
    try:
        _check_archive(archive, record, destination)
    except (tarfile.TarError, EOFError) as exc:
        raise ValueError(f'pipeline source archive is unreadable: {exc}') from exc
