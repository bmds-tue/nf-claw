"""The website reads each generated skill.md itself (website/src/lib/data/markdown.ts). These pin that
parser to what the librarian actually emits, using the committed skill.md files.

They need node and the website's own TypeScript (`npm ci` in website/) and are skipped without them.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "website"
TSC = WEB / "node_modules" / "typescript" / "bin" / "tsc"


@pytest.fixture(scope="module")
def markdown_js(tmp_path_factory):
    if shutil.which("node") is None or not TSC.is_file():
        pytest.skip("needs node and the website dependencies (`npm ci` in website/)")
    out = tmp_path_factory.mktemp("markdown-ts")
    subprocess.run(["node", str(TSC), "--outDir", str(out), "--module", "commonjs",
                    "--target", "es2020", "--skipLibCheck",
                    str(WEB / "src" / "lib" / "data" / "markdown.ts")],
                   check=True, capture_output=True, text=True)
    return out / "markdown.js"


_SCRIPT = """
const fs = require("fs");
const md = require(process.argv[1]);
const out = {};
for (const file of process.argv.slice(2)) {
  const body = md.splitFrontmatter(fs.readFileSync(file, "utf8")).content;
  out[file] = {
    run: (md.codeBlockUnder(body, "Run it") || "").split("\\n").map((l) => l.trim()),
    inputs: md.codeBlocksUnder(body, "Inputs"),
  };
}
process.stdout.write(JSON.stringify(out));
"""


def _parse(markdown_js, files):
    r = subprocess.run(["node", "-e", _SCRIPT, str(markdown_js), *map(str, files)],
                       check=True, capture_output=True, text=True)
    return json.loads(r.stdout)


def test_every_skill_run_block_yields_both_commands(markdown_js):
    # The Run-it block holds `# raw equivalent …` shell comments; read as headings, they ended the
    # section, so the raw `nextflow run` command was never found and the site showed an invented one.
    skills = sorted(ROOT.glob("pipelines/*/skill.md"))
    assert skills
    for file, parsed in _parse(markdown_js, skills).items():
        name = Path(file).parent.name
        assert any(line.startswith(f"nfclaw run {name}") for line in parsed["run"]), file
        assert any(line.startswith(f"nextflow run pipelines/{name}/upstream")
                   for line in parsed["run"]), file


def test_samplesheet_headers_are_read_as_generated(markdown_js):
    parsed = _parse(markdown_js, [ROOT / "pipelines" / "mhcquant" / "skill.md",
                                  ROOT / "pipelines" / "createpanelrefs" / "skill.md"])
    sheets = {Path(f).parent.name: [b for b in p["inputs"] if b["lang"] in ("csv", "tsv")]
              for f, p in parsed.items()}
    # mhcquant takes a TSV: its header is TAB-separated, not comma-joined.
    assert [b["lang"] for b in sheets["mhcquant"]] == ["tsv"]
    assert "\t" in sheets["mhcquant"][0]["code"] and "," not in sheets["mhcquant"][0]["code"]
    # createpanelrefs' column groups exclude each other: one header per group, never all at once.
    assert [b["code"] for b in sheets["createpanelrefs"]] == ["sample,bam", "sample,cram"]
