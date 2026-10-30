"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useInView, useReducedMotion } from "framer-motion";
import {
  ArrowUpRight,
  Check,
  GitBranch,
  LayoutGrid,
  Orbit,
  Plus,
  Puzzle,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type { PipelineSummary, SortKey } from "@/lib/derive";
import { DOMAIN_ORDER, colorForCategory, comparePipelines, domainCounts } from "@/lib/derive";
import { layoutConstellation } from "@/lib/constellation";
import { useCopy } from "@/components/ui/copy-button";
import { Highlight } from "@/components/ui/highlight";
import { SearchField, DomainChips } from "@/components/ui/filters";
import { cn, formatDate } from "@/lib/utils";
import { EASE } from "@/lib/motion";

const MAX_COMPARE = 4;

/** Short wedge label: the domain's first word ("Microbial & metagenomics" → "Microbial"). */
function shortLabel(category: string): string {
  if (category === "Data & utilities") return "Utilities";
  return category.split(" & ")[0];
}

export function PipelineUniverse({ pipelines }: { pipelines: PipelineSummary[] }) {
  const reduce = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("All");
  const [hoverCategory, setHoverCategory] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("domain");
  const [view, setView] = useState<"orbit" | "grid">("orbit");
  const [selected, setSelected] = useState<string | null>(pipelines.find((p) => p.name === "rnaseq")?.name ?? pipelines[0]?.name ?? null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [compare, setCompare] = useState<string[]>([]);
  const chartRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const inView = useInView(chartRef, { once: true, margin: "-80px" });

  // On a phone the disc is too small to tap, so the list is the better default there.
  useEffect(() => {
    setMounted(true);
    if (window.matchMedia("(max-width: 767px)").matches) setView("grid");
  }, []);

  const byName = useMemo(() => new Map(pipelines.map((p) => [p.name, p])), [pipelines]);

  const categories = useMemo(() => domainCounts(pipelines), [pipelines]);

  const q = query.trim().toLowerCase();
  const matches = (p: PipelineSummary) => {
    const inQuery =
      !q ||
      p.name.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q) ||
      p.tools.some((t) => t.toLowerCase().includes(q));
    return inQuery && (category === "All" || p.category === category);
  };

  const sorted = useMemo(() => [...pipelines].sort(comparePipelines(sort)), [pipelines, sort]);

  const filtered = sorted.filter(matches);
  const matchSet = new Set(filtered.map((p) => p.name));

  // A search that narrows to one pipeline selects it — once, when the narrowing happens: the
  // filtered array itself is rebuilt on every render.
  useEffect(() => {
    if (q && filtered.length === 1) setSelected(filtered[0].name);
  }, [q, filtered.length]);

  const layout = useMemo(
    () =>
      layoutConstellation(
        pipelines.map((p) => ({ name: p.name, category: p.category, parameterCount: p.parameterCount })),
        DOMAIN_ORDER,
        { labelName: shortLabel },
      ),
    [pipelines],
  );
  const nodeByName = useMemo(() => new Map(layout.nodes.map((n) => [n.name, n])), [layout]);
  // Keyboard order follows the disc: clockwise from the top.
  const ring = useMemo(() => [...layout.nodes].sort((a, b) => a.angle - b.angle).map((n) => n.name), [layout]);

  const selectedPipeline = selected ? byName.get(selected) ?? null : null;
  const focusCategory = hoverCategory ?? (category !== "All" ? category : null);
  const tip = hovered ? nodeByName.get(hovered) : null;
  const tipPipeline = hovered ? byName.get(hovered) : null;

  const toggleCompare = (name: string) =>
    setCompare((c) => (c.includes(name) ? c.filter((n) => n !== name) : c.length >= MAX_COMPARE ? c : [...c, name]));

  const onChartKey = (e: React.KeyboardEvent) => {
    const pool = ring.filter((n) => matchSet.has(n));
    if (!pool.length) return;
    const i = selected ? pool.indexOf(selected) : -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      setSelected(pool[(i + 1) % pool.length]);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      setSelected(pool[(i - 1 + pool.length) % pool.length]);
    } else if (e.key === "Enter" && selected) {
      router.push(`/pipelines/${selected}/`);
    }
  };

  const { cx, cy, width: W, height: H } = layout;

  return (
    <div className="mt-12">
      {/* toolbar */}
      <div className="glass flex flex-col gap-3 p-3 sm:p-4 md:flex-row md:items-center">
        <SearchField value={query} onChange={setQuery} placeholder="Search pipelines, domains or tools (e.g. “salmon”)…" label="Search pipelines" className="flex-1" />
        <div className="flex items-center gap-2">
          <AnimatePresence initial={false}>
            {view === "grid" && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.25, ease: EASE }}
                className="relative flex-1 overflow-hidden md:flex-none"
              >
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortKey)}
                  aria-label="Sort pipelines"
                  className="w-full appearance-none rounded-xl border border-white/10 bg-ink-900/60 py-3 pl-4 pr-9 text-sm text-fog-muted outline-none transition focus:border-claw-400/40"
                >
                  <option value="domain">Sort: Domain</option>
                  <option value="parameters">Sort: Parameters</option>
                  <option value="modules">Sort: Modules</option>
                  <option value="newest">Sort: Newest</option>
                </select>
                <SlidersHorizontal className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fog-dim" />
              </motion.div>
            )}
          </AnimatePresence>
          <div className="relative flex rounded-xl border border-white/10 bg-ink-900/60 p-1" role="group" aria-label="View">
            {(
              [
                ["orbit", "Orbit", Orbit],
                ["grid", "Grid", LayoutGrid],
              ] as const
            ).map(([v, label, Icon]) => (
              <button
                key={v}
                onClick={() => setView(v)}
                aria-pressed={view === v}
                className={cn(
                  "relative inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors",
                  view === v ? "text-fog" : "text-fog-dim hover:text-fog",
                )}
              >
                {view === v && (
                  <motion.span
                    layoutId="universe-view"
                    className="absolute inset-0 rounded-lg bg-white/10"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <Icon className="relative h-4 w-4" />
                <span className="relative">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* domain chips */}
      <div className="mt-4">
        <DomainChips
          domains={categories}
          total={pipelines.length}
          value={category}
          onChange={setCategory}
          onHover={setHoverCategory}
        />
      </div>
      <p className="mt-3 text-xs text-fog-dim" aria-live="polite">
        {filtered.length === pipelines.length
          ? `${pipelines.length} pipelines across ${categories.length} domains`
          : `${filtered.length} of ${pipelines.length} pipelines match`}
      </p>

      {/* main */}
      <div className="mt-4 grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        {/* visualization */}
        <div className="glass relative flex min-w-0 flex-col overflow-hidden p-2 sm:p-3">
          <AnimatePresence mode="wait" initial={false}>
            {view === "orbit" ? (
              <motion.div
                key="orbit"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="flex flex-1 flex-col justify-center"
              >
                <div
                  ref={chartRef}
                  className="relative rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-claw-400/60"
                  tabIndex={0}
                  role="listbox"
                  aria-label="Pipeline constellation — use the arrow keys to move between pipelines, Enter to open one"
                  aria-activedescendant={selected ? `node-${selected}` : undefined}
                  onKeyDown={onChartKey}
                  onMouseLeave={() => setHovered(null)}
                >
                  <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full select-none">
                    <defs>
                      <radialGradient id="hubGlow">
                        <stop offset="0%" stopColor="rgba(57,211,83,0.28)" />
                        <stop offset="100%" stopColor="rgba(57,211,83,0)" />
                      </radialGradient>
                    </defs>

                    {/* guide rings */}
                    {[0.45, 0.72, 1].map((f, i) => (
                      <ellipse
                        key={f}
                        cx={cx}
                        cy={cy}
                        rx={(layout.rInner + (layout.rOuter - layout.rInner) * f) * layout.sx}
                        ry={layout.rInner + (layout.rOuter - layout.rInner) * f}
                        fill="none"
                        stroke="rgba(255,255,255,0.045)"
                        strokeDasharray={i === 2 ? undefined : "2 6"}
                      />
                    ))}

                    {/* domain wedges */}
                    {layout.wedges.map((w, i) => {
                      const color = colorForCategory(w.category);
                      const lit = focusCategory === w.category;
                      const faded = focusCategory !== null && !lit;
                      return (
                        <g
                          key={w.category}
                          className="cursor-pointer"
                          onMouseEnter={() => setHoverCategory(w.category)}
                          onMouseLeave={() => setHoverCategory(null)}
                          onClick={() => setCategory(category === w.category ? "All" : w.category)}
                        >
                          <motion.path
                            d={w.path}
                            fill={color}
                            initial={reduce ? false : { opacity: 0 }}
                            animate={{ opacity: !inView ? 0 : lit ? 0.14 : faded ? 0.02 : 0.05 }}
                            transition={{ duration: 0.5, delay: inView && !lit && !faded ? 0.1 + i * 0.05 : 0 }}
                          />
                          {/* the wedge's tag: leader, dot on the bisector, name and count */}
                          <motion.g
                            initial={reduce ? false : { opacity: 0 }}
                            animate={{ opacity: !inView ? 0 : faded ? 0.35 : 1 }}
                            transition={{ duration: 0.5, delay: inView && !faded && !lit ? 0.4 + i * 0.05 : 0 }}
                          >
                            <line
                              x1={w.label.leader.x1}
                              y1={w.label.leader.y1}
                              x2={w.label.leader.x2}
                              y2={w.label.leader.y2}
                              stroke={color}
                              strokeOpacity={lit ? 0.9 : 0.5}
                              strokeWidth={1.25}
                              strokeLinecap="round"
                            />
                            <circle cx={w.label.dot.x} cy={w.label.dot.y} r={lit ? 5 : 4} fill={color} />
                            <circle cx={w.label.dot.x} cy={w.label.dot.y} r={8} fill={color} opacity={lit ? 0.22 : 0.12} />
                            <text
                              x={w.label.nameAt.x}
                              y={w.label.nameAt.y}
                              textAnchor={w.label.anchor}
                              fontSize="13.5"
                              fontWeight={lit ? 600 : 500}
                              fill={lit ? "#F4F5F6" : "#C9CDD3"}
                            >
                              {w.label.name}
                            </text>
                            <text
                              x={w.label.subAt.x}
                              y={w.label.subAt.y}
                              textAnchor={w.label.anchor}
                              fontSize="11.5"
                              fill="#8A919B"
                            >
                              {w.label.sub}
                            </text>
                          </motion.g>
                        </g>
                      );
                    })}

                    {/* the selected / hovered pipeline's link to the hub */}
                    {[selected, hovered !== selected ? hovered : null].map((name, i) => {
                      const n = name ? nodeByName.get(name) : null;
                      if (!n) return null;
                      return (
                        <motion.line
                          key={`${i}-${n.name}`}
                          x1={cx}
                          y1={cy}
                          x2={n.x}
                          y2={n.y}
                          stroke={colorForCategory(n.category)}
                          strokeWidth={i === 0 ? 1.4 : 1}
                          strokeOpacity={i === 0 ? 0.55 : 0.3}
                          strokeLinecap="round"
                          initial={reduce ? false : { pathLength: 0 }}
                          animate={{ pathLength: 1 }}
                          transition={{ duration: 0.45, ease: EASE }}
                          pointerEvents="none"
                        />
                      );
                    })}

                    {/* hub */}
                    <g pointerEvents="none">
                      <circle cx={cx} cy={cy} r={layout.rInner - 18} fill="url(#hubGlow)" />
                      <circle cx={cx} cy={cy} r={36} fill="#0A0B0E" stroke="rgba(57,211,83,0.45)" strokeWidth={1} />
                      <text x={cx} y={cy - 1} textAnchor="middle" fontSize="12.5" fontWeight="600" fill="#F4F5F6" style={{ fontFamily: "var(--font-mono)" }}>
                        nf-claw
                      </text>
                      <text x={cx} y={cy + 14} textAnchor="middle" fontSize="9.5" fill="#7C838E">
                        {filtered.length === pipelines.length ? `${pipelines.length} pipelines` : `${filtered.length} / ${pipelines.length}`}
                      </text>
                    </g>

                    {/* nodes */}
                    {layout.nodes.map((n) => {
                      const p = byName.get(n.name)!;
                      const dim = !matchSet.has(n.name) || (hoverCategory !== null && n.category !== hoverCategory);
                      const isSel = n.name === selected;
                      const isHover = n.name === hovered;
                      const color = colorForCategory(n.category);
                      // the sweep-in order: clockwise from the top
                      const order = (n.angle + Math.PI / 2 + Math.PI * 2) % (Math.PI * 2);
                      return (
                        <motion.g
                          key={n.name}
                          id={`node-${n.name}`}
                          role="option"
                          aria-selected={isSel}
                          aria-label={`${p.name} ${p.version}, ${p.category}`}
                          className="cursor-pointer"
                          onClick={() => setSelected(n.name)}
                          onMouseEnter={() => setHovered(n.name)}
                          initial={reduce ? false : { opacity: 0, scale: 0 }}
                          animate={inView ? { opacity: dim ? 0.18 : 1, scale: 1 } : { opacity: 0, scale: 0 }}
                          transition={{
                            opacity: { duration: 0.3 },
                            scale: { duration: 0.6, ease: EASE, delay: inView ? 0.25 + order * 0.12 : 0 },
                          }}
                        >
                          {/* generous invisible hit target */}
                          <circle cx={n.x} cy={n.y} r={Math.max(n.r + 6, 12)} fill="transparent" />
                          {/* The server cannot observe the motion preference. Add this optional
                              element only after hydration so both initial trees agree. */}
                          {isSel && mounted && !reduce && (
                            <motion.circle
                              cx={n.x}
                              cy={n.y}
                              fill="none"
                              stroke={color}
                              strokeWidth={1.2}
                              initial={{ r: n.r + 2, opacity: 0.6 }}
                              animate={{ r: [n.r + 2, n.r + 14], opacity: [0.6, 0] }}
                              transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
                            />
                          )}
                          <circle cx={n.x} cy={n.y} r={n.r + 4} fill={color} opacity={isSel || isHover ? 0.25 : 0.1} />
                          <circle
                            cx={n.x}
                            cy={n.y}
                            r={isHover && !isSel ? n.r + 1.5 : n.r}
                            fill={color}
                            stroke={isSel ? "#ffffff" : "#0A0B0E"}
                            strokeWidth={isSel ? 2 : 1.5}
                            style={{ transition: "r 0.2s ease" }}
                          />
                        </motion.g>
                      );
                    })}
                    {/* the selected pipeline's name, drawn last so no neighbouring node covers it */}
                    {selected && nodeByName.get(selected) && <SelectedLabel node={nodeByName.get(selected)!} reduce={!!reduce} />}
                  </svg>

                  {/* hover tooltip */}
                  <AnimatePresence>
                    {tip && tipPipeline && tip.name !== selected && (
                      <motion.div
                        key="tip"
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-xl border border-white/10 bg-ink-900/95 px-3 py-2 shadow-[0_12px_32px_-8px_rgba(0,0,0,0.8)] backdrop-blur"
                        style={{ left: `${(tip.x / W) * 100}%`, top: `calc(${(tip.y / H) * 100}% - ${tip.r + 10}px)` }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{ background: colorForCategory(tip.category) }} />
                          <span className="font-mono text-sm font-semibold text-fog">{tip.name}</span>
                          <span className="font-mono text-[11px] text-fog-dim">{tipPipeline.version}</span>
                        </div>
                        <div className="mt-0.5 text-[11px] text-fog-dim">
                          {tipPipeline.category} · {tipPipeline.parameterCount} params
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-2 pb-1 pt-2 text-[11px] text-fog-dim">
                  <span className="flex items-center gap-2">
                    <span className="flex items-end gap-1" aria-hidden>
                      <span className="h-1.5 w-1.5 rounded-full bg-fog-dim" />
                      <span className="h-2.5 w-2.5 rounded-full bg-fog-dim" />
                      <span className="h-3.5 w-3.5 rounded-full bg-fog-dim" />
                    </span>
                    size = parameters · color = domain
                  </span>
                  <span className="hidden sm:inline">Click a node or wedge · arrow keys to step through</span>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="grid"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="grid max-h-[600px] content-start gap-2.5 overflow-y-auto p-1 sm:grid-cols-2"
              >
                {filtered.map((p) => (
                  <button
                    key={p.name}
                    onClick={() => setSelected(p.name)}
                    aria-pressed={p.name === selected}
                    className={cn(
                      "group rounded-2xl border p-4 text-left transition-colors duration-200",
                      p.name === selected
                        ? "border-claw-400/40 bg-claw-500/[0.06]"
                        : "border-white/[0.07] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.035]",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex min-w-0 items-center gap-2 font-mono text-sm font-semibold text-fog">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colorForCategory(p.category) }} />
                        <span className="truncate">
                          <Highlight text={p.name} query={query} />
                        </span>
                      </span>
                      <span className="shrink-0 font-mono text-xs text-fog-dim">{p.version}</span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-fog-muted">{p.description}</p>
                    <div className="mt-3 flex gap-3 text-[11px] text-fog-dim">
                      <span>{p.parameterCount} params</span>
                      <span>{p.moduleCount} modules</span>
                      <span className="ml-auto truncate">{p.category}</span>
                    </div>
                  </button>
                ))}
                {filtered.length === 0 && <EmptyState onReset={() => { setQuery(""); setCategory("All"); }} />}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* inspector */}
        <div className="glass relative flex min-h-[420px] flex-col overflow-hidden p-6">
          {selectedPipeline && (
            <div
              aria-hidden
              className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full blur-[90px] transition-colors duration-700"
              style={{ background: `${colorForCategory(selectedPipeline.category)}26` }}
            />
          )}
          <AnimatePresence mode="wait">
            {selectedPipeline ? (
              <Inspector
                key={selectedPipeline.name}
                p={selectedPipeline}
                inCompare={compare.includes(selectedPipeline.name)}
                compareFull={compare.length >= MAX_COMPARE}
                onCompare={() => toggleCompare(selectedPipeline.name)}
              />
            ) : (
              <p className="m-auto text-sm text-fog-dim">Select a pipeline to inspect.</p>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* compare tray */}
      <AnimatePresence>
        {compare.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: 20, height: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="overflow-hidden"
          >
            <CompareTray
              names={compare}
              byName={byName}
              onRemove={(n) => setCompare((c) => c.filter((x) => x !== n))}
              onClear={() => setCompare([])}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SelectedLabel({ node, reduce }: { node: { name: string; category: string; x: number; y: number; r: number }; reduce: boolean }) {
  const w = node.name.length * 7 + 20;
  const h = 22;
  // above the node, or below it when the top edge is too close
  const above = node.y - node.r - h - 8 > 4;
  const y = above ? node.y - node.r - h - 7 : node.y + node.r + 7;
  return (
    <motion.g
      key={node.name}
      pointerEvents="none"
      initial={reduce ? false : { opacity: 0, y: above ? 4 : -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: EASE }}
    >
      <rect
        x={node.x - w / 2}
        y={y}
        width={w}
        height={h}
        rx={h / 2}
        fill="#0A0B0E"
        fillOpacity={0.94}
        stroke={colorForCategory(node.category)}
        strokeOpacity={0.55}
      />
      <text
        x={node.x}
        y={y + 15}
        textAnchor="middle"
        fontSize="12"
        fontWeight="600"
        fill="#F4F5F6"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {node.name}
      </text>
    </motion.g>
  );
}

function Inspector({
  p,
  inCompare,
  compareFull,
  onCompare,
}: {
  p: PipelineSummary;
  inCompare: boolean;
  compareFull: boolean;
  onCompare: () => void;
}) {
  const { copied, failed, copy } = useCopy();
  const tools = p.tools.slice(0, 7);
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.28, ease: EASE }}
      className="relative flex h-full flex-col"
    >
      <div className="flex items-center gap-2">
        <span className="chip">
          <span className="h-2 w-2 rounded-full" style={{ background: colorForCategory(p.category) }} />
          {p.category}
        </span>
        <span className="ml-auto font-mono text-sm text-fog-muted">{p.version}</span>
      </div>
      <h3 className="mt-4 font-mono text-2xl font-semibold text-fog">{p.name}</h3>
      <p className="mt-1 text-xs text-fog-dim">{p.pipeline}</p>
      <p className="mt-4 text-sm leading-relaxed text-fog-muted">{p.description}</p>

      {tools.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {tools.map((t) => (
            <span key={t} className="rounded-md border border-white/[0.07] bg-white/[0.03] px-2 py-0.5 text-[11px] text-fog-muted">
              {t}
            </span>
          ))}
          {p.tools.length > tools.length && (
            <span className="px-1 py-0.5 text-[11px] text-fog-dim">+{p.tools.length - tools.length} more</span>
          )}
        </div>
      )}

      <div className="mt-5 grid grid-cols-2 gap-2.5">
        <Metric icon={<SlidersHorizontal className="h-4 w-4" />} value={p.parameterCount} label="parameters" />
        <Metric icon={<Puzzle className="h-4 w-4" />} value={p.moduleCount} label="nf-core modules" />
        <Metric icon={<GitBranch className="h-4 w-4" />} value={p.groupCount} label="param groups" />
        <Metric icon={<Check className="h-4 w-4" />} value={p.requiredCount} label="required" />
      </div>

      {p.releaseDate && (
        <p className="mt-4 text-xs text-fog-dim">
          Pinned release · {formatDate(p.releaseDate)}
          {p.policy && ` · ${p.policy}`}
        </p>
      )}

      <div className="mt-auto grid grid-cols-2 gap-2 pt-6">
        <Link
          href={`/pipelines/${p.name}/`}
          className="col-span-2 inline-flex items-center justify-center gap-2 rounded-xl bg-claw-500 px-4 py-3 text-sm font-semibold text-ink-950 transition hover:bg-claw-400 hover:shadow-[0_10px_30px_-12px_rgba(57,211,83,0.7)] active:scale-[0.97]"
        >
          Inspect pipeline
          <ArrowUpRight className="h-4 w-4" />
        </Link>
        <button
          onClick={() => void copy(p.runCommand)}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2.5 text-xs font-medium text-fog-muted transition hover:border-white/20 hover:text-fog"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-claw-400" /> : <span className="font-mono text-claw-400">$</span>}
          {copied ? "Copied" : failed ? "Copy failed" : "Copy run command"}
        </button>
        <button
          onClick={onCompare}
          disabled={!inCompare && compareFull}
          title={!inCompare && compareFull ? "Compare holds up to four pipelines" : undefined}
          className={cn(
            "inline-flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40",
            inCompare
              ? "border-claw-400/40 bg-claw-500/10 text-claw-200"
              : "border-white/10 bg-white/[0.02] text-fog-muted hover:border-white/20 hover:text-fog",
          )}
        >
          {inCompare ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {inCompare ? "Comparing" : "Compare"}
        </button>
      </div>
    </motion.div>
  );
}

const COMPARE_ROWS: [string, (p: PipelineSummary) => string | number, boolean][] = [
  ["Domain", (p) => p.category, false],
  ["Version", (p) => p.version, false],
  ["Parameters", (p) => p.parameterCount, true],
  ["Param groups", (p) => p.groupCount, true],
  ["nf-core modules", (p) => p.moduleCount, true],
  ["Required params", (p) => p.requiredCount, true],
  ["Samplesheet columns", (p) => p.samplesheetCount, true],
  ["Pinned", (p) => (p.releaseDate ? formatDate(p.releaseDate) : "—"), false],
];

function CompareTray({
  names,
  byName,
  onRemove,
  onClear,
}: {
  names: string[];
  byName: Map<string, PipelineSummary>;
  onRemove: (name: string) => void;
  onClear: () => void;
}) {
  const ps = names.map((n) => byName.get(n)!).filter(Boolean);
  return (
    <div className="glass mt-6 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-fog">
          Comparing {ps.length} pipeline{ps.length > 1 ? "s" : ""}
          <span className="ml-2 font-normal text-fog-dim">· up to {MAX_COMPARE}</span>
        </h4>
        <button onClick={onClear} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-fog-dim transition hover:bg-white/5 hover:text-fog">
          <X className="h-3.5 w-3.5" /> Clear
        </button>
      </div>
      {/* focusable, so a keyboard can scroll the table sideways on a narrow screen */}
      <div tabIndex={0} role="region" aria-label="Pipeline comparison" className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-fog-dim">
              <th className="py-2 pr-4 font-medium">Metric</th>
              {ps.map((p) => (
                <th key={p.name} className="py-2 pr-4 font-medium normal-case tracking-normal">
                  <span className="inline-flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full" style={{ background: colorForCategory(p.category) }} />
                    <Link href={`/pipelines/${p.name}/`} className="font-mono text-sm text-fog hover:text-claw-300">
                      {p.name}
                    </Link>
                    <button
                      onClick={() => onRemove(p.name)}
                      className="inline-flex h-5 w-5 items-center justify-center rounded text-fog-dim transition hover:bg-white/5 hover:text-fog"
                      aria-label={`Remove ${p.name} from comparison`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARE_ROWS.map(([label, get, numeric]) => {
              const values = ps.map(get);
              const max = numeric && ps.length > 1 ? Math.max(...(values as number[])) : null;
              return (
                <tr key={label} className="border-t border-white/[0.05]">
                  <td className="py-2.5 pr-4 text-fog-dim">{label}</td>
                  {values.map((v, i) => (
                    <td
                      key={ps[i].name}
                      className={cn("py-2.5 pr-4 tabular-nums", max !== null && v === max ? "font-semibold text-claw-300" : "text-fog")}
                    >
                      {v}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ icon, value, label }: { icon: React.ReactNode; value: number; label: string }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="flex items-center gap-2 text-claw-400/80">{icon}</div>
      <div className="mt-2 text-2xl font-semibold tabular-nums text-fog">{value}</div>
      <div className="text-[11px] text-fog-dim">{label}</div>
    </div>
  );
}

function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="col-span-full flex flex-col items-center gap-3 py-16 text-center">
      <Search className="h-6 w-6 text-fog-faint" />
      <p className="text-sm text-fog-muted">No pipelines match your search.</p>
      <button onClick={onReset} className="pill pill-off">
        Reset filters
      </button>
    </div>
  );
}
