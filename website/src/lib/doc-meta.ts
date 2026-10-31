// Presentation helpers for repository documents: a clean plain-text preview, reading time, and the
// document's headings (for the on-page table of contents). Pure, so server and client share them.

/** Plain-text lead of a Markdown (or plain-text) document, cut at a word boundary. */
export function docPreview(md: string, max = 170): string {
  let text = md
    .replace(/^---\r?\n[\s\S]*?\r?\n---\s*/, "") // frontmatter
    .replace(/<!--[\s\S]*?-->/g, " ") // comments
    .replace(/```[\s\S]*?```/g, " ") // fenced code
    // real HTML only — a placeholder like `<name>` or `<outdir>` is content
    .replace(/<\/?(?:p|div|span|img|a|br|hr|sup|sub|b|i|em|strong|picture|source|details|summary|table|thead|tbody|tr|td|th|h[1-6]|ul|ol|li|center)\b[^>]*>/gi, " ")
    .replace(/^#{1,6}\s+.*$/gm, " ") // headings, the title included
    .replace(/^\s*[=_-]{3,}\s*$/gm, " ") // rules and plain-text dividers
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ") // images
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1") // links
    .replace(/`([^`]*)`/g, "$1") // inline code
    .replace(/\*\*|__/g, "")
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/gm, "") // list markers
    .replace(/^\s*>\s?/gm, "") // quotes
    .replace(/\|/g, " ");

  // A plain-text file opens with a short banner line ("nf-claw — NOTICE"): not part of the lead.
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  if (lines.length > 1 && lines[0].length < 40 && !/[.!?:]$/.test(lines[0])) lines.shift();
  text = lines.join(" ").replace(/\s+/g, " ").trim();

  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  return cut.slice(0, Math.max(cut.lastIndexOf(" "), max - 20)).replace(/[\s,;:—–-]+$/, "") + "…";
}

export function readingMinutes(md: string): number {
  return Math.max(1, Math.round(md.split(/\s+/).filter(Boolean).length / 220));
}

/** URL fragment for a heading — GitHub-style, so links written against GitHub keep working. */
export function slugify(text: string): string {
  let plain = text.toLowerCase();
  // Until stable: removing one tag must not leave another assembled from its neighbours.
  for (let previous = ""; previous !== plain; ) {
    previous = plain;
    plain = plain.replace(/<[^>]+>/g, "");
  }
  return plain
    .replace(/[`*~[\]()]/g, "")
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .trim()
    .replace(/\s/g, "-");
}

export interface DocHeading {
  depth: 2 | 3;
  text: string;
  id: string;
  /** 1-based source line, so a renderer can look the id up by its node's position. */
  line: number;
}

/** The ## and ### headings of a Markdown document, outside code fences, with unique ids. */
export function docHeadings(md: string): DocHeading[] {
  const out: DocHeading[] = [];
  const seen = new Map<string, number>();
  let fence: string | null = null;
  const lines = md.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const f = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (f) {
      if (fence === null) fence = f[1];
      else if (f[1][0] === fence[0] && f[1].length >= fence.length) fence = null;
      continue;
    }
    if (fence !== null) continue;
    const m = line.match(/^(#{2,3})\s+(.+?)\s*#*\s*$/);
    if (!m) continue;
    // Keep code spans intact while removing emphasis from the surrounding heading.
    const code: string[] = [];
    const text = m[2]
      .replace(/(`+)(.*?)\1/g, (_match, _ticks, value: string) => {
        code.push(value);
        return String.fromCharCode(0) + (code.length - 1) + String.fromCharCode(0);
      })
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/(?<![\p{L}\p{N}_])__(\S(?:.*?\S)?)__(?![\p{L}\p{N}_])/gu, "$1")
      .replace(/\*([^*\s][^*]*)\*/g, "$1") // *emphasis*
      .replace(/(^|\s)_([^_\s][^_]*)_(?=\s|$)/g, "$1$2") // _emphasis_ (not snake_case)
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/\u0000(\d+)\u0000/g, (_match, index: string) => code[Number(index)]);
    out.push({ depth: m[1].length as 2 | 3, text, id: uniqueId(slugify(text), seen), line: i + 1 });
  }
  return out;
}

function uniqueId(base: string, seen: Map<string, number>): string {
  const n = seen.get(base) ?? 0;
  seen.set(base, n + 1);
  return n === 0 ? base : `${base}-${n}`;
}
