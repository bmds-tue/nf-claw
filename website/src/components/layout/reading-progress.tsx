"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Reading progress as chapters. Every element in <main> marked `data-progress="Label"` starts a
 * chapter that runs to the next marker (the last one to the end of <main>): the home sections, a
 * pipeline page's sections, a doc's `##` headings. Each chapter is one segment of the bar and fills
 * as the reading line (a third of the way down the viewport) moves through it — the one being read
 * glows, finished ones settle to a quieter green. Hovering a segment names its chapter; clicking it
 * jumps there. A page with no markers gets a single segment for the whole page.
 *
 * Positions are read on every animation frame while scrolling (a handful of getBoundingClientRect
 * calls), so the bar follows layout changes — an expanded timeline, a collapsed parameter — for free.
 */
type Chapter = { label: string; el: Element | null };

const READING_LINE = 0.33;

export function ReadingProgress({ visible }: { visible: boolean }) {
  const pathname = usePathname();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const fills = useRef<(HTMLSpanElement | null)[]>([]);
  const reduce = useReducedMotion();

  // Collect the chapters of the page now on screen (after its content has rendered).
  useEffect(() => {
    let raf = 0;
    const collect = () => {
      const main = document.getElementById("main");
      const markers = main ? Array.from(main.querySelectorAll("[data-progress]")) : [];
      const next: Chapter[] = markers.length
        ? markers.map((el) => ({ label: el.getAttribute("data-progress") || "Section", el }))
        : [{ label: "Page", el: null }];
      setChapters((prev) =>
        prev.length === next.length && prev.every((c, i) => c.label === next[i].label && c.el === next[i].el) ? prev : next,
      );
    };
    // twice: once the route renders, and once more after late content (Markdown, reveals) settles
    raf = requestAnimationFrame(collect);
    const t = window.setTimeout(collect, 600);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(t);
    };
  }, [pathname]);

  // Fill the segments from the scroll position.
  useEffect(() => {
    if (!chapters.length) return;
    let raf = 0;
    const update = () => {
      raf = 0;
      const main = document.getElementById("main");
      const vh = window.innerHeight;
      const line = vh * READING_LINE;
      const maxScroll = document.documentElement.scrollHeight - vh;
      const atEnd = window.scrollY >= maxScroll - 2;
      const mainBottom = main ? main.getBoundingClientRect().bottom : document.documentElement.scrollHeight;

      const fractions = chapters.map((c, i) => {
        if (atEnd) return 1;
        if (!c.el) return maxScroll > 0 ? Math.min(1, window.scrollY / maxScroll) : 1;
        const start = c.el.getBoundingClientRect().top;
        const nextEl = chapters[i + 1]?.el;
        const end = nextEl ? nextEl.getBoundingClientRect().top : mainBottom;
        return Math.max(0, Math.min(1, (line - start) / Math.max(1, end - start)));
      });
      const active = fractions.findIndex((f) => f > 0 && f < 1);
      fractions.forEach((f, i) => {
        const el = fills.current[i];
        if (!el) return;
        el.style.width = `${f * 100}%`;
        el.dataset.state = i === active ? "active" : f >= 1 ? "done" : "idle";
      });
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(raf);
    };
  }, [chapters]);

  const jump = (c: Chapter) => {
    const behavior = reduce ? "auto" : "smooth";
    if (c.el) (c.el as HTMLElement).scrollIntoView({ behavior, block: "start" });
    else window.scrollTo({ top: 0, behavior });
  };

  return (
    <div
      aria-hidden
      className={cn(
        "absolute inset-x-0 -bottom-px transition-opacity duration-500",
        visible ? "opacity-100" : "pointer-events-none opacity-0",
      )}
    >
      <div className="container-site flex gap-1.5">
        {chapters.map((c, i) => (
          <button
            key={`${c.label}-${i}`}
            type="button"
            tabIndex={-1}
            onClick={() => jump(c)}
            className="group/seg relative -mb-3 h-[14px] min-w-0 flex-1 cursor-pointer"
          >
            {/* track */}
            <span className="absolute inset-x-0 top-0 h-[2px] rounded-full bg-white/[0.07] transition-[height,background-color] duration-200 group-hover/seg:h-[4px] group-hover/seg:bg-white/[0.12]">
              {/* fill — width and state are set per frame */}
              <span
                ref={(el) => {
                  fills.current[i] = el;
                }}
                data-state="idle"
                className={cn(
                  "absolute inset-y-0 left-0 w-0 rounded-full bg-claw-500/45",
                  "data-[state=active]:bg-claw-400 data-[state=active]:shadow-[0_0_10px_0_rgba(57,211,83,0.55)]",
                  // the glowing head of the chapter being read
                  "after:absolute after:right-0 after:top-1/2 after:h-[6px] after:w-[6px] after:-translate-y-1/2 after:translate-x-1/2 after:rounded-full after:bg-claw-200 after:opacity-0 after:shadow-[0_0_8px_2px_rgba(57,211,83,0.75)] after:transition-opacity after:duration-300",
                  "data-[state=active]:after:opacity-100",
                  !reduce && "transition-[width,background-color] duration-150 ease-out",
                )}
              />
            </span>
            {/* the chapter's name, under the bar on hover */}
            <span
              className={cn(
                "pointer-events-none absolute top-3 max-w-[min(22rem,80vw)] truncate whitespace-nowrap",
                i < chapters.length / 2 ? "left-0" : "right-0",
                "rounded-md border border-white/10 bg-ink-900/95 px-2 py-1 text-[11px] font-medium text-fog-muted opacity-0 shadow-[0_8px_24px_-8px_rgba(0,0,0,0.9)] backdrop-blur transition-[opacity,transform] duration-200 group-hover/seg:translate-y-0.5 group-hover/seg:opacity-100",
              )}
            >
              <span className="mr-1.5 font-mono text-fog-dim">{String(i + 1).padStart(2, "0")}</span>
              {c.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
