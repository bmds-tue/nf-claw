"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { ArrowUpRight, FileText, Play, Search } from "lucide-react";
import type { Quickstart } from "@/lib/data/quickstart";
import { CopyButton } from "@/components/ui/copy-button";
import { cn } from "@/lib/utils";
import { EASE } from "@/lib/motion";

const TYPE_MS = 22; // per character
const STEP_GAP_MS = 450; // pause between one terminal finishing and the next starting

type Line = { kind: "cmd" | "out" | "comment" | "heading"; text: string };

/** skill.md lines as output: Markdown headings stand out, everything inside a code fence stays plain. */
function markdownLines(lines: string[]): Line[] {
  let fenced = false;
  return lines.map((text) => {
    if (text.startsWith("```")) {
      fenced = !fenced;
      return { kind: "out", text };
    }
    return { kind: !fenced && /^#{1,6} /.test(text) ? "heading" : "out", text };
  });
}

interface Step {
  n: string;
  icon: typeof Search;
  title: string;
  body: string;
  file: string;
  lines: Line[];
  copy: string;
}

function steps(q: Quickstart): Step[] {
  const demo = q.demoCommand?.replace(/\s+#.*$/, "") ?? null;
  return [
    {
      n: "01",
      icon: Search,
      title: "Find the pipeline",
      body: "Grep the catalog for a keyword instead of reading it whole — one line per pipeline.",
      file: "catalog.md",
      lines: [
        { kind: "cmd", text: `grep ${q.name} catalog.md` },
        ...q.catalogLines.map((text) => ({ kind: "out" as const, text })),
      ],
      copy: `grep ${q.name} catalog.md`,
    },
    {
      n: "02",
      icon: FileText,
      title: "Read its skill",
      body: "skill.md is generated from the pinned schema: the exact command, inputs and required parameters.",
      file: `pipelines/${q.name}/skill.md`,
      lines: [
        { kind: "cmd", text: `cat pipelines/${q.name}/skill.md` },
        ...markdownLines(q.skillLines),
        { kind: "comment", text: "…" },
      ],
      copy: `cat pipelines/${q.name}/skill.md`,
    },
    {
      n: "03",
      icon: Play,
      title: "Run it, then check it",
      body: "nfclaw validates first, runs the pinned release and records every run where status can read it.",
      file: "terminal",
      lines: [
        ...(demo ? [{ kind: "comment" as const, text: "# the bundled test profile, end to end" }, { kind: "cmd" as const, text: demo }] : []),
        { kind: "comment", text: "# or your own data" },
        { kind: "cmd", text: q.runCommand },
        { kind: "cmd", text: "nfclaw status results" },
        { kind: "out", text: "status: success" },
      ],
      copy: demo ?? q.runCommand,
    },
  ];
}

/** How many characters of each command are shown, typed one terminal after another. */
function useTypewriter(all: Step[], start: boolean, reduce: boolean) {
  const total = all.map((s) => s.lines.filter((l) => l.kind === "cmd").reduce((n, l) => n + l.text.length, 0));
  const [typed, setTyped] = useState<number[]>(() => all.map(() => 0));
  // the terminal being typed into — or, once all are done, the last one
  const current = Math.max(0, typed.findIndex((t, i) => t < total[i]));
  const active = typed.every((t, i) => t >= total[i]) ? total.length - 1 : current;

  useEffect(() => {
    if (!start) return;
    if (reduce) {
      setTyped(total);
      return;
    }
    let step = 0;
    let chars = 0;
    let timer = 0;
    const tick = () => {
      if (step >= total.length) return;
      chars += 1;
      // React runs the updater later; read the counters now, not when it runs
      const at = step;
      const shown = chars;
      setTyped((t) => t.map((v, i) => (i === at ? shown : v)));
      if (chars >= total[step]) {
        step += 1;
        chars = 0;
        timer = window.setTimeout(tick, STEP_GAP_MS);
      } else {
        timer = window.setTimeout(tick, TYPE_MS);
      }
    };
    timer = window.setTimeout(tick, 350);
    return () => window.clearTimeout(timer);
    // `total` is left out on purpose: it is rebuilt from the same steps on every render, and
    // restarting on each rebuild would restart the typing.
  }, [start, reduce]);

  return { typed, active };
}

export function HowItWorks({ quickstart }: { quickstart: Quickstart }) {
  const reduce = useReducedMotion() ?? false;
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  const all = steps(quickstart);
  const { typed, active: activeStep } = useTypewriter(all, inView, reduce);

  return (
    <div ref={ref} className="relative mt-12">
      {/* the thread linking the three steps (large screens) */}
      <div aria-hidden className="absolute left-[16.66%] right-[16.66%] top-[19px] hidden h-px bg-white/[0.06] lg:block">
        <motion.div
          className="h-full origin-left bg-gradient-to-r from-claw-500/70 via-claw-400/50 to-claw-300/30"
          initial={{ scaleX: reduce ? 1 : 0 }}
          animate={{ scaleX: inView ? 1 : reduce ? 1 : 0 }}
          transition={{ duration: 2.4, ease: EASE, delay: 0.3 }}
        />
      </div>

      <ol className="grid gap-8 lg:grid-cols-3 lg:gap-6">
        {all.map((s, i) => {
          const active = typed[i] > 0;
          return (
            <motion.li
              key={s.n}
              className="flex min-w-0 flex-col"
              initial={reduce ? false : { opacity: 0, y: 24 }}
              animate={inView ? { opacity: 1, y: 0 } : undefined}
              transition={{ duration: 0.7, ease: EASE, delay: i * 0.12 }}
            >
              <div className="flex items-center gap-3 lg:flex-col lg:text-center">
                <span
                  className={cn(
                    "relative z-10 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border font-mono text-xs font-semibold transition-colors duration-500",
                    active
                      ? "border-claw-400/50 bg-ink-900 text-claw-300 shadow-[0_0_24px_-4px_rgba(57,211,83,0.5)]"
                      : "border-white/10 bg-ink-900 text-fog-dim",
                  )}
                >
                  {s.n}
                </span>
                <div className="min-w-0">
                  <h3 className="flex items-center gap-2 text-base font-semibold text-fog lg:mt-3 lg:justify-center">
                    <s.icon className="h-4 w-4 text-claw-400" />
                    {s.title}
                  </h3>
                  <p className="mt-1 text-sm leading-relaxed text-fog-muted lg:mx-auto lg:min-h-[4.3rem] lg:max-w-xs">{s.body}</p>
                </div>
              </div>

              <Terminal step={s} typed={typed[i]} focused={i === activeStep && typed[i] > 0} />
            </motion.li>
          );
        })}
      </ol>

      <motion.p
        className="mt-10 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-center text-sm text-fog-muted"
        initial={reduce ? false : { opacity: 0 }}
        animate={inView ? { opacity: 1 } : undefined}
        transition={{ duration: 0.8, delay: 0.6 }}
      >
        The same three steps work for every pipeline in the library.
        <Link href={`/pipelines/${quickstart.name}/`} className="group inline-flex items-center gap-1 font-medium text-claw-300 hover:text-claw-200">
          See {quickstart.name} in full
          <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </Link>
      </motion.p>
    </div>
  );
}

function Terminal({ step, typed, focused }: { step: Step; typed: number; focused: boolean }) {
  // Walk the lines, spending the typed budget on commands; output appears once its command is done.
  let budget = typed;
  let blocked = false;
  const rendered: { line: Line; text: string; caret: boolean }[] = [];
  for (const line of step.lines) {
    if (blocked) break;
    if (line.kind === "cmd") {
      const shown = line.text.slice(0, Math.max(0, budget));
      budget -= line.text.length;
      const complete = shown.length === line.text.length;
      rendered.push({ line, text: shown, caret: !complete && shown.length > 0 });
      if (!complete) blocked = true;
    } else if (typed > 0) {
      rendered.push({ line, text: line.text, caret: false });
    }
  }
  const finished = !blocked && typed > 0;

  return (
    <div className="glass mt-5 flex flex-1 flex-col overflow-hidden rounded-2xl bg-ink-950/70 lg:min-h-[248px]">
      <div className="flex items-center gap-2 border-b border-white/[0.06] py-2 pl-4 pr-1.5">
        <span className="flex gap-1.5" aria-hidden>
          <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
          <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
          <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
        </span>
        <span className="ml-2 min-w-0 flex-1 truncate font-mono text-[11px] text-fog-dim">{step.file}</span>
        <CopyButton text={step.copy} iconOnly label="Copy command" />
      </div>
      {/* screen readers get the whole transcript at once; the typed animation is visual only */}
      <pre className="sr-only">{step.lines.map((l) => (l.kind === "cmd" ? `$ ${l.text}` : l.text)).join("\n")}</pre>
      <pre aria-hidden className="flex-1 overflow-hidden px-4 py-3.5 font-mono text-[12px] leading-[1.7]">
        <code>
          {rendered.map(({ line, text, caret }, i) => (
            <div
              key={i}
              className={cn(
                "overflow-hidden text-ellipsis whitespace-nowrap",
                line.kind === "out" && "text-fog-muted",
                line.kind === "comment" && "italic text-fog-dim",
                line.kind === "heading" && "font-semibold text-fog",
                line.kind === "out" && line.text.startsWith("status:") && "text-claw-300",
              )}
            >
              {line.kind === "cmd" && <span className="select-none text-claw-400">$ </span>}
              {line.kind === "cmd" ? <span className="text-fog">{text}</span> : text || " "}
              {caret && <Caret />}
            </div>
          ))}
          {finished && (
            <div>
              <span className="select-none text-claw-400">$ </span>
              {focused && <Caret />}
            </div>
          )}
        </code>
      </pre>
    </div>
  );
}

function Caret() {
  return <span className="ml-px inline-block h-[1.05em] w-[0.55em] translate-y-[2px] animate-[caret_1.05s_steps(1)_infinite] bg-claw-400/80" />;
}
