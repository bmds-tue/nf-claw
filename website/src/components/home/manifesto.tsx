"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { GitBranch, RefreshCw, ShieldCheck } from "lucide-react";
import type { PipelineSummary } from "@/lib/derive";
import { colorForCategory } from "@/lib/derive";
import { EASE } from "@/lib/motion";

const PRINCIPLES = [
  {
    icon: GitBranch,
    title: "Pinned, unmodified",
    body: "Every pipeline is an nf-core release pinned as a git submodule — wrapped, never forked.",
  },
  {
    icon: RefreshCw,
    title: "Generated context",
    body: "skill.md and the full parameter reference are generated from the pinned schema, not written by hand.",
  },
  {
    icon: ShieldCheck,
    title: "Drift-gated",
    body: "CI regenerates the context from pinned schemas and checks for drift. This site builds from the same repository.",
  },
];

export function Manifesto({ pipelines }: { pipelines: PipelineSummary[] }) {
  const reduce = useReducedMotion();
  const track = [...pipelines, ...pipelines];
  // The marquee travels half the track (one full set of names) per cycle, so the
  // duration must scale with the pipeline count to keep a constant, calm speed
  // no matter how large the library grows.
  const marqueeDuration = Math.max(40, pipelines.length * 4);

  return (
    <section className="relative border-y border-white/[0.06] py-14 md:py-16">
      {/* marquee of pipeline names — pauses under the pointer so a name can be clicked */}
      <div className="mask-fade-x group relative overflow-hidden" aria-label="Pipelines in the library">
        <div
          className="flex w-max gap-8 will-change-transform group-hover:[animation-play-state:paused]"
          style={reduce ? undefined : { animation: `marquee ${marqueeDuration}s linear infinite` }}
        >
          {track.map((p, i) => (
            <Link
              key={`${p.name}-${i}`}
              href={`/pipelines/${p.name}/`}
              tabIndex={i >= pipelines.length ? -1 : undefined}
              aria-hidden={i >= pipelines.length ? true : undefined}
              className="group/name flex items-center gap-3 whitespace-nowrap rounded-lg"
            >
              <span className="h-2 w-2 rounded-full" style={{ background: colorForCategory(p.category) }} />
              <span className="font-mono text-xl font-semibold text-fog/60 transition-colors group-hover/name:text-fog md:text-2xl">
                {p.name}
              </span>
              <span className="text-sm text-fog-dim">{p.category}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="container-site mt-12 grid gap-6 md:mt-14 md:grid-cols-3 md:gap-5">
        {PRINCIPLES.map((p, i) => (
          <motion.div
            key={p.title}
            initial={reduce ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: i * 0.08, ease: EASE }}
            className="flex gap-4"
          >
            <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-claw-400">
              <p.icon className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-fog">{p.title}</h2>
              <p className="mt-1 text-sm leading-relaxed text-fog-muted">{p.body}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
