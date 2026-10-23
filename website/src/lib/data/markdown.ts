// Lightweight, dependency-free parsing helpers for the generated markdown
// files (skill.md / reference.md). These read the exact tables the librarian
// emits, so the website never duplicates or hardcodes their content.

const PIPE_PLACEHOLDER = "__NFCLAW_ESCAPED_PIPE__";

export interface Frontmatter {
  data: Record<string, string | boolean>;
  content: string;
}

/**
 * Split YAML-style frontmatter from a generated markdown document. skill.md and
 * reference.md only ever use a flat block of `key: value` scalars (no nesting,
 * anchors or merge keys), so this small dedicated parser replaces a full YAML
 * dependency — and removes its transitive attack surface from the build.
 */
export function splitFrontmatter(raw: string): Frontmatter {
  const m = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!m) return { data: {}, content: raw };
  const data: Record<string, string | boolean> = {};
  for (const line of m[1].split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf(":");
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    data[key] = value === "true" || value === "false" ? value === "true" : value;
  }
  return { data, content: raw.slice(m[0].length) };
}

/** Split a markdown table row into trimmed cells, respecting escaped pipes. */
export function splitRow(line: string): string[] {
  const normalized = line.replace(/\\\|/g, PIPE_PLACEHOLDER);
  return normalized
    .replace(/^\s*\|/, "")
    .replace(/\|\s*$/, "")
    .split("|")
    .map((c) => c.replace(new RegExp(PIPE_PLACEHOLDER, "g"), "|").trim());
}

export interface MarkdownTable {
  headers: string[];
  rows: string[][];
}

/** Parse the first markdown table found within `lines` starting at `from`. */
export function parseTableAt(lines: string[], from: number): MarkdownTable | null {
  let i = from;
  while (i < lines.length && !lines[i].trim().startsWith("|")) i++;
  if (i >= lines.length) return null;
  const headers = splitRow(lines[i]);
  // separator row
  if (i + 1 >= lines.length || !/^[\s|:-]+$/.test(lines[i + 1])) return null;
  const rows: string[][] = [];
  let j = i + 2;
  while (j < lines.length && lines[j].trim().startsWith("|")) {
    rows.push(splitRow(lines[j]));
    j++;
  }
  return { headers, rows };
}

const FENCE = /^ {0,3}(`{3,}|~{3,})(.*)$/;

/**
 * For each line, the heading text if it is a heading, else null. A line inside a fenced code block is
 * content, never a heading: the "Run it" block's `# raw equivalent …` shell comment otherwise ended the
 * section there, and the raw `nextflow run` command after it was never found.
 */
function headings(lines: string[]): (string | null)[] {
  let fence: string | null = null; // the opening marker of the block we are in, if any
  return lines.map((line) => {
    const f = line.match(FENCE);
    if (fence !== null) {
      // A closing fence: the same character, at least as long as the opener, nothing after it.
      if (f && f[1][0] === fence[0] && f[1].length >= fence.length && !f[2].trim()) fence = null;
      return null;
    }
    if (f) {
      fence = f[1];
      return null;
    }
    const m = line.match(/^#{1,6}\s+(.*)$/);
    return m ? m[1].trim() : null;
  });
}

/** Find a section heading (## Title) and return the lines until the next heading. */
export function sectionLines(md: string, heading: string): string[] {
  const lines = md.split("\n");
  const heads = headings(lines);
  const wanted = heading.trim().toLowerCase();
  const start = heads.findIndex((h) => h !== null && h.toLowerCase().startsWith(wanted));
  if (start === -1) return [];
  const end = heads.findIndex((h, i) => i > start && h !== null);
  return lines.slice(start + 1, end === -1 ? lines.length : end);
}

/** Parse the table under a given "## Heading" section. */
export function tableUnder(md: string, heading: string): MarkdownTable | null {
  const lines = sectionLines(md, heading);
  return parseTableAt(lines, 0);
}

export interface CodeBlockText {
  /** The fence's info string, e.g. "bash", "csv", "tsv" ("" when there is none). */
  lang: string;
  code: string;
}

/** Every fenced code block under a "## Heading" section, in order. */
export function codeBlocksUnder(md: string, heading: string): CodeBlockText[] {
  const blocks: CodeBlockText[] = [];
  let open: { fence: string; lang: string; lines: string[] } | null = null;
  for (const line of sectionLines(md, heading)) {
    const f = line.match(FENCE);
    if (open === null) {
      if (f) open = { fence: f[1], lang: f[2].trim().split(/\s+/)[0] ?? "", lines: [] };
      continue;
    }
    if (f && f[1][0] === open.fence[0] && f[1].length >= open.fence.length && !f[2].trim()) {
      blocks.push({ lang: open.lang, code: open.lines.join("\n") });
      open = null;
      continue;
    }
    open.lines.push(line);
  }
  return blocks;
}

/** The first fenced code block under a "## Heading" section. */
export function codeBlockUnder(md: string, heading: string): string | null {
  const block = codeBlocksUnder(md, heading)[0];
  return block && block.code ? block.code : null;
}

/** The text under a "## Heading", without its code-fence marker lines. */
export function proseUnder(md: string, heading: string): string {
  return sectionLines(md, heading)
    .filter((l) => !l.trim().startsWith("```"))
    .join("\n")
    .trim();
}

/**
 * Split an "allowed values" cell into a clean list. The librarian writes each value as its own code
 * span (`bac,arc`, `vst`) so a value containing a comma stays whole; a plain comma-separated cell
 * (older generated docs) is still read.
 */
export function splitAllowed(cell: string): string[] {
  if (!cell || !cell.trim()) return [];
  const spans = [...cell.matchAll(/`([^`]*)`/g)].map((m) => m[1].trim()).filter(Boolean);
  if (spans.length) return spans;
  return cell
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isYes(cell: string): boolean {
  const v = (cell || "").trim().toLowerCase();
  return v === "yes" || v === "true" || v === "✓" || v === "x";
}

/** Strip surrounding backticks from a cell value. */
export function unticked(cell: string): string {
  return (cell || "").replace(/`/g, "").trim();
}
