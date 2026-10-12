import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { ArrowLeft, ArrowRight, Clock, FileText, Github } from "lucide-react";
import { getDefaultBranch, getDoc, getDocs, getRemote } from "@/lib/data";
import type { LinkContext } from "@/lib/links";
import { docHeadings, docPreview, readingMinutes } from "@/lib/doc-meta";
import { Markdown } from "@/components/ui/markdown";
import { DocToc } from "@/components/docs/doc-toc";
import { Reveal } from "@/components/ui/reveal";
import { OG_IMAGE, siteUrl } from "@/lib/site";
import { cn } from "@/lib/utils";

export function generateStaticParams() {
  return getDocs().map((d) => ({ slug: d.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const doc = getDoc(slug);
  if (!doc) return { title: "Document not found" };
  const description = docPreview(doc.content, 160);
  return {
    title: doc.title,
    description,
    alternates: { canonical: siteUrl(`/docs/${doc.slug}/`) },
    openGraph: { title: `${doc.title} · nf-claw`, description, type: "article", images: [OG_IMAGE] },
  };
}

/** Apply `strip` until nothing more is removed: one pass can join "<!<!---->--" into "<!--". */
function stripUntilStable(text: string, strip: (value: string) => string): string {
  for (let previous = ""; previous !== text; ) {
    previous = text;
    text = strip(text);
  }
  return text;
}

function clean(md: string): string {
  // Frontmatter only at the very start: with a multiline flag `^` matched any `---` line, so a
  // horizontal rule deleted everything up to the next `---` (even one inside a table separator).
  const body = md.replace(/^---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/, "");
  const base = stripUntilStable(body, (text) => text.replace(/<!--[\s\S]*?-->/g, "")) // comments
    .replace(/^<p[\s\S]*?<\/p>\s*/i, "") // leading centered logo block
    .trim();

  // Plain-text files (e.g. NOTICE) use long runs of "=" as section dividers.
  // A run directly under a text line is a setext heading underline (keep it so
  // the heading still renders); a standalone run is a divider → make it a real
  // <hr> instead of an 80-character string that overflows the column.
  const lines = base.split("\n");
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^={3,}\s*$/.test(line)) {
      const prev = i > 0 ? lines[i - 1] : "";
      const isSetextUnderline = prev.trim() !== "" && !/^[=_*\s-]+$/.test(prev);
      if (!isSetextUnderline) {
        out.push("", "---", "");
        continue;
      }
    }
    out.push(line);
  }
  return out.join("\n");
}

export default async function DocPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const doc = getDoc(slug);
  if (!doc) notFound();

  const all = getDocs();
  const index = all.findIndex((d) => d.slug === slug);
  const prev = index > 0 ? all[index - 1] : null;
  const next = index < all.length - 1 ? all[index + 1] : null;
  // Repository-relative links resolve to this site's doc pages, or to the file on GitHub.
  const remote = getRemote();
  const branch = getDefaultBranch();
  const links: LinkContext = {
    source: doc.source,
    docs: Object.fromEntries(all.map((d) => [d.source, d.slug])),
    repoBlobBase: remote ? `https://github.com/${remote}/blob/${branch}` : null,
  };
  const body = clean(doc.content);
  const headings = docHeadings(body);

  return (
    <div className="container-site pt-24 md:pt-28">
      <Link href="/docs/" className="inline-flex items-center gap-2 text-sm text-fog-dim transition hover:text-fog">
        <ArrowLeft className="h-4 w-4" /> Documentation hub
      </Link>

      <div className="mt-8 grid gap-10 lg:grid-cols-[200px_minmax(0,1fr)] xl:grid-cols-[200px_minmax(0,1fr)_200px] xl:gap-12">
        {/* all docs */}
        <aside aria-label="All documents" className="hidden lg:block">
          <nav aria-label="Documentation" className="sticky top-24">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-fog-dim">Docs</p>
            <ul className="space-y-0.5">
              {all.map((d) => {
                const on = d.slug === slug;
                return (
                  <li key={d.slug}>
                    <Link
                      href={`/docs/${d.slug}/`}
                      aria-current={on ? "page" : undefined}
                      className={cn(
                        "block rounded-lg px-3 py-2 text-[13px] transition-colors",
                        on ? "bg-white/[0.06] font-medium text-fog" : "text-fog-dim hover:bg-white/[0.03] hover:text-fog",
                      )}
                    >
                      {d.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </aside>

        <article className="min-w-0">
          {/* on small screens: jump between docs */}
          <div className="mask-fade-r scrollbar-none -mx-1 mb-6 flex gap-2 overflow-x-auto px-1 py-0.5 lg:hidden">
            {all.map((d) => (
              <Link
                key={d.slug}
                href={`/docs/${d.slug}/`}
                aria-current={d.slug === slug ? "page" : undefined}
                className={cn("pill", d.slug === slug ? "pill-on" : "pill-off")}
              >
                {d.title}
              </Link>
            ))}
          </div>

          <Reveal y={12}>
            <header className="mb-8 flex flex-wrap items-center gap-x-5 gap-y-3">
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-claw-400">
                <FileText className="h-5 w-5" />
              </span>
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-fog-dim">Generated from</p>
                <code className="font-mono text-sm text-fog">{doc.source}</code>
              </div>
              <div className="ml-auto flex items-center gap-4 text-xs text-fog-dim">
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" /> {readingMinutes(doc.content)} min read
                </span>
                {remote && (
                  <a
                    href={`https://github.com/${remote}/blob/${branch}/${doc.source}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 transition hover:text-claw-300"
                  >
                    <Github className="h-3.5 w-3.5" /> View source
                  </a>
                )}
              </div>
            </header>
            <div className="glass overflow-hidden px-5 py-7 sm:px-8 md:px-10 md:py-10">
              <div className="mx-auto max-w-prose">
                <Markdown content={body} links={links} />
              </div>
            </div>
          </Reveal>

          {(prev || next) && (
            <nav aria-label="More docs" className="mt-8 grid gap-3 sm:grid-cols-2">
              {prev ? (
                <Link href={`/docs/${prev.slug}/`} className="glass glass-hover group flex items-center gap-4 p-5">
                  <ArrowLeft className="h-4 w-4 shrink-0 text-fog-dim transition group-hover:-translate-x-0.5 group-hover:text-claw-300" />
                  <span className="min-w-0">
                    <span className="block text-[11px] uppercase tracking-[0.16em] text-fog-dim">Previous</span>
                    <span className="mt-0.5 block truncate font-medium text-fog">{prev.title}</span>
                  </span>
                </Link>
              ) : (
                <span className="hidden sm:block" />
              )}
              {next && (
                <Link href={`/docs/${next.slug}/`} className="glass glass-hover group flex items-center justify-end gap-4 p-5 text-right">
                  <span className="min-w-0">
                    <span className="block text-[11px] uppercase tracking-[0.16em] text-fog-dim">Next</span>
                    <span className="mt-0.5 block truncate font-medium text-fog">{next.title}</span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-fog-dim transition group-hover:translate-x-0.5 group-hover:text-claw-300" />
                </Link>
              )}
            </nav>
          )}
        </article>

        {/* table of contents */}
        <aside aria-label="Table of contents" className="hidden xl:block">
          <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pb-6">
            <DocToc headings={headings} />
          </div>
        </aside>
      </div>
    </div>
  );
}
