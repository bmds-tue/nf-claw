import { Fragment, type ReactNode } from "react";
import { cn, safeHref } from "@/lib/utils";

/**
 * Render the inline Markdown that generated text carries — `code`, **bold**, [links](url) and bare
 * URLs — without a full Markdown parser. Parameter descriptions, the README lead and skill.md's
 * Outputs prose all use it; shown as plain text, their backticks leaked onto the page.
 *
 * Pure (no hooks), so it renders in server and client components alike.
 */
const TOKEN = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)\s]+\))|(https?:\/\/[^\s)<]+[^\s)<.,;:!?'"])/g;

export function InlineMarkdown({ text }: { text: string }) {
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(TOKEN)) {
    const at = m.index ?? 0;
    if (at > last) out.push(<Fragment key={key++}>{text.slice(last, at)}</Fragment>);
    const [tok] = m;
    if (m[1]) {
      const code = tok.slice(1, -1);
      out.push(
        <code
          key={key++}
          className={cn(
            "rounded-[5px] border border-white/[0.07] bg-white/[0.05] px-1 py-px font-mono text-[0.88em] text-cream/90",
            // a short flag or path never breaks at its own hyphens ("-" / "-resume")
            code.length <= 32 && "whitespace-nowrap",
          )}
        >
          {code}
        </code>,
      );
    } else if (m[2]) {
      out.push(
        <strong key={key++} className="font-semibold text-fog">
          {tok.slice(2, -2)}
        </strong>,
      );
    } else if (m[3]) {
      // Parameter descriptions are upstream schema text the update bot regenerates: a link to any
      // other scheme is shown as its label.
      const [, label, href] = tok.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/) ?? [];
      out.push(
        safeHref(href) ? (
          <ExternalLink key={key++} href={href} label={label} />
        ) : (
          <Fragment key={key++}>{label}</Fragment>
        ),
      );
    } else {
      out.push(<ExternalLink key={key++} href={tok} label={tok.replace(/^https?:\/\//, "")} />);
    }
    last = at + tok.length;
  }
  if (last < text.length) out.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  return <span>{out}</span>;
}

function ExternalLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="break-words font-medium text-claw-300 underline decoration-claw-400/30 underline-offset-[3px] transition-colors hover:text-claw-200 hover:decoration-claw-300"
    >
      {label}
    </a>
  );
}

/** The same text with its inline Markdown stripped — for previews, titles and search. */
export function plainText(text: string): string {
  return text
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
}
