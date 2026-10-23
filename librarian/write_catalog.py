"""Generate catalog.md and catalog.json from every pipeline's skill.md frontmatter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from librarian.write_skill import _cell
from runner import discovery


def _json_list(raw: object) -> list[str]:
    """A list-valued frontmatter field (`tools`, `feeds`): a JSON list (names may contain commas,
    e.g. "SHazaM, Change-O"). A comma-separated string — the older form — is still read."""
    text = str(raw or "").strip()
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return [str(t).strip() for t in data if str(t).strip()]
    return [t.strip() for t in text.split(",") if t.strip()]


def generate(*, pipelines_dir: Path, out_md: Path, out_json: Path) -> None:
    rows = [{"name": p.name,
             "version": p.frontmatter.get("version", ""),
             "description": p.frontmatter.get("description", ""),
             "summary": p.frontmatter.get("summary", ""),
             "input": p.frontmatter.get("input", ""),
             "output": p.frontmatter.get("output", ""),
             "tools": _json_list(p.frontmatter.get("tools")),
             # The pipelines it can hand its outputs to in a chain (handoffs/).
             "feeds": _json_list(p.frontmatter.get("feeds"))}
            for p in discovery.discover(pipelines_dir)]
    out_json.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = ["# Pipeline catalog", "",
             f"{len(rows)} nf-core pipelines. Grep this file (or `catalog.json`) for a keyword, "
             "then read `pipelines/<name>/skill.md`. `input` is derived from each pipeline's "
             "samplesheet schema; `output` names output locations and potential reports "
             "(the selected workflow and parameters determine the actual files; per-release detail "
             "is in the pipeline's upstream `docs/output.md`, linked from its skill). `catalog.json` "
             "and each `skill.md` also carry a `summary` (the authors' own one-paragraph description "
             "from the pipeline README, a richer signal for matching a request than the terse "
             "`description` below) and the `tools` it runs (from the pipeline's own `CITATIONS.md`).",
             "",
             "| pipeline | version | input | output | description |",
             "|---|---|---|---|---|"]
    lines += [f"| `{r['name']}` | {r['version']} | {_cell(r['input'])} | {_cell(r['output'])} "
              f"| {_cell(r['description'])} |" for r in rows]
    chains = [r for r in rows if r["feeds"]]
    if chains:
        lines += ["", "## Chains", "",
                  "Pipelines `nfclaw chain run` can run in sequence, the first one's outputs "
                  "prepared as the next one's inputs (rules in `handoffs/`, see "
                  "`docs/chaining.md`):", ""]
        lines += [f"- `{r['name']}` → " + ", ".join(f"`{f}`" for f in r["feeds"]) for r in chains]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="librarian.write_catalog")
    parser.add_argument("--pipelines-dir", default="pipelines")
    args = parser.parse_args(argv)
    generate(pipelines_dir=Path(args.pipelines_dir),
             out_md=Path("catalog.md"), out_json=Path("catalog.json"))
    print("wrote catalog.md and catalog.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
