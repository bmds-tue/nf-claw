"use client";

import { Children, isValidElement, useMemo, type ReactNode } from "react";
import Link from "next/link";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link2 } from "lucide-react";
import { CopyButton } from "@/components/ui/copy-button";
import { highlightShell } from "@/components/ui/code-block";
import { resolveDocLink, type LinkContext } from "@/lib/links";
import { docHeadings, slugify } from "@/lib/doc-meta";
import { cn } from "@/lib/utils";

const LINK_CLASS =
  "font-medium text-claw-300 underline decoration-claw-400/30 underline-offset-[3px] transition-colors hover:text-claw-200 hover:decoration-claw-300";

/** Fence languages rendered with shell accents (program, flags, placeholders, comments). */
const SHELL = new Set(["bash", "sh", "shell", "console", "zsh"]);

function CodeBlock({ children, lang }: { children: string; lang: string }) {
  return (
    <div className="group relative my-5 overflow-hidden rounded-2xl border border-white/[0.08] bg-ink-950/80">
      <div className="flex items-center justify-between border-b border-white/[0.06] py-1 pl-4 pr-1.5">
        <span className="font-mono text-[11px] text-fog-dim">{lang || "text"}</span>
        <CopyButton text={children} />
      </div>
      {/* focusable, so a keyboard can scroll a long line into view */}
      <pre tabIndex={0} className="overflow-x-auto px-4 py-4 font-mono text-[13px] leading-relaxed text-fog-muted">
        <code>
          {SHELL.has(lang)
            ? children.split("\n").map((line, i) => (
                <div key={i} className="whitespace-pre">
                  {highlightShell(line)}
                </div>
              ))
            : children}
        </code>
      </pre>
    </div>
  );
}

/** The plain text of rendered Markdown children (for heading ids). */
function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children);
  return "";
}

type HeadingProps = { children?: ReactNode; node?: { position?: { start: { line: number } } } };

export function Markdown({
  content,
  links,
}: {
  content: string;
  /** Where the document lives in the repository, so its relative links resolve on the site. */
  links?: LinkContext;
}) {
  const components = useMemo<Components>(() => {
    // Heading ids come from the source (the same ids the table of contents uses), looked up by the
    // heading's line — never counted during render, which React may repeat.
    const ids = new Map(docHeadings(content).map((h) => [h.line, h.id]));
    const anchored = (Tag: "h2" | "h3", className: string) =>
      function Heading({ children, node }: HeadingProps) {
        const id = ids.get(node?.position?.start.line ?? -1) ?? slugify(textOf(children));
        return (
          <Tag
            id={id}
            data-progress={Tag === "h2" ? textOf(children) : undefined}
            className={cn("group/h relative scroll-mt-6", className)}
          >
            <a
              href={`#${id}`}
              aria-label="Link to this section"
              className="absolute -left-6 top-1/2 hidden -translate-y-1/2 p-1 text-fog-faint opacity-0 transition hover:text-claw-300 group-hover/h:opacity-100 md:block"
            >
              <Link2 className="h-4 w-4" />
            </a>
            {children}
          </Tag>
        );
      };

    return {
      h1: ({ children }) => (
        <h1 className="mb-6 mt-2 text-balance text-3xl font-semibold tracking-tight text-fog md:text-4xl">{children}</h1>
      ),
      h2: anchored("h2", "mb-4 mt-12 border-b border-white/[0.07] pb-3 text-2xl font-semibold tracking-tight text-fog"),
      h3: anchored("h3", "mb-3 mt-8 text-xl font-semibold text-fog"),
      h4: ({ children }) => <h4 className="mb-2 mt-6 text-base font-semibold text-fog">{children}</h4>,
      p: ({ children }) => <p className="my-4 leading-[1.75] text-fog-muted">{children}</p>,
      a: ({ href, children }) => {
        const resolved = links ? resolveDocLink(href, links) : null;
        const target = resolved?.href ?? href;
        if (resolved?.internal) {
          return (
            <Link href={resolved.href} className={LINK_CLASS}>
              {children}
            </Link>
          );
        }
        return (
          <a
            href={target}
            target={target?.startsWith("http") ? "_blank" : undefined}
            rel="noreferrer"
            className={LINK_CLASS}
          >
            {children}
          </a>
        );
      },
      ul: ({ children }) => <ul className="my-4 space-y-2 pl-5 marker:text-claw-400/60 [list-style:disc]">{children}</ul>,
      ol: ({ children }) => <ol className="my-4 space-y-2 pl-5 marker:text-fog-dim [list-style:decimal]">{children}</ol>,
      li: ({ children }) => <li className="pl-1 leading-[1.7] text-fog-muted">{children}</li>,
      blockquote: ({ children }) => (
        <blockquote className="my-5 rounded-r-xl border-l-2 border-claw-400/40 bg-white/[0.02] py-1 pl-5 pr-3 text-fog-muted">
          {children}
        </blockquote>
      ),
      hr: () => <div className="hairline my-10" />,
      strong: ({ children }) => <strong className="font-semibold text-fog">{children}</strong>,
      table: ({ children, node }: { children?: ReactNode; node?: { position?: { start: { line: number } } } }) => {
        // a focusable, labelled region so a keyboard can scroll a wide table; the label names the
        // table by its columns and source line, which keeps it unique on the page
        const head = textOf(Children.toArray(children)[0]).replace(/\s+/g, " ").trim().slice(0, 60);
        const line = node?.position?.start.line;
        return (
          <div
            tabIndex={0}
            role="region"
            aria-label={`Table${head ? `: ${head}` : ""}${line ? ` (line ${line})` : ""}`}
            className="my-6 overflow-x-auto rounded-2xl border border-white/[0.07]"
          >
            <table className="w-full text-sm">{children}</table>
          </div>
        );
      },
      thead: ({ children }) => <thead className="bg-white/[0.03]">{children}</thead>,
      th: ({ children }) => (
        <th className="border-b border-white/[0.07] px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-fog-dim">
          {children}
        </th>
      ),
      td: ({ children }) => <td className="border-b border-white/[0.04] px-4 py-3 align-top text-fog-muted">{children}</td>,
      code: (props) => {
        const { children, className } = props as { children?: ReactNode; className?: string };
        const lang = /language-(\w+)/.exec(className ?? "")?.[1] ?? "";
        const text = Children.toArray(children).map(textOf).join("");
        if (lang || text.includes("\n")) {
          return <CodeBlock lang={lang}>{text.replace(/\n$/, "")}</CodeBlock>;
        }
        return (
          <code
            className={cn(
              "rounded-md border border-white/[0.06] bg-white/[0.05] px-1.5 py-0.5 font-mono text-[0.85em] text-cream",
              // a short flag or path never breaks at its own hyphens ("-" / "-resume")
              text.length <= 32 ? "whitespace-nowrap" : "break-words",
            )}
          >
            {children}
          </code>
        );
      },
      pre: ({ children }) => <>{children}</>,
    };
  }, [content, links]);

  return (
    <div className="text-[15px] text-fog-muted [overflow-wrap:break-word]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
