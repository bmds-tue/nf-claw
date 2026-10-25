import { docHeadings } from "./doc-meta";

export interface DocSearchSection {
  id: string;
  title: string;
  heading: string;
  href: string;
  body: string;
}
export interface DocSearchIndex { version: 1; sections: DocSearchSection[] }

function plain(markdown: string): string {
  return markdown
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, " ")
    .replace(/^\s*(?:`{3,}|~{3,}).*$/gm, " ") // retain code/error text inside fences
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/<\/?(?:p|div|span|img|a|br|hr|sup|sub|b|i|em|strong|picture|source|details|summary|table|thead|tbody|tr|td|th|h[1-6]|ul|ol|li|center)\b[^>]*>/gi, " ")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/[`*]/g, "")
    .replace(/\s+/g, " ").trim();
}

/** Build from the same heading IDs the documentation renderer uses. */
export function buildDocSearch(docs: { slug: string; title: string; content: string }[]): DocSearchIndex {
  const sections = docs.flatMap((doc) => {
    const lines = doc.content.split("\n");
    const headings = [{ line: 1, text: "", id: "" }, ...docHeadings(doc.content)];
    return headings.map((heading, index) => ({
      id: `${doc.slug}#${heading.id}`,
      title: doc.title,
      heading: heading.text,
      href: `/docs/${encodeURIComponent(doc.slug)}/${heading.id ? `#${encodeURIComponent(heading.id)}` : ""}`,
      body: plain(lines.slice(heading.line - 1, (headings[index + 1]?.line ?? lines.length + 1) - 1).join("\n")),
    })).filter((section) => section.body);
  });
  return { version: 1, sections };
}

export function validDocSearch(value: unknown): value is DocSearchIndex {
  if (!value || typeof value !== "object" || !("version" in value) || value.version !== 1 || !("sections" in value)) return false;
  return Array.isArray(value.sections) && value.sections.length < 10_000 && value.sections.every((s: unknown) => {
    if (!s || typeof s !== "object") return false;
    const section = s as Record<string, unknown>;
    return ["id", "title", "heading", "href", "body"].every((key) => typeof section[key] === "string")
      && (section.href as string).startsWith("/docs/") && (section.body as string).length < 1_000_000;
  });
}

function snippet(body: string, terms: string[]): string {
  const lower = body.toLowerCase();
  const positions = terms.map((term) => lower.indexOf(term)).filter((position) => position >= 0);
  const start = Math.max(0, (positions.length ? Math.min(...positions) : 0) - 20);
  const end = Math.min(body.length, start + 180);
  return `${start ? "…" : ""}${body.slice(start, end)}${end < body.length ? "…" : ""}`;
}

/** Literal token matching: query text is never evaluated as HTML or a regular expression. */
export function searchDocs(index: DocSearchIndex, query: string): (DocSearchSection & { score: number; snippet: string })[] {
  const q = query.trim().toLowerCase().slice(0, 200);
  const terms = q.split(/\s+/).filter(Boolean).slice(0, 12);
  if (!terms.length) return [];
  return index.sections.flatMap((section) => {
    const heading = `${section.title} ${section.heading}`.toLowerCase();
    const body = section.body.toLowerCase();
    if (!terms.every((term) => `${heading} ${body}`.includes(term))) return [];
    const score = (heading.includes(q) ? 60 : 20) + (body.includes(q) ? 10 : 0);
    return [{ ...section, score, snippet: snippet(section.body, terms) }];
  }).sort((a, b) => b.score - a.score || a.href.localeCompare(b.href)).slice(0, 25);
}
