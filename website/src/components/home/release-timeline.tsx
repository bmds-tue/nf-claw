"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, Rocket, Tag } from "lucide-react";
import type { TimelineEntry } from "@/lib/types";
import { cn, formatDate, formatMonth } from "@/lib/utils";
import { EASE } from "@/lib/motion";

/** A timeline entry with the colour of its research domain. */
export type TimelineItem = TimelineEntry & { accent: string };

/** How many entries show before "full history" — whole months are kept together. */
const INITIAL = 10;

type Group = { key: string; label: string; items: TimelineItem[] };

function groupByMonth(items: TimelineItem[]): Group[] {
  const groups: Group[] = [];
  for (const item of items) {
    const key = item.date ? item.date.slice(0, 7) : "undated";
    const label = item.date ? formatMonth(item.date) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(item);
    else groups.push({ key, label, items: [item] });
  }
  return groups;
}

export function ReleaseTimeline({ items }: { items: TimelineItem[] }) {
  const reduce = useReducedMotion();
  const [filter, setFilter] = useState<"all" | "release" | "tag">("all");
  const [expanded, setExpanded] = useState(false);
  const topRef = useRef<HTMLDivElement>(null);

  const hasTags = items.some((i) => i.kind === "tag");
  const filtered = useMemo(() => items.filter((i) => filter === "all" || i.kind === filter), [items, filter]);
  const groups = useMemo(() => groupByMonth(filtered), [filtered]);

  // Show whole months until at least INITIAL entries are on screen.
  const initialGroups = useMemo(() => {
    let n = 0;
    let g = 0;
    while (g < groups.length && n < INITIAL) n += groups[g++].items.length;
    return Math.max(1, g);
  }, [groups]);
  const visible = expanded ? groups : groups.slice(0, initialGroups);
  const hiddenCount = groups.slice(initialGroups).reduce((n, g) => n + g.items.length, 0);

  const releases = items.filter((i) => i.kind === "release" && i.date);
  const years = releases.map((i) => new Date(i.date!).getUTCFullYear());
  const span = years.length ? `${Math.min(...years)}–${Math.max(...years)}` : null;

  const collapse = () => {
    setExpanded(false);
    topRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };

  return (
    <div className="mt-12" ref={topRef}>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-fog-muted">
          <span className="font-semibold text-fog">{releases.length}</span> pinned releases
          {span && (
            <>
              {" "}
              spanning <span className="text-fog">{span}</span>
            </>
          )}
          {hasTags && (
            <>
              {" "}
              · <span className="text-fog">{items.length - releases.length}</span> library tags
            </>
          )}
        </p>
        {hasTags && (
          <div className="flex gap-2" role="group" aria-label="Filter timeline">
            {(["all", "release", "tag"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
                className={cn("pill capitalize", filter === f ? "pill-on" : "pill-off")}
              >
                {f === "all" ? "All" : `${f}s`}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="relative">
        {/* spine */}
        <div
          aria-hidden
          className="absolute bottom-0 left-[7px] top-2 w-px bg-gradient-to-b from-claw-400/50 via-white/10 to-transparent md:left-[151px]"
        />

        <ol className="space-y-10">
          <AnimatePresence initial={false}>
            {visible.map((g, gi) => (
              <motion.li
                key={g.key}
                initial={reduce ? false : { opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? undefined : { opacity: 0, transition: { duration: 0.15 } }}
                transition={{ duration: 0.45, ease: EASE, delay: gi >= initialGroups ? (gi - initialGroups) * 0.04 : 0 }}
                className="relative grid gap-4 pl-8 md:grid-cols-[120px_1fr] md:gap-10 md:pl-0"
              >
                {/* month */}
                <div className="md:pt-3 md:text-right">
                  <span
                    aria-hidden
                    className="absolute left-0 top-1.5 h-[15px] w-[15px] rounded-full border-2 border-claw-400/70 bg-ink md:left-[144px] md:top-3.5"
                  />
                  <h3 className="text-sm font-semibold text-fog md:sticky md:top-24">{g.label}</h3>
                  <p className="text-xs text-fog-dim">
                    {g.items.length} {g.items.length === 1 ? "entry" : "entries"}
                  </p>
                </div>

                {/* entries */}
                <motion.ul
                  className="grid gap-3 lg:grid-cols-2"
                  initial={reduce ? false : "hidden"}
                  whileInView="show"
                  viewport={{ once: true, margin: "-40px" }}
                  variants={{ show: { transition: { staggerChildren: 0.05 } } }}
                >
                  {g.items.map((item) => (
                    <motion.li
                      key={item.id}
                      variants={{
                        hidden: { opacity: 0, y: 12 },
                        show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
                      }}
                    >
                      <Entry item={item} />
                    </motion.li>
                  ))}
                </motion.ul>
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>

        {(hiddenCount > 0 || expanded) && groups.length > initialGroups && (
          <div className="relative mt-10 flex justify-center md:justify-start md:pl-[176px]">
            <button
              onClick={() => (expanded ? collapse() : setExpanded(true))}
              aria-expanded={expanded}
              className="group inline-flex items-center gap-2 rounded-full border border-white/10 bg-ink-900/80 px-5 py-2.5 text-sm font-medium text-fog-muted backdrop-blur transition hover:border-claw-400/30 hover:text-fog"
            >
              {expanded ? "Show recent only" : `Show full history · ${hiddenCount} more`}
              <ChevronDown className={cn("h-4 w-4 transition-transform duration-300", expanded && "rotate-180")} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Entry({ item }: { item: TimelineItem }) {
  const Icon = item.kind === "release" ? Rocket : Tag;
  const body = (
    <>
      <span
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.08] bg-ink-900"
        style={{ boxShadow: `0 0 18px -6px ${item.accent}80` }}
      >
        <Icon className="h-4 w-4" style={{ color: item.accent }} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-3">
          <span className="truncate font-mono text-sm font-semibold text-fog transition-colors group-hover:text-claw-200">
            {item.pipeline ? (
              <>
                {item.pipeline}
                <span className="ml-1.5 font-normal text-fog-muted">{item.version}</span>
              </>
            ) : (
              item.title
            )}
          </span>
          <span className="shrink-0 text-[11px] tabular-nums text-fog-dim">{item.date ? formatDate(item.date) : "unreleased"}</span>
        </span>
        <span className="mt-0.5 line-clamp-1 text-xs leading-relaxed text-fog-muted">{item.subtitle}</span>
      </span>
    </>
  );
  const cls = "glass glass-hover group flex items-center gap-3.5 rounded-2xl p-3.5";
  return item.pipeline ? (
    <Link href={`/pipelines/${item.pipeline}/`} className={cls}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}
