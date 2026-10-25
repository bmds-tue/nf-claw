"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, Search, SlidersHorizontal } from "lucide-react";
import type { PipelineSummary } from "@/lib/derive";
import { DOMAIN_ORDER, categoryRank, colorForCategory, domainCounts } from "@/lib/derive";
import { Highlight } from "@/components/ui/highlight";
import { SearchField, DomainChips } from "@/components/ui/filters";
import { formatDate } from "@/lib/utils";
import { EASE } from "@/lib/motion";

type SortKey = "name" | "domain" | "parameters" | "modules" | "newest";

export function PipelineIndex({ pipelines }: { pipelines: PipelineSummary[] }) {
  const reduce = useReducedMotion();
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("All");
  const [sort, setSort] = useState<SortKey>("name");
  const [urlReady, setUrlReady] = useState(false);

  const filterUrl = (nextDomain: string, nextQuery: string) => {
    const sp = new URLSearchParams();
    if (nextDomain !== "All") sp.set("domain", nextDomain);
    if (nextQuery.trim()) sp.set("q", nextQuery.trim());
    return `${window.location.pathname}${sp.size ? `?${sp}` : ""}`;
  };
  const selectDomain = (value: string) => {
    if (value !== domain) history.pushState(history.state, "", filterUrl(value, query));
    setDomain(value);
  };

  // Shareable state: /pipelines/?domain=Epigenomics&q=chip
  useEffect(() => {
    const read = () => {
      const sp = new URLSearchParams(window.location.search);
      const d = sp.get("domain");
      setDomain(d && DOMAIN_ORDER.includes(d) ? d : "All");
      setQuery(sp.get("q") || "");
      setUrlReady(true);
    };
    read();
    window.addEventListener("popstate", read);
    return () => window.removeEventListener("popstate", read);
  }, []);
  useEffect(() => {
    if (urlReady) history.replaceState(history.state, "", filterUrl(domain, query));
  }, [domain, query, urlReady]);

  const domains = useMemo(() => domainCounts(pipelines), [pipelines]);

  const q = query.trim().toLowerCase();
  const shown = useMemo(() => {
    const list = pipelines.filter((p) => {
      if (domain !== "All" && p.category !== domain) return false;
      if (!q) return true;
      return (
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.tools.some((t) => t.toLowerCase().includes(q))
      );
    });
    return list.sort((a, b) => {
      switch (sort) {
        case "domain":
          return categoryRank(a.category) - categoryRank(b.category) || a.name.localeCompare(b.name);
        case "parameters":
          return b.parameterCount - a.parameterCount;
        case "modules":
          return b.moduleCount - a.moduleCount;
        case "newest":
          return (b.releaseDate ? +new Date(b.releaseDate) : 0) - (a.releaseDate ? +new Date(a.releaseDate) : 0);
        default:
          return a.name.localeCompare(b.name);
      }
    });
  }, [pipelines, domain, q, sort]);

  return (
    <div className="mt-10">
      <div className="glass flex flex-col gap-3 p-3 sm:p-4 md:flex-row md:items-center">
        <SearchField value={query} onChange={setQuery} placeholder="Search by name, description or tool…" label="Search pipelines" className="flex-1" />
        <div className="relative">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label="Sort pipelines"
            className="w-full appearance-none rounded-xl border border-white/10 bg-ink-900/60 py-3 pl-4 pr-10 text-sm text-fog-muted outline-none transition focus:border-claw-400/40 md:w-auto"
          >
            <option value="name">Sort: Name</option>
            <option value="domain">Sort: Domain</option>
            <option value="newest">Sort: Newest release</option>
            <option value="parameters">Sort: Most parameters</option>
            <option value="modules">Sort: Most modules</option>
          </select>
          <SlidersHorizontal className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-fog-dim" />
        </div>
      </div>

      <div className="mt-4">
        <DomainChips
          domains={domains}
          total={pipelines.length}
          value={domain}
          onChange={selectDomain}
        />
      </div>

      <p className="mt-4 px-1 text-xs text-fog-dim" aria-live="polite">
        {shown.length === pipelines.length ? `${pipelines.length} pipelines` : `${shown.length} of ${pipelines.length} pipelines`}
      </p>

      <LayoutGroup>
        <motion.ul layout={!reduce} className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence initial={false} mode="popLayout">
            {shown.map((p, i) => {
              const accent = colorForCategory(p.category);
              return (
                <motion.li
                  key={p.name}
                  layout={!reduce}
                  initial={reduce ? false : { opacity: 0, y: 14, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={reduce ? undefined : { opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.35, ease: EASE, delay: Math.min(i, 12) * 0.02 }}
                >
                  <Link href={`/pipelines/${p.name}/`} className="group block h-full rounded-3xl">
                    <article className="glass glass-hover relative flex h-full flex-col overflow-hidden p-6">
                      <div aria-hidden className="absolute -right-12 -top-12 h-32 w-32 rounded-full opacity-70 blur-3xl transition-opacity duration-500 group-hover:opacity-100" style={{ background: `${accent}26` }} />
                      <div className="relative flex items-center justify-between gap-3">
                        <span className="inline-flex min-w-0 items-center gap-2 font-mono text-lg font-semibold text-fog">
                          <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: accent }} />
                          <span className="truncate">
                            <Highlight text={p.name} query={query} />
                          </span>
                        </span>
                        <ArrowUpRight className="h-5 w-5 shrink-0 text-fog-dim transition duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-claw-300" />
                      </div>
                      <p className="relative mt-1 text-xs text-fog-dim">{p.pipeline}</p>
                      <p className="relative mt-3 line-clamp-3 flex-1 text-sm leading-relaxed text-fog-muted">{p.description}</p>
                      {q && p.tools.some((t) => t.toLowerCase().includes(q)) && (
                        <p className="relative mt-3 flex flex-wrap gap-1">
                          {p.tools
                            .filter((t) => t.toLowerCase().includes(q))
                            .slice(0, 4)
                            .map((t) => (
                              <span key={t} className="rounded-md border border-claw-400/20 bg-claw-500/10 px-1.5 py-0.5 text-[11px] text-claw-200">
                                <Highlight text={t} query={query} />
                              </span>
                            ))}
                        </p>
                      )}
                      <div className="relative mt-5 flex items-center justify-between gap-2 border-t border-white/[0.05] pt-4 text-xs text-fog-dim">
                        <span className="truncate">{p.category}</span>
                        <span className="flex shrink-0 items-center gap-3">
                          <span>{p.parameterCount} params</span>
                          <span className="font-mono text-fog-muted">{p.version}</span>
                        </span>
                      </div>
                      {p.releaseDate && <p className="relative mt-2 text-[11px] text-fog-dim">Pinned {formatDate(p.releaseDate)}</p>}
                    </article>
                  </Link>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </motion.ul>
      </LayoutGroup>

      {shown.length === 0 && (
        <div className="glass mt-4 flex flex-col items-center gap-3 py-16 text-center">
          <Search className="h-6 w-6 text-fog-faint" />
          <p className="text-sm text-fog-muted">No pipeline matches “{query}”{domain !== "All" && ` in ${domain}`}.</p>
          <button onClick={() => { setQuery(""); setDomain("All"); }} className="pill pill-off">
            Reset filters
          </button>
        </div>
      )}
    </div>
  );
}
