"use client";

import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Sparkles, Boxes, Workflow, SlidersHorizontal, Puzzle, ChevronDown } from "lucide-react";
import { Github } from "@/components/ui/github-icon";
import { Counter } from "@/components/ui/counter";
import { logoSrc } from "@/components/ui/logo";
import { InlineMarkdown } from "@/components/ui/inline-markdown";
import type { RepoMeta } from "@/lib/types";
import { asset, formatDate } from "@/lib/utils";
import { EASE } from "@/lib/motion";

export function Hero({
  meta,
  latest,
}: {
  meta: RepoMeta;
  latest: { name: string; pipeline: string; version: string; date: string | null } | null;
}) {
  const reduce = useReducedMotion();
  const fade = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.9, ease: EASE, delay },
  });

  const repoUrl = meta.remote ? `https://github.com/${meta.remote}` : null;
  const mark = (
    <motion.div
      className="relative overflow-hidden rounded-[28px] shadow-glow ring-1 ring-white/10 transition-shadow duration-300 group-hover:ring-claw-400/40"
      whileHover={reduce ? undefined : { scale: 1.04, rotate: -2 }}
      whileTap={reduce ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 300, damping: 18 }}
    >
      <Image
        src={asset(logoSrc(144))}
        alt="nf-claw"
        width={132}
        height={132}
        priority
        className="h-[104px] w-[104px] object-cover sm:h-[112px] sm:w-[112px] md:h-[132px] md:w-[132px]"
      />
    </motion.div>
  );

  const stats = [
    { label: "Pipelines", value: meta.stats.pipelines, icon: Workflow, href: "/pipelines/" },
    { label: "Agent skills", value: meta.stats.skills, icon: Boxes, href: "/#skills" },
    { label: "Parameters", value: meta.stats.parameters, icon: SlidersHorizontal, href: "/#skills" },
    { label: "nf-core modules", value: meta.stats.modules, icon: Puzzle, href: "/#pipelines" },
  ];

  return (
    <section className="relative flex min-h-[100svh] flex-col items-center justify-center overflow-hidden px-5 pb-28 pt-28 sm:px-6">
      {/* orbital rings behind logo */}
      <div aria-hidden className="pointer-events-none absolute left-1/2 top-[34%] -z-0 -translate-x-1/2 -translate-y-1/2">
        {[320, 520, 760].map((s, i) => (
          <motion.div
            key={s}
            className="absolute rounded-full border border-white/[0.05]"
            style={{ width: s, height: s, left: -s / 2, top: -s / 2 }}
            initial={reduce ? false : { opacity: 0, scale: 0.92 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, rotate: i % 2 === 0 ? 360 : -360 }}
            transition={{
              opacity: { duration: 1.2, delay: 0.2 + i * 0.15 },
              scale: { duration: 1.6, ease: EASE, delay: 0.2 + i * 0.15 },
              rotate: { duration: 60 + i * 24, repeat: Infinity, ease: "linear" },
            }}
          >
            <span
              className="absolute h-1.5 w-1.5 rounded-full bg-claw-400/70 shadow-[0_0_12px_2px_rgba(57,211,83,0.6)]"
              style={{ top: -3, left: "50%" }}
            />
          </motion.div>
        ))}
      </div>

      <div className="relative z-10 flex w-full max-w-4xl flex-col items-center text-center">
        {latest && (
          <motion.div {...fade(0)}>
            <Link
              href={`/pipelines/${latest.name}/`}
              className="group mb-10 inline-flex max-w-full items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] py-1.5 pl-1.5 pr-4 text-sm text-fog-muted backdrop-blur transition hover:border-claw-400/30 hover:bg-white/[0.05]"
            >
              <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-claw-500/15 px-2.5 py-1 text-xs font-medium text-claw-300">
                <Sparkles className="h-3 w-3" /> Latest
              </span>
              <span className="truncate text-fog">
                {latest.pipeline} {latest.version}
              </span>
              {latest.date && (
                <span className="hidden shrink-0 text-fog-dim sm:inline">· {formatDate(latest.date)}</span>
              )}
              <ArrowRight className="h-3.5 w-3.5 shrink-0 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </motion.div>
        )}

        {/* brand mark — opens the repository */}
        <motion.div {...fade(0.05)} className="relative mb-9">
          <div className="absolute inset-0 -z-10 animate-pulse-ring rounded-3xl bg-claw-500/20 blur-2xl" />
          {repoUrl ? (
            <a
              href={repoUrl}
              target="_blank"
              rel="noreferrer"
              aria-label="nf-claw on GitHub (opens in a new tab)"
              title="View nf-claw on GitHub"
              className="group relative block rounded-[28px] focus-visible:outline-offset-4"
            >
              {mark}
              {/* where the click goes, shown on hover and keyboard focus */}
              <span
                aria-hidden
                className="pointer-events-none absolute -bottom-2 -right-2 inline-flex h-9 w-9 scale-75 items-center justify-center rounded-full border border-white/15 bg-ink-900 text-fog opacity-0 shadow-[0_8px_24px_-8px_rgba(0,0,0,0.9)] transition duration-300 ease-out group-hover:scale-100 group-hover:border-claw-400/40 group-hover:opacity-100 group-focus-visible:scale-100 group-focus-visible:opacity-100"
              >
                <Github className="h-4 w-4" />
              </span>
            </a>
          ) : (
            mark
          )}
        </motion.div>

        <motion.p {...fade(0.1)} className="eyebrow mb-5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-claw-400" />
          nf-claw
        </motion.p>

        <motion.h1
          {...fade(0.16)}
          className="text-balance text-[2.6rem] font-semibold leading-[1.03] tracking-tightest sm:text-5xl md:text-7xl"
        >
          <span className="gradient-text">{meta.tagline}</span>
        </motion.h1>

        <motion.p
          {...fade(0.24)}
          className="mt-7 max-w-2xl text-pretty text-base leading-relaxed text-fog-muted sm:text-lg md:text-xl"
        >
          <InlineMarkdown text={meta.description} />
        </motion.p>

        <motion.div {...fade(0.32)} className="mt-10 flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
          <Link
            href="/#pipelines"
            className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-claw-500 px-7 py-3.5 text-sm font-semibold text-ink-950 transition hover:bg-claw-400 hover:shadow-[0_12px_40px_-12px_rgba(57,211,83,0.6)] sm:w-auto active:scale-[0.97]"
          >
            Explore the universe
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <Link
            href="/docs/"
            className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-7 py-3.5 text-sm font-semibold text-fog transition hover:border-white/20 hover:bg-white/[0.06] active:scale-[0.97] sm:w-auto"
          >
            Read the docs
          </Link>
        </motion.div>

        {/* stats */}
        <motion.div {...fade(0.42)} className="mt-16 grid w-full grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
          {stats.map((s) => (
            <Link key={s.label} href={s.href} className="glass glass-hover group flex flex-col items-center px-4 py-5">
              <s.icon className="mb-3 h-5 w-5 text-claw-400/80 transition-transform duration-300 group-hover:-translate-y-0.5" />
              <div className="text-3xl font-semibold tracking-tight text-fog tabular-nums md:text-4xl">
                <Counter value={s.value} />
              </div>
              <div className="mt-1 text-[11px] uppercase tracking-[0.16em] text-fog-dim">{s.label}</div>
            </Link>
          ))}
        </motion.div>
      </div>

      {/* scroll cue */}
      <motion.a
        href="#pipelines"
        aria-label="Scroll to the pipeline universe"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={reduce ? { duration: 0 } : { delay: 1.2, duration: 1 }}
        className="group absolute bottom-6 left-1/2 hidden -translate-x-1/2 flex-col items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-fog-dim transition hover:text-fog-muted sm:flex"
      >
        <motion.span
          animate={reduce ? undefined : { y: [0, 5, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/[0.02] group-hover:border-claw-400/30"
        >
          <ChevronDown className="h-4 w-4" />
        </motion.span>
      </motion.a>
    </section>
  );
}
