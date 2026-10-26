"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, CornerDownLeft, FileText, Hash, Search, X } from "lucide-react";
import { Highlight } from "@/components/ui/highlight";
import { colorForCategory } from "@/lib/derive";
import { lockScroll } from "@/lib/scroll-lock";
import { readRecent } from "@/lib/recent";
import { cn } from "@/lib/utils";
import { EASE } from "@/lib/motion";

export interface PaletteData {
  pipelines: { name: string; version: string; category: string; description: string }[];
  docs: { slug: string; title: string; source: string }[];
}

type Item =
  | { kind: "section"; id: string; label: string; hint: string; href: string }
  | { kind: "pipeline"; id: string; label: string; hint: string; href: string; color: string; version: string; description: string }
  | { kind: "doc"; id: string; label: string; hint: string; href: string };

// The home page's sections, in page order.
const SECTIONS = [
  { id: "how", label: "How it works", hint: "Find, read, run — three commands" },
  { id: "pipelines", label: "Pipeline universe", hint: "Explore the constellation" },
  { id: "skills", label: "Skills explorer", hint: "What an agent reads" },
  { id: "activity", label: "Repository activity", hint: "Commits & automation" },
  { id: "releases", label: "Release timeline", hint: "Pinned versions" },
  { id: "docs", label: "Documentation hub", hint: "Rendered from the repo" },
];

export const OPEN_PALETTE_EVENT = "nfclaw:open-palette";

/** Open the palette from anywhere (a search button, the header). */
export function openPalette(): void {
  window.dispatchEvent(new Event(OPEN_PALETTE_EVENT));
}

function score(item: Item, q: string): number {
  const label = item.label.toLowerCase();
  if (label === q) return 100;
  if (label.startsWith(q)) return 80 - label.length / 100;
  if (label.includes(q)) return 60 - label.indexOf(q);
  if (item.kind === "pipeline") {
    if (item.hint.toLowerCase().includes(q)) return 30;
    if (item.description.toLowerCase().includes(q)) return 20;
  }
  if (item.hint.toLowerCase().includes(q)) return 10;
  return 0;
}

