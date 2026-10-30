"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

/** Write text to the clipboard, falling back to a hidden selection; resolve whether it was copied. */
async function writeClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API unavailable (insecure context) or refused: fall back to a hidden selection.
  }
  const focused = document.activeElement;
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    ta.remove();
    // Selecting moved focus to the textarea; give it back so keyboard users stay on the control.
    if (focused instanceof HTMLElement) focused.focus();
  }
}

/** Copy text to the clipboard; `copied` or `failed` stays true for a moment afterwards. */
export function useCopy(timeout = 1600) {
  const [result, setResult] = useState<"copied" | "failed" | null>(null);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const copy = useCallback(
    async (text: string) => {
      setResult((await writeClipboard(text)) ? "copied" : "failed");
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setResult(null), timeout);
    },
    [timeout],
  );
  return { copied: result === "copied", failed: result === "failed", copy };
}

/** An icon-and-label copy control whose icon swaps to a check once copied. */
export function CopyButton({
  text,
  label = "Copy",
  className,
  iconOnly = false,
}: {
  text: string;
  label?: string;
  className?: string;
  iconOnly?: boolean;
}) {
  const { copied, failed, copy } = useCopy();
  const outcome = copied ? "Copied" : failed ? "Copy failed" : null;
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        void copy(text);
      }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-fog-dim transition hover:bg-white/5 hover:text-fog",
        className,
      )}
      aria-label={outcome ?? `${label}: ${text}`}
      title={outcome ?? label}
    >
      <span className="relative inline-flex h-3.5 w-3.5">
        <AnimatePresence initial={false} mode="popLayout">
          {copied ? (
            <motion.span
              key="ok"
              initial={{ scale: 0.4, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.4, opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="absolute inset-0"
            >
              <Check className="h-3.5 w-3.5 text-claw-400" />
            </motion.span>
          ) : (
            <motion.span
              key="copy"
              initial={{ scale: 0.4, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.4, opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="absolute inset-0"
            >
              <Copy className="h-3.5 w-3.5" />
            </motion.span>
          )}
        </AnimatePresence>
      </span>
      {!iconOnly && <span aria-live="polite">{outcome ?? label}</span>}
    </button>
  );
}
