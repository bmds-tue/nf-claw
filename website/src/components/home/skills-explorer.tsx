"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  ArrowUpRight,
  BookOpen,
  ChevronDown,
  ChevronRight,
  GitCommitHorizontal,
  Layers,
  Puzzle,
  Search,
  SlidersHorizontal,
  Table2,
} from "lucide-react";
import type { ParamHit, SkillCard } from "@/lib/derive";
import { colorForCategory, domainCounts } from "@/lib/derive";
import { CodeBlock } from "@/components/ui/code-block";
import { Highlight } from "@/components/ui/highlight";
import { InlineMarkdown } from "@/components/ui/inline-markdown";
import { SearchField, DomainChips } from "@/components/ui/filters";
import { useParamIndex } from "@/lib/param-index";
import { cn, formatDate, humanize } from "@/lib/utils";
import { EASE } from "@/lib/motion";

const MOBILE_PAGE = 8;

type Result = { skill: SkillCard; matchedParams: ParamHit[] };

export function SkillsExplorer({ skills }: { skills: SkillCard[] }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [selected, setSelected] = useState<string | null>(skills.find((s) => s.name === "rnaseq")?.name ?? skills[0]?.name ?? null);
  // Small screens open a skill's detail inline under its row; this is that row (independent of the
  // selection, which always stays on a visible result for the large-screen detail panel).
  const [mobileOpen, setMobileOpen] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  // Large screens show the selected skill beside the list (a listbox); small screens open it under
  // its row (a disclosure). The roles follow the layout, so a listbox never holds a skill's detail.
  const [compact, setCompact] = useState(false);
  useEffect(() => {
    const layout = window.matchMedia("(max-width: 1023px)");
    const update = () => setCompact(layout.matches);
    update();
    layout.addEventListener("change", update);
    return () => layout.removeEventListener("change", update);
  }, []);

  const categories = useMemo(() => domainCounts(skills), [skills]);

  const q = query.trim().toLowerCase();
  // Parameters are not in the page: they load the first time the search box is used.
  const [warm, setWarm] = useState(false);
  const { index, failed, retry } = useParamIndex(warm || q.length > 0);

  const results = useMemo<Result[]>(() => {
    return skills
      .filter((s) => category === "All" || s.category === category)
      .map((s) => {
        const matchedParams: ParamHit[] =
          q && index
            ? (index[s.name] ?? [])
                .filter(([name, , description]) => name.toLowerCase().includes(q) || description.toLowerCase().includes(q))
                .map(([name, group, description]) => ({ name, group, description }))
            : [];
        const textMatch =
          !q ||
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.category.toLowerCase().includes(q);
        return { skill: s, matchedParams, visible: textMatch || matchedParams.length > 0, rank: s.name.toLowerCase().startsWith(q) ? 0 : textMatch ? 1 : 2 };
      })
      .filter((r) => r.visible)
      .sort((a, b) => (q ? a.rank - b.rank || b.matchedParams.length - a.matchedParams.length : 0) || a.skill.name.localeCompare(b.skill.name));
  }, [skills, category, q, index]);

  // Keep the selection inside the visible results.
  useEffect(() => {
    if (results.length && !results.some((r) => r.skill.name === selected)) setSelected(results[0].skill.name);
  }, [results, selected]);

  useEffect(() => {
    setShowAll(false);
    setMobileOpen(null);
  }, [q, category]);

  const current = results.find((r) => r.skill.name === selected) ?? results[0] ?? null;
  const totalParamHits = results.reduce((n, r) => n + r.matchedParams.length, 0);

  const onListKey = (e: React.KeyboardEvent) => {
    // Only rows on screen: small screens hide everything past the first page until "Show all".
    const pool = !showAll && compact ? results.slice(0, MOBILE_PAGE) : results;
    if (!pool.length) return;
    const focused = (e.target as HTMLElement).closest<HTMLElement>("[data-skill]")?.dataset.skill;
    const i = pool.findIndex((r) => r.skill.name === (focused ?? selected));
    let next = -1;
    if (e.key === "ArrowDown") next = Math.min(pool.length - 1, i + 1);
    else if (e.key === "ArrowUp") next = Math.max(0, i - 1);
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = pool.length - 1;
    if (next >= 0) {
      e.preventDefault();
      setSelected(pool[next].skill.name);
      listRef.current?.querySelector<HTMLElement>(`[data-skill="${pool[next].skill.name}"]`)?.focus();
    }
  };

  return (
    <div className="mt-12">
      <div className="glass flex flex-col gap-3 p-3 sm:p-4">
        <SearchField
          value={query}
          onChange={setQuery}
          onFocus={() => setWarm(true)}
          placeholder="Search skills, descriptions and every parameter (e.g. “aligner”, “strandedness”)…"
          label="Search skills and parameters"
        />
        <DomainChips domains={categories} total={skills.length} value={category} onChange={setCategory} wrapFrom="lg" />
      </div>

      <p className="mt-3 px-1 text-xs text-fog-dim" aria-live="polite">
        {results.length} skill{results.length !== 1 ? "s" : ""}
        {q && !index && !failed && " · searching parameters…"}
        {q && failed && " · parameter search unavailable"}
        {q && totalParamHits > 0 && ` · ${totalParamHits} matching parameter${totalParamHits !== 1 ? "s" : ""}`}
      </p>

      {failed && <button type="button" onClick={retry}
        className="mt-2 rounded-lg border border-white/20 px-3 py-2 text-sm text-fog">
        Retry parameter search
      </button>}

      {results.length === 0 ? (
        <div className="glass mt-4 flex flex-col items-center gap-3 py-16 text-center">
          <Search className="h-6 w-6 text-fog-faint" />
          <p className="text-sm text-fog-muted">
            {index || failed ? `No skill or parameter matches “${query}”.` : "Searching parameters…"}
          </p>
          <button onClick={() => { setQuery(""); setCategory("All"); }} className="pill pill-off">
            Reset filters
          </button>
        </div>
      ) : (
        <div className="mt-4 grid items-start gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
          {/* list — a sticky sidebar beside the detail on large screens */}
          <div className="glass min-w-0 p-2 lg:sticky lg:top-24">
            <div
              ref={listRef}
              role={compact ? undefined : "listbox"}
              aria-label={compact ? undefined : "Skills"}
              onKeyDown={onListKey}
              className="space-y-1 lg:max-h-[min(680px,calc(100vh-8rem))] lg:overflow-y-auto lg:pr-1"
            >
              {results.map((r, i) => {
                const isSel = current?.skill.name === r.skill.name;
                const hiddenOnMobile = !showAll && i >= MOBILE_PAGE;
                return (
                  <div key={r.skill.name} className={cn(hiddenOnMobile && "hidden lg:block")}>
                    <SkillRow
                      result={r}
                      query={query}
                      selected={isSel}
                      compact={compact}
                      open={mobileOpen === r.skill.name}
                      onSelect={() => {
                        setSelected(r.skill.name);
                        setMobileOpen((o) => (o === r.skill.name ? null : r.skill.name));
                      }}
                    />
                    {/* on small screens the detail opens inline, under its row */}
                    <AnimatePresence initial={false}>
                      {mobileOpen === r.skill.name && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={reduce ? { duration: 0 } : { duration: 0.3, ease: EASE }}
                          className="overflow-hidden lg:hidden"
                        >
                          <div className="px-2 pb-3 pt-1">
                            <SkillDetail result={r} query={query} />
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
            {!showAll && results.length > MOBILE_PAGE && (
              <button
                onClick={() => setShowAll(true)}
                className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-xl border border-white/[0.07] py-3 text-sm text-fog-muted transition hover:border-white/15 hover:text-fog lg:hidden"
              >
                Show all {results.length} skills <ChevronDown className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* detail (large screens) */}
          <div className="hidden min-w-0 lg:block">
            <div className="glass p-6 xl:p-7">
              <AnimatePresence mode="wait">
                {current && (
                  <motion.div
                    key={current.skill.name}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={reduce ? { duration: 0 } : { duration: 0.25, ease: EASE }}
                  >
                    <SkillDetail result={current} query={query} large />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SkillRow({
  result,
  query,
  selected,
  compact,
  open,
  onSelect,
}: {
  result: Result;
  query: string;
  selected: boolean;
  /** Small-screen layout: the row discloses its detail instead of selecting it. */
  compact: boolean;
  /** Its detail is expanded inline (small screens). */
  open: boolean;
  onSelect: () => void;
}) {
  const { skill, matchedParams } = result;
  const reduce = useReducedMotion();
  return (
    <button
      data-skill={skill.name}
      role={compact ? undefined : "option"}
      aria-selected={compact ? undefined : selected}
      aria-expanded={compact ? open : undefined}
      tabIndex={compact || selected ? 0 : -1}
      onClick={onSelect}
      className={cn(
        "relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors duration-200 hover:bg-white/[0.03]",
        open && "bg-white/[0.06]",
        selected && "lg:bg-white/[0.06]",
        !open && "max-lg:bg-transparent",
      )}
    >
      {selected && (
        <motion.span
          layoutId="skill-active"
          className="absolute inset-y-2 left-0 hidden w-0.5 rounded-full bg-claw-400 lg:block"
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 40 }}
        />
      )}
      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colorForCategory(skill.category) }} />
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline gap-2">
          <span className="truncate font-mono text-sm font-semibold text-fog">
            <Highlight text={skill.name} query={query} />
          </span>
          <span className="shrink-0 font-mono text-[11px] text-fog-dim">{skill.version}</span>
        </span>
        <span className="block truncate text-xs text-fog-dim">{skill.description}</span>
      </span>
      {matchedParams.length > 0 ? (
        <span className="shrink-0 rounded-md border border-claw-400/20 bg-claw-500/10 px-1.5 py-0.5 text-[10px] font-medium text-claw-300">
          {matchedParams.length} param{matchedParams.length !== 1 ? "s" : ""}
        </span>
      ) : (
        <ChevronRight
          className={cn(
            "h-4 w-4 shrink-0 text-fog-faint transition-transform duration-300",
            open && "max-lg:rotate-90",
            selected && "lg:translate-x-0.5 lg:text-fog-dim",
          )}
        />
      )}
    </button>
  );
}

function SkillDetail({ result, query, large = false }: { result: Result; query: string; large?: boolean }) {
  const { skill, matchedParams } = result;
  const [outputsOpen, setOutputsOpen] = useState(false);
  // Inline (small screens) the detail sits under the section heading, with no skill heading of its own.
  const Subheading = large ? "h4" : "h3";
  const explorerHref = `/pipelines/${skill.name}/${query.trim() && matchedParams.length ? `?q=${encodeURIComponent(query.trim())}` : ""}#parameters`;

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {large && (
              <h3 className="font-mono text-2xl font-semibold text-fog">
                <Link href={`/pipelines/${skill.name}/`} className="transition hover:text-claw-300">
                  {skill.name}
                </Link>
              </h3>
            )}
            <span className="chip">
              <span className="h-2 w-2 rounded-full" style={{ background: colorForCategory(skill.category) }} />
              {skill.category}
            </span>
          </div>
          <p className="mt-1 text-xs text-fog-dim">{skill.pipeline}</p>
        </div>
        <div className="text-right">
          <div className="font-mono text-sm text-fog">{skill.version}</div>
          {skill.releaseDate && <div className="text-[11px] text-fog-dim">{formatDate(skill.releaseDate)}</div>}
        </div>
      </div>

      {large && <p className="mt-4 text-sm leading-relaxed text-fog-muted">{skill.description}</p>}

      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <Stat icon={<SlidersHorizontal className="h-3.5 w-3.5" />}>{skill.parameterCount} params</Stat>
        <Stat icon={<Layers className="h-3.5 w-3.5" />}>{skill.groups.length} groups</Stat>
        <Stat icon={<Puzzle className="h-3.5 w-3.5" />}>{skill.moduleCount} modules</Stat>
        {skill.hasSamplesheet && <Stat icon={<Table2 className="h-3.5 w-3.5" />}>{skill.samplesheetCount}-column sheet</Stat>}
        <Stat icon={<GitCommitHorizontal className="h-3.5 w-3.5" />}>
          <span className="font-mono">{skill.commit}</span>
        </Stat>
      </div>

      {matchedParams.length > 0 && (
        <div className="mt-5 rounded-2xl border border-claw-400/15 bg-claw-500/[0.04] p-4">
          <p className="mb-3 text-[11px] font-medium uppercase tracking-wider text-claw-300/80">
            {matchedParams.length} matching parameter{matchedParams.length !== 1 ? "s" : ""}
          </p>
          <ul className="space-y-2">
            {matchedParams.slice(0, 5).map((p) => (
              <li key={`${p.group}-${p.name}`} className="text-sm">
                <code className="font-mono text-[13px] text-fog">
                  <Highlight text={p.name} query={query} />
                </code>
                <span className="ml-2 text-[10px] uppercase tracking-wider text-fog-dim">{humanize(p.group)}</span>
                {p.description && (
                  <p className="mt-0.5 line-clamp-1 text-xs text-fog-muted">
                    <Highlight text={p.description.replace(/`/g, "")} query={query} />
                  </p>
                )}
              </li>
            ))}
          </ul>
          {matchedParams.length > 5 && (
            <Link href={explorerHref} className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-claw-300 hover:text-claw-200">
              See all {matchedParams.length} in the explorer <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>
      )}

      <div className="mt-5">
        <CodeBlock code={skill.runCommand} label="run it" />
      </div>
      {skill.demoCommand && (
        <div className="mt-3">
          <CodeBlock code={skill.demoCommand} label="demo · bundled test profile" />
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        {skill.required.length > 0 && (
          <div>
            <Subheading className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-fog-dim">Required parameters</Subheading>
            <ul className="space-y-2">
              {skill.required.map((r) => (
                <li key={r.name} className="text-sm">
                  <code className="font-mono text-[13px] text-claw-300">{r.name}</code>
                  <span className="ml-2 text-[11px] text-fog-dim">{r.type}</span>
                  {r.description && (
                    <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-fog-muted">
                      <InlineMarkdown text={r.description} />
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div>
          <Subheading className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-fog-dim">Parameter groups</Subheading>
          <div className="flex flex-wrap gap-1.5">
            {skill.groups.map((g) => (
              <span key={g.name} className="chip px-2.5 py-0.5 text-[11px]">
                {humanize(g.name)}
                <span className="text-fog-dim">{g.count}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {skill.outputs && (
        <div className="mt-6">
          <Subheading className="mb-2 text-[11px] font-medium uppercase tracking-wider text-fog-dim">Outputs</Subheading>
          <p className={cn("text-sm leading-relaxed text-fog-muted", !outputsOpen && "line-clamp-3")}>
            <InlineMarkdown text={skill.outputs} />
          </p>
          <button
            onClick={() => setOutputsOpen((v) => !v)}
            className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-fog-dim transition hover:text-fog"
            aria-expanded={outputsOpen}
          >
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", outputsOpen && "rotate-180")} />
            {outputsOpen ? "Less" : "More"}
          </button>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[0.06] pt-5">
        <Link
          href={explorerHref}
          className="group inline-flex items-center gap-1.5 text-sm font-medium text-claw-300 transition hover:text-claw-200"
        >
          Full parameter explorer
          <ArrowUpRight className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </Link>
        {skill.usageUrl && (
          <a
            href={skill.usageUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-fog-dim transition hover:text-fog"
          >
            <BookOpen className="h-4 w-4" /> Upstream docs
          </a>
        )}
      </div>
    </div>
  );
}

function Stat({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-fog-muted">
      <span className="text-claw-400/70">{icon}</span>
      {children}
    </span>
  );
}