export function CommandPalette({ data }: { data: PaletteData }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const restoreFocus = useRef<HTMLElement | null>(null);
  const router = useRouter();
  const pathname = usePathname();
  const reduce = useReducedMotion();
  // pipelines opened lately (this browser only), offered first while the query is empty
  const [recent, setRecent] = useState<string[]>([]);

  const all = useMemo<Item[]>(
    () => [
      ...SECTIONS.map((s) => ({ kind: "section" as const, id: `s-${s.id}`, label: s.label, hint: s.hint, href: `/#${s.id}` })),
      ...data.pipelines.map((p) => ({
        kind: "pipeline" as const,
        id: `p-${p.name}`,
        label: p.name,
        hint: p.category,
        href: `/pipelines/${p.name}/`,
        color: colorForCategory(p.category),
        version: p.version,
        description: p.description,
      })),
      ...data.docs.map((d) => ({ kind: "doc" as const, id: `d-${d.slug}`, label: d.title, hint: d.source, href: `/docs/${d.slug}/` })),
    ],
    [data],
  );

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return all;
    return all
      .map((item) => ({ item, s: score(item, q) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .map((r) => r.item);
  }, [all, query]);

  const groups = useMemo(() => {
    const order: Item["kind"][] = query.trim() ? ["pipeline", "doc", "section"] : ["section", "pipeline", "doc"];
    const titles = { section: "Jump to", pipeline: "Pipelines", doc: "Documentation" };
    const out = order
      .map((kind) => ({ key: kind as string, title: titles[kind], items: results.filter((r) => r.kind === kind) }))
      .filter((g) => g.items.length);
    if (!query.trim() && recent.length) {
      const byName = new Map<string, Item>(all.filter((i) => i.kind === "pipeline").map((i) => [i.label, i]));
      const items = recent.flatMap((name): Item[] => {
        const item = byName.get(name);
        return item ? [{ ...item, id: `r-${name}` }] : [];
      });
      if (items.length) out.unshift({ key: "recent", title: "Recent", items });
    }
    return out;
  }, [results, query, recent, all]);
  const flat = useMemo(() => groups.flatMap((g) => g.items), [groups]);

  const close = useCallback(() => setOpen(false), []);

  // Global shortcuts: ⌘K / Ctrl+K anywhere, "/" when not typing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement | null)?.closest?.("input, textarea, select, [contenteditable=true]");
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (open) setOpen(false);
        else openPalette();
      } else if (e.key === "/" && !typing && !open) {
        e.preventDefault();
        openPalette();
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_PALETTE_EVENT, onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_PALETTE_EVENT, onOpen);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    restoreFocus.current = document.activeElement as HTMLElement | null;
    setRecent(readRecent());
    setQuery("");
    setActive(0);
    const unlock = lockScroll();
    requestAnimationFrame(() => inputRef.current?.focus());
    return () => {
      unlock();
      if (restoreFocus.current?.isConnected) restoreFocus.current.focus();
    };
  }, [open]);

  // Any navigation — including browser back/forward — closes the palette.
  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => setActive(0), [query]);

  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-index="${active}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const go = useCallback(
    (item: Item | undefined) => {
      if (!item) return;
      setOpen(false);
      if (item.kind === "section" && pathname === "/") {
        const id = item.href.slice(2);
        document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
        history.replaceState(null, "", `#${id}`);
        return;
      }
      router.push(item.href);
    },
    [pathname, reduce, router],
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (flat.length ? (i + 1) % flat.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (flat.length ? (i - 1 + flat.length) % flat.length : 0));
    } else if (e.key === "Home") {
      setActive(0);
    } else if (e.key === "End") {
      setActive(Math.max(0, flat.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(flat[active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
    } else if (e.key === "Tab") {
      // keep focus inside the dialog: the input is its only control
      e.preventDefault();
    }
  };

  let index = -1;

  // The overlay is always mounted and shown/hidden with CSS. Unmounting it through an exit
  // animation left an invisible layer over the page in production builds after a navigation
  // (the exit never reported complete), swallowing every click.
  return (
    <div
      className={cn(
        "fixed inset-0 z-[70] flex items-start justify-center px-4 pt-[12vh] sm:pt-[14vh]",
        // visibility flips at once when opening (so the input can take focus), after the fade when closing
        open
          ? "visible opacity-100 [transition:opacity_200ms]"
          : "pointer-events-none invisible opacity-0 [transition:opacity_200ms,visibility_0s_linear_200ms]",
      )}
      aria-hidden={!open}
    >
      <div className="absolute inset-0 bg-ink-950/70 backdrop-blur-sm" onClick={close} aria-hidden />
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Search nf-claw"
          className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 bg-ink-900/95 shadow-[0_40px_120px_-20px_rgba(0,0,0,0.9),0_0_0_1px_rgba(57,211,83,0.06)] backdrop-blur-xl"
          initial={reduce ? false : { opacity: 0, y: -12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.22, ease: EASE }}
          onKeyDown={onKeyDown}
        >
          <div className="flex items-center gap-3 border-b border-white/[0.07] px-4">
            <Search className="h-4 w-4 shrink-0 text-fog-dim" />
            <input
              ref={inputRef}
              // focus on mount, so keys typed right after ⌘K are not lost
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search pipelines, docs and sections…"
              className="h-14 w-full bg-transparent text-[15px] text-fog outline-none placeholder:text-fog-dim focus-visible:outline-none"
              role="combobox"
              aria-expanded="true"
              aria-controls="palette-results"
              aria-activedescendant={flat[active] ? `palette-${flat[active].id}` : undefined}
              autoComplete="off"
              spellCheck={false}
            />
            <button
              onClick={close}
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-fog-dim transition hover:bg-white/5 hover:text-fog"
              aria-label="Close search"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div ref={listRef} id="palette-results" role="listbox" className="max-h-[min(60vh,440px)] overflow-y-auto p-2">
            {flat.length === 0 && (
              <div className="px-4 py-12 text-center">
                <p className="text-sm text-fog-muted">No results for “{query}”.</p>
                <p className="mt-1 text-xs text-fog-dim">Try a pipeline name, a domain or a doc title.</p>
              </div>
            )}
            {groups.map((g) => (
              <div key={g.key} className="mb-1 last:mb-0">
                <p className="px-3 pb-1.5 pt-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-fog-dim">
                  {g.title}
                  <span className="ml-1.5 font-normal tracking-normal text-fog-dim">{g.items.length}</span>
                </p>
                {g.items.map((item) => {
                  index += 1;
                  const i = index;
                  const isActive = i === active;
                  return (
                    <button
                      key={item.id}
                      id={`palette-${item.id}`}
                      role="option"
                      aria-selected={isActive}
                      data-index={i}
                      onMouseMove={() => active !== i && setActive(i)}
                      onClick={() => go(item)}
                      className={cn(
                        "relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                        isActive ? "bg-white/[0.06]" : "hover:bg-white/[0.03]",
                      )}
                    >
                      {isActive && (
                        <motion.span
                          layoutId="palette-active"
                          className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-claw-400"
                          transition={{ duration: 0.15 }}
                        />
                      )}
                      <ItemIcon item={item} />
                      <span className="min-w-0 flex-1">
                        <span className={cn("block truncate text-sm", item.kind === "pipeline" ? "font-mono font-medium text-fog" : "text-fog")}>
                          <Highlight text={item.label} query={query} />
                        </span>
                        <span className="block truncate text-xs text-fog-dim">
                          {item.kind === "pipeline" ? item.description : item.hint}
                        </span>
                      </span>
                      {item.kind === "pipeline" && (
                        <span className="hidden shrink-0 font-mono text-[11px] text-fog-dim sm:block">{item.version}</span>
                      )}
                      <ArrowRight
                        className={cn("h-3.5 w-3.5 shrink-0 transition", isActive ? "text-claw-300 opacity-100" : "opacity-0")}
                      />
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between gap-4 border-t border-white/[0.07] px-4 py-2.5 text-[11px] text-fog-dim">
            <span className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="kbd">↑</span>
                <span className="kbd">↓</span> navigate
              </span>
              <span className="flex items-center gap-1">
                <span className="kbd">
                  <CornerDownLeft className="h-3 w-3" />
                </span>{" "}
                open
              </span>
              <span className="hidden items-center gap-1 sm:flex">
                <span className="kbd">esc</span> close
              </span>
            </span>
            <span>
              {flat.length} result{flat.length !== 1 ? "s" : ""}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
}

function ItemIcon({ item }: { item: Item }) {
  const box = "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03]";
  if (item.kind === "pipeline") {
    return (
      <span className={box}>
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
      </span>
    );
  }
  if (item.kind === "doc") {
    return (
      <span className={cn(box, "text-claw-400/80")}>
        <FileText className="h-4 w-4" />
      </span>
    );
  }
  return (
    <span className={cn(box, "text-claw-400/80")}>
      <Hash className="h-4 w-4" />
    </span>
  );
}
