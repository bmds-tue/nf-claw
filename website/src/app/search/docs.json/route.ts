import { getDocs } from "@/lib/data";
import { buildDocSearch } from "@/lib/doc-search";

export const dynamic = "force-static";
export function GET() { return Response.json(buildDocSearch(getDocs())); }
