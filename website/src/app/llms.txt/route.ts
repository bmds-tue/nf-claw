import { readText } from "@/lib/data/paths";

// The repository's own llms.txt, served at the site root (where the llms.txt convention looks for
// it) from the same file at build time, so the site never holds a second copy to keep in sync.
export const dynamic = "force-static";

export function GET() {
  const text = readText("llms.txt");
  if (text === null) throw new Error("llms.txt is missing from the repository root");
  return new Response(text, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
