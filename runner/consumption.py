"""Compare a handoff boundary with the successor's recorded local data selection."""
from __future__ import annotations

import fnmatch
from pathlib import Path

from runner.inputs import absolute_local_path
from runner.replay_guard import _glob_patterns


def _matches(path: Path, pattern: Path) -> bool:
    """Match path components, including zero or more components for recursive **."""
    parts, patterns = path.parts, pattern.parts

    def match(i, j):
        if j == len(patterns):
            return i == len(parts)
        if patterns[j] == "**":
            return (match(i, j + 1) or i < len(parts) and not parts[i].startswith(".")
                    and match(i + 1, j))
        if i < len(parts) and parts[i].startswith(".") and not patterns[j].startswith("."):
            return False
        return (i < len(parts) and fnmatch.fnmatchcase(parts[i], patterns[j])
                and match(i + 1, j + 1))

    return match(0, 0)


def agrees(evidence: dict, hashes: dict, nodes: dict | None, *, scalar: bool = False) -> bool:
    """Select membership from historical input records, never today's glob matches.

    Scalar parameters resolve their parent before launch; samplesheet cells retain
    their supplied paths. Keep final symlink names and target identities in either case.
    Legacy file-only bundles can establish byte agreement, but not directory identity.
    """
    expected_hashes = evidence["consumed_dependencies"]
    expected_nodes = evidence["consumed_inventory"]
    sources = [Path(value) for value in evidence["consumed_sources"]]
    if scalar:
        mapped_hashes, mapped_nodes = {}, {}
        for source in sources:
            destination = absolute_local_path(source)
            for name, node in expected_nodes.items():
                if Path(name).is_relative_to(source):
                    key = str(destination / Path(name).relative_to(source))
                    node = dict(node)
                    if node.get("resolved_path") == key:
                        node.pop("resolved_path")
                    mapped_nodes[key] = node
            for name, digest in expected_hashes.items():
                if Path(name).is_relative_to(source):
                    mapped_hashes[str(destination / Path(name).relative_to(source))] = digest
        expected_hashes, expected_nodes = mapped_hashes, mapped_nodes
        sources = [absolute_local_path(source) for source in sources]
    patterns = [Path(pattern) for source in sources for pattern in _glob_patterns(str(source))]

    def selected(name):
        path = Path(name)
        return any(_matches(parent, pattern)
                   for pattern in patterns for parent in (path, *path.parents))

    selected_hashes = {name: digest for name, digest in hashes.items() if selected(name)}
    if selected_hashes != expected_hashes:
        return False
    if nodes is None:
        return all(node["type"] == "file" for node in expected_nodes.values())
    return {name: node for name, node in nodes.items() if selected(name)} == expected_nodes
