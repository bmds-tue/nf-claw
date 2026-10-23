"use client";

import { TerminalSquare } from "lucide-react";
import { CopyButton } from "@/components/ui/copy-button";
import { cn } from "@/lib/utils";

/** Shell-flavoured accents for a command line: program, subcommand, flags, placeholders, comment. */
export function highlightShell(line: string) {
  if (!line.trim()) return <span>&nbsp;</span>;
  if (/^\s*#/.test(line)) return <span className="italic text-fog-dim">{line}</span>;

  // A trailing comment ("… results   # adds the test profile") is dimmed as a whole.
  const hash = line.search(/\s#\s/);
  const code = hash === -1 ? line : line.slice(0, hash);
  const comment = hash === -1 ? "" : line.slice(hash);

  const tokens = code.split(/(\s+)/);
  let word = -1;
  return (
    <>
      {tokens.map((tok, i) => {
        if (/^\s+$/.test(tok) || !tok) return <span key={i}>{tok}</span>;
        word += 1;
        // A wrapped line breaks between words, never inside a short one ("-" / "profile").
        const keep = tok.length <= 32 ? "whitespace-nowrap" : "";
        if (word === 0) return <span key={i} className={cn("text-claw-300", keep)}>{tok}</span>;
        if (/^-{1,2}[\w-]/.test(tok)) return <span key={i} className={cn("text-cream", keep)}>{tok}</span>;
        if (/^<[^>]+>$/.test(tok)) return <span key={i} className={cn("italic text-cream/60", keep)}>{tok}</span>;
        if (word === 1 && /^[a-z]+$/.test(tok)) return <span key={i} className="text-white">{tok}</span>;
        if (/^NXF_\w+=/.test(tok)) return <span key={i} className={cn("text-claw-200/80", keep)}>{tok}</span>;
        return <span key={i} className={cn("text-fog-muted", keep)}>{tok}</span>;
      })}
      {comment && <span className="italic text-fog-dim">{comment}</span>}
    </>
  );
}

/** A command, soft-wrapped so it stays readable without sideways scrolling, with a copy button. */
export function CodeBlock({ code, label = "shell" }: { code: string; label?: string }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-ink-950/80">
      <div className="flex items-center justify-between border-b border-white/[0.06] py-1.5 pl-4 pr-2">
        <span className="flex items-center gap-2 text-xs font-medium text-fog-dim">
          <TerminalSquare className="h-3.5 w-3.5" />
          {label}
        </span>
        <CopyButton text={code} />
      </div>
      <pre className="whitespace-pre-wrap break-words px-4 py-3.5 font-mono text-[13px] leading-relaxed [overflow-wrap:anywhere]">
        <code>
          {code.split("\n").map((line, i) => (
            <div key={i} className="pl-[2ch] -indent-[2ch]">
              {highlightShell(line)}
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}
