from __future__ import annotations

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
