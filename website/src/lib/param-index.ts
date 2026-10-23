"use client";

import { useEffect, useState } from "react";
import type { ParamIndex } from "@/lib/derive";
import { BASE_PATH } from "@/lib/site";

let request: Promise<ParamIndex> | null = null;

function load(): Promise<ParamIndex> {
  request ??= fetch(`${BASE_PATH}/search/params.json`)
    .then((r) => {
      if (!r.ok) throw new Error(`params index: HTTP ${r.status}`);
      return r.json() as Promise<ParamIndex>;
    })
    .catch((e) => {
      request = null; // let a later search try again
      throw e;
    });
  return request;
}

/**
 * The every-pipeline parameter index, fetched once — when `enabled` first turns true (a search
 * starts, or the search box gains focus) — and shared by every caller after that.
 */
export function useParamIndex(enabled: boolean): { index: ParamIndex | null; failed: boolean } {
  const [index, setIndex] = useState<ParamIndex | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!enabled || index) return;
    let live = true;
    load()
      .then((i) => live && (setIndex(i), setFailed(false)))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [enabled, index]);
  return { index, failed };
}
