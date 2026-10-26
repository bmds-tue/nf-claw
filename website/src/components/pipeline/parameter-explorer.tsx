"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ChevronsDownUp, ChevronsUpDown, Code2, Eye, EyeOff, Search, Star } from "lucide-react";
import type { ParamLite, SkillGroupLite } from "@/lib/derive";
import { CopyButton } from "@/components/ui/copy-button";
import { Highlight } from "@/components/ui/highlight";
import { InlineMarkdown } from "@/components/ui/inline-markdown";
import { SearchField } from "@/components/ui/filters";
import { cn, humanize } from "@/lib/utils";
import { EASE } from "@/lib/motion";

const key = (p: ParamLite) => `${p.group}/${p.name}`;

export function ParameterExplorer({
  params,
  groups,
  schemaUrl,
}: {
  params: ParamLite[];
  groups: SkillGroupLite[];
  schemaUrl: string | null;
}) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("All");
  const [requiredOnly, setRequiredOnly] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [open, setOpen] = useState<Set<string>>(new Set());

  // Arriving from a skills search (…/?q=aligner#parameters) carries the query over.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      setQuery(q);
      setShowHidden(true);
    }
  }, []);

  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      params.filter((p) => {
        if (!showHidden && p.hidden) return false;
        if (requiredOnly && !p.required) return false;
        if (group !== "All" && p.group !== group) return false;
        if (!q) return true;
        return (
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.allowed.join(" ").toLowerCase().includes(q) ||
          p.group.toLowerCase().includes(q)
        );
      }),
    [params, q, group, requiredOnly, showHidden],
  );

  const grouped = useMemo(() => {
    const by = new Map<string, ParamLite[]>();
    for (const p of filtered) by.set(p.group, [...(by.get(p.group) ?? []), p]);
    return groups.filter((g) => by.has(g.name)).map((g) => ({ ...g, items: by.get(g.name)! }));
  }, [filtered, groups]);

  const hiddenCount = params.filter((p) => p.hidden).length;
  const allOpen = filtered.length > 0 && filtered.every((p) => open.has(key(p)));
  const toggleAll = () => setOpen(allOpen ? new Set() : new Set(filtered.map(key)));
  const toggle = (k: string) =>
    setOpen((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });
  const reset = () => {
    setQuery("");
    setGroup("All");
    setRequiredOnly(false);
  };

  // Per-group counts under the visibility toggles (not the search, so a group never "vanishes").
  const counts = useMemo(() => {
    const m = new Map<string, number>([["All", 0]]);
    for (const p of params) {
      if ((!showHidden && p.hidden) || (requiredOnly && !p.required)) continue;
      m.set(p.group, (m.get(p.group) ?? 0) + 1);
      m.set("All", m.get("All")! + 1);
    }
    return m;
  }, [params, showHidden, requiredOnly]);

  return (
    <div>
      {/* toolbar */}
      <div className="glass flex flex-col gap-3 p-3 sm:p-4 lg:flex-row lg:items-center">
        <SearchField value={query} onChange={setQuery} placeholder="Search parameters, values, descriptions…" label="Search parameters" className="flex-1" />
        <div className="flex flex-wrap items-center gap-2">
          <Toggle active={requiredOnly} onClick={() => setRequiredOnly((v) => !v)}>
            <Star className="h-3.5 w-3.5" /> Required only
          </Toggle>
          {hiddenCount > 0 && (
            <Toggle active={showHidden} onClick={() => setShowHidden((v) => !v)}>
              {showHidden ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
              Hidden <span className="text-fog-dim">{hiddenCount}</span>
            </Toggle>
          )}
          <Toggle active={false} pressable={false} onClick={toggleAll}>
            {allOpen ? <ChevronsDownUp className="h-3.5 w-3.5" /> : <ChevronsUpDown className="h-3.5 w-3.5" />}
            {allOpen ? "Collapse all" : "Expand all"}
          </Toggle>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-8">
        {/* groups: chips on small screens, a sticky list beside the parameters on large ones */}
        <div className="min-w-0">
          <div className="lg:sticky lg:top-36">
            <p className="mb-2 hidden text-[11px] font-semibold uppercase tracking-[0.16em] text-fog-dim lg:block">Groups</p>
            <div className="mask-fade-r scrollbar-none -mx-1 flex gap-1.5 overflow-x-auto px-1 py-0.5 lg:mask-none lg:mx-0 lg:flex-col lg:gap-0.5 lg:overflow-visible lg:px-0">
              {[{ name: "All" }, ...groups].map((g) => {
                const on = group === g.name;
                const count = counts.get(g.name) ?? 0;
                return (
                  <button
                    key={g.name}
                    onClick={() => setGroup(g.name)}
                    aria-pressed={on}
                    disabled={count === 0}
                    className={cn(
                      "flex shrink-0 items-center justify-between gap-3 whitespace-nowrap rounded-full border px-3 py-1.5 text-left text-xs transition-colors disabled:opacity-35",
                      "lg:rounded-lg lg:border-transparent lg:px-3 lg:py-2 lg:text-[13px]",
                      on
                        ? "border-claw-400/40 bg-claw-500/15 text-claw-100 lg:border-transparent lg:bg-white/[0.06] lg:text-fog"
                        : "border-white/10 bg-white/[0.02] text-fog-muted hover:text-fog lg:bg-transparent lg:hover:bg-white/[0.03]",
                    )}
                  >
                    <span className="truncate">{g.name === "All" ? "All groups" : humanize(g.name)}</span>
                    <span className={cn("tabular-nums", on ? "text-claw-200/70 lg:text-fog-muted" : "text-fog-dim")}>{count}</span>
                  </button>
                );
              })}
            </div>
            {schemaUrl && (
              <a
                href={schemaUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-4 hidden items-center gap-1.5 px-3 text-xs text-fog-dim transition hover:text-claw-300 lg:inline-flex"
              >
                <Code2 className="h-3.5 w-3.5" /> nextflow_schema.json
              </a>
            )}
          </div>
        </div>

        {/* parameters */}
        <div className="min-w-0">
          <p className="mb-3 px-1 text-xs text-fog-dim" aria-live="polite">
            {filtered.length} parameter{filtered.length !== 1 ? "s" : ""}
            {!showHidden && hiddenCount > 0 && ` · ${hiddenCount} hidden`}
          </p>

          {grouped.length === 0 ? (
            <div className="glass flex flex-col items-center gap-3 py-14 text-center">
              <Search className="h-6 w-6 text-fog-faint" />
              <p className="text-sm text-fog-muted">No parameters match.</p>
              <button onClick={reset} className="pill pill-off">
                Reset filters
              </button>
            </div>
          ) : (
            <div className="space-y-8">
              {grouped.map((g) => (
                <section key={g.name} aria-label={g.title}>
                  {group === "All" && (
                    <h3 className="mb-3 flex items-baseline gap-2 px-1 text-sm font-semibold text-fog">
                      {humanize(g.name)}
                      <span className="text-xs font-normal text-fog-dim">{g.items.length}</span>
                    </h3>
                  )}
                  <div className="space-y-2">
                    {g.items.map((p) => (
                      <ParamRow key={key(p)} param={p} query={query} open={open.has(key(p))} onToggle={() => toggle(key(p))} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ParamRow({
  param,
  query,
  open,
  onToggle,
}: {
  param: ParamLite;
  query: string;
  open: boolean;
  onToggle: () => void;
}) {
  const expandable = Boolean(param.description || param.allowed.length || param.constraints || param.default);
  const flag = param.name.startsWith("-") ? param.name : `--${param.name}`;
  const candidate = param.allowed[0] ?? (param.default && param.default.length < 40
    ? param.default.replace(/^`|`$/g, "") : null);
  const concrete = candidate !== null && !/\$|\bparams\.|\bprojectDir\b|^<|^\[|^\{/.test(candidate);
  const boolean = param.type.startsWith("boolean");
  const copyable = boolean || concrete;
  const quoted = candidate === null ? "" : "'" + candidate.replace(/'/g, "'\"'\"'") + "'";
  const example = boolean ? flag : concrete ? `${flag}=${quoted}` : `${flag}=<value>`;
  return (
    <div
      className={cn(
        "group/row rounded-2xl border transition-colors duration-200",
        open ? "border-white/[0.12] bg-white/[0.035]" : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]",
      )}
    >
      <div className="flex items-start gap-2 p-3.5 sm:p-4">
        <button
          onClick={() => expandable && onToggle()}
          aria-expanded={expandable ? open : undefined}
          className="flex min-w-0 flex-1 items-start gap-3 text-left"
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <code className="font-mono text-sm font-medium text-fog">
                <Highlight text={param.name} query={query} />
              </code>
              <span className="chip px-2 py-0.5 text-[10px]">{param.type}</span>
              {param.required && (
                <span className="rounded-md border border-claw-400/20 bg-claw-500/15 px-1.5 py-0.5 text-[10px] font-medium text-claw-300">
                  required
                </span>
              )}
              {param.hidden && (
                <span className="rounded-md border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[10px] text-fog-dim">hidden</span>
              )}
              {param.default && !open && (
                <span className="hidden max-w-[16rem] truncate font-mono text-[11px] text-fog-dim sm:inline">
                  = {param.default.replace(/`/g, "")}
                </span>
              )}
            </div>
            {param.description && (
              <p className={cn("mt-1.5 text-sm leading-relaxed text-fog-muted", !open && "line-clamp-1")}>
                {query.trim() ? (
                  <Highlight text={param.description.replace(/`/g, "")} query={query} />
                ) : (
                  <InlineMarkdown text={param.description} />
                )}
              </p>
            )}
          </div>
          {expandable && (
            <ChevronDown
              className={cn("mt-1 h-4 w-4 shrink-0 text-fog-dim transition-transform duration-300", open && "rotate-180")}
            />
          )}
        </button>
        <CopyButton
          text={flag}
          label={`Copy ${flag}`}
          iconOnly
          className="-mr-1 -mt-0.5 shrink-0 opacity-60 transition-opacity group-hover/row:opacity-100 focus-visible:opacity-100"
        />
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="grid gap-4 border-t border-white/[0.05] px-4 py-3.5 text-xs sm:grid-cols-3">
              <Field label="Default">
                {param.default ? (
                  <code className="break-all font-mono text-cream">{param.default.replace(/`/g, "")}</code>
                ) : (
                  <span className="text-fog-dim">—</span>
                )}
              </Field>
              <Field label="Constraints">
                {param.constraints ? (
                  <span className="break-words font-mono text-[11px] text-fog-muted">{param.constraints}</span>
                ) : (
                  <span className="text-fog-dim">—</span>
                )}
              </Field>
              <Field label="Allowed values">
                {param.allowed.length ? (
                  <span className="flex flex-wrap gap-1">
                    {param.allowed.map((a) => (
                      <code key={a} className="rounded bg-white/[0.05] px-1.5 py-0.5 font-mono text-[11px] text-fog">
                        {a}
                      </code>
                    ))}
                  </span>
                ) : (
                  <span className="text-fog-dim">any</span>
                )}
              </Field>
              <div className="sm:col-span-3">
                <div className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-ink-950/60 py-1.5 pl-3 pr-1.5">
                  <code className="min-w-0 truncate font-mono text-[12px] text-fog-muted">
                    <span className="text-cream">{flag}</span>
                    {example.slice(flag.length)}
                  </code>
                  {copyable ? <CopyButton text={example} label="Copy" /> :
                    <span className="px-2 text-xs text-fog-dim">Set a concrete value before copying</span>}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="mb-1 text-[10px] uppercase tracking-wider text-fog-dim">{label}</div>
      <div>{children}</div>
    </div>
  );
}

function Toggle({
  active,
  onClick,
  children,
  pressable = true,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  /** A toggle reports its pressed state; a plain action button does not. */
  pressable?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={pressable ? active : undefined}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-xl border px-3 py-2.5 text-xs font-medium transition-colors",
        active
          ? "border-claw-400/40 bg-claw-500/15 text-claw-200"
          : "border-white/10 bg-ink-900/60 text-fog-muted hover:border-white/20 hover:text-fog",
      )}
    >
      {children}
    </button>
  );
}
