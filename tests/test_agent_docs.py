from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_claude_md_imports_agents_md():
    # One agent guide, two entry points: Claude Code reads CLAUDE.md, other agents AGENTS.md. A
    # second copy had silently fallen five sections behind (replay, --limit-*, `nfclaw verify`,
    # remote reference defaults, warnings that are not faults), so CLAUDE.md imports the guide
    # instead of repeating it.
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@AGENTS.md" in text.splitlines()
    assert len(text) < 500


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
