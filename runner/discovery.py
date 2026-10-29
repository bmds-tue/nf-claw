from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from runner.errors import ErrorCode, NfclawError


@dataclass(frozen=True)
class Pipeline:
    name: str
    path: Path
    upstream: Path
    skill_md: Path
    frontmatter: dict


def _parse_frontmatter(md: Path) -> dict:
    if not md.exists():
        return {}
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict = {}
    for line in text[3:end].splitlines():
        if line and not line.startswith((" ", "\t")) and ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def pipeline_dirs(pipelines_dir: Path) -> list[Path]:
    """The pipeline directories under `pipelines/`, sorted. Hidden entries are not pipelines: a
    Nextflow launched with `pipelines/` as its working directory leaves `.nextflow/` there."""
    if not pipelines_dir.is_dir():
        return []
    return sorted(p for p in pipelines_dir.iterdir() if p.is_dir() and not p.name.startswith("."))


def _pipeline(d: Path) -> Pipeline:
    skill = d / "skill.md"
    return Pipeline(name=d.name, path=d, upstream=d / "upstream", skill_md=skill,
                    frontmatter=_parse_frontmatter(skill))


def discover(pipelines_dir: Path) -> list[Pipeline]:
    return [_pipeline(d) for d in pipeline_dirs(pipelines_dir)]


def find(name: str, pipelines_dir: Path) -> Pipeline:
    """The pipeline called `name` — matched against the directory listing, so a name can never
    reach outside `pipelines/` — with only its own skill.md read."""
    for d in pipeline_dirs(pipelines_dir):
        if d.name == name:
            return _pipeline(d)
    raise NfclawError(ErrorCode.PIPELINE_NOT_FOUND,
                      f"Pipeline '{name}' not found in {pipelines_dir}.",
                      fix="Run `nfclaw list` to see available pipelines.")


def _squash(text: str) -> str:
    """Compared without case, punctuation or spacing: "RNA-seq", "rna seq" and "rnaseq" meet."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def query_words(query: str) -> list[str]:
    """The words of a search, each squashed; words are separated by spaces, commas or
    semicolons."""
    return [w for w in (_squash(w) for w in re.split(r"[\s,;]+", query)) if w]


def search(rows: list[dict], query: str) -> list[dict]:
    """The catalog rows (`catalog.json`) matching `query`, best match first; every row, by name,
    for an empty query. Rows holding more of the words come first, so one word in a name
    ("calling" in callingcards) never outranks a pipeline that matches the whole query. Among rows
    holding as many, each word scores by the most telling field it occurs in — the name, then the
    description and tools, the input, the summary — and naming a pipeline exactly ranks it first.
    A row no word occurs in is not a match. `nfclaw list` and the MCP `list_pipelines` rank
    alike."""
    words = query_words(query)

    def text(value) -> str:
        return _squash(" ".join(value) if isinstance(value, list) else str(value or ""))

    def score(row: dict) -> tuple[int, int]:
        if not words:
            return 1, 1
        name = text(row.get("name"))
        fields = [(name, 10), (text(row.get("description")), 4), (text(row.get("tools")), 4),
                  (text(row.get("input")), 2), (text(row.get("summary")), 1)]
        matched = total = 0
        for word in words:
            best = max((weight for field, weight in fields if word in field), default=0)
            matched += best > 0
            total += best + (30 if word == name else 0)
        return matched, total

    ranked = sorted(((score(row), row) for row in rows),
                    key=lambda pair: (-pair[0][0], -pair[0][1], str(pair[1].get("name", ""))))
    return [row for (matched, _), row in ranked if matched > 0]
