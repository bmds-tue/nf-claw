from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_agents_md_matches_claude_md():
    # Two entry points to the same agent guide: CLAUDE.md (Claude Code) and AGENTS.md (other agents).
    # AGENTS.md had silently fallen five sections behind (replay, --limit-*, `nfclaw verify`, remote
    # reference defaults, warnings that are not faults), so agents reading it never learned them.
    assert (ROOT / "AGENTS.md").read_text(encoding="utf-8") == \
        (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def test_llms_txt_exists_and_matches_website_public():
    llms_root = ROOT / "llms.txt"
    llms_public = ROOT / "website" / "public" / "llms.txt"
    assert llms_root.is_file(), "llms.txt must exist at repo root"
    assert llms_public.is_file(), "llms.txt must exist in website/public for GitHub Pages deployment"
    assert llms_root.read_text(encoding="utf-8") == llms_public.read_text(encoding="utf-8"), \
        "website/public/llms.txt must be identical to root llms.txt"


def test_llms_txt_conforms_to_spec():
    text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    lines = text.splitlines()

    # 1. H1 with project name
    assert lines[0] == "# nf-claw"

    # 2. Blockquote summary
    assert any(line.startswith("> ") for line in lines[:5])

    # 3. Preamble before first H2 must not contain headings (llmstxt.org v2 requirement)
    first_h2_idx = next(i for i, line in enumerate(lines) if line.startswith("## "))
    for line in lines[1:first_h2_idx]:
        assert not line.startswith("#"), f"Preamble must not contain headings: {line}"

    # 4. Required H2 sections
    sections = [line for line in lines if line.startswith("## ")]
    assert "## Agent Guidance" in sections
    assert "## Essential Documentation" in sections
    assert "## Pipeline Catalogs & Library" in sections
    assert "## Optional" in sections

    # 5. Core files and AGENTS.md referenced
    assert "AGENTS.md" in text
    assert "README.md" in text

    # 6. File list links use absolute HTTPS URLs per llms.txt best practices
    for line in lines[first_h2_idx:]:
        if line.startswith("- ["):
            assert "](https://" in line, f"Link must be an absolute HTTPS URL: {line}"
