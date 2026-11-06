import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# iCloud can leave "<name> 2.<ext>" copies in a checkout; a repository file name has no space.
GUIDES = sorted(p for p in (ROOT / "docs").glob("*.md") if " " not in p.name)
HAND_WRITTEN = GUIDES + [ROOT / name for name in (
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
    "docs/audit/README.md", "website/README.md")]
LINK = re.compile(r"(?<!!)\[(?:[^\[\]]|\[[^\]]*\])*\]\(([^)\s]+)\)")


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


def _prose(text):
    """The document without its fenced code blocks, whose links and `#` lines are examples."""
    kept, fence = [], None
    for line in text.splitlines():
        mark = re.match(r"\s*(?:>\s*)?(`{3,}|~{3,})", line)
        if mark and (fence is None or mark.group(1).startswith(fence)):
            fence = mark.group(1) if fence is None else None
        elif fence is None:
            kept.append(line)
    return "\n".join(kept)


def _anchors(text):
    """The fragments GitHub gives a document's headings; the website's slugs follow its rule."""
    found, seen = set(), {}
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", _prose(text), re.M):
        slug = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title.lower())
        slug = re.sub(r"[^\w\s-]", "", slug).strip().replace(" ", "-")
        found.add(f"{slug}-{seen[slug]}" if slug in seen else slug)
        seen[slug] = seen.get(slug, 0) + 1
    return found


def test_relative_links_and_anchors_in_the_guides_resolve():
    broken = []
    for doc in HAND_WRITTEN:
        for target in LINK.findall(_prose(doc.read_text(encoding="utf-8"))):
            if re.match(r"[a-z]+:", target):
                continue
            path, _, anchor = target.partition("#")
            dest = (doc.parent / path).resolve() if path else doc
            if not dest.exists():
                broken.append(f"{doc.relative_to(ROOT)}: {target}")
            elif anchor and dest.suffix == ".md":
                if anchor not in _anchors(dest.read_text(encoding="utf-8")):
                    broken.append(f"{doc.relative_to(ROOT)}: {target}")
    assert not broken


def test_every_guide_is_listed_in_the_readme_and_llms_txt():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for guide in GUIDES:
        assert f"(docs/{guide.name})" in readme, guide.name
        assert f"/docs/{guide.name})" in llms, guide.name


def test_mcp_guide_lists_every_tool():
    from runner.mcp_tools import TOOLS

    guide = (ROOT / "docs" / "mcp.md").read_text(encoding="utf-8")
    assert set(re.findall(r"^\| `([a-z_]+)` \|", guide, re.M)) == {tool["name"] for tool in TOOLS}


def test_architecture_module_map_names_every_runner_module():
    guide = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    mapped = guide[guide.index("### Module map"):guide.index("### 2.1 ")]
    missing = [p.name for p in (ROOT / "runner").glob("*.py")
               if " " not in p.name and p.name != "__init__.py" and f"`{p.name}`" not in mapped]
    assert not missing
