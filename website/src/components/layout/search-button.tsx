"use client";

import { Search } from "lucide-react";
import { openPalette } from "@/components/layout/command-palette";

/** Opens the site-wide command palette. */
export function SearchButton({ className, children }: { className?: string; children?: React.ReactNode }) {
  return (
    <button type="button" onClick={openPalette} className={className}>
      <Search className="h-4 w-4" />
      {children ?? "Search"}
    </button>
  );
}
