// Test the production static export with the same project base path as Pages.
import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";

const root = path.resolve("out");
const base = process.env.TEST_BASE_PATH ?? "/nf-claw";
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain", ".woff2": "font/woff2" };
await fs.access(path.join(root, "index.html"));
const server = http.createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    if (pathname !== base && !pathname.startsWith(base + "/")) throw new Error("outside base path");
    let target = path.resolve(root, "." + (pathname.slice(base.length) || "/"));
    if (target !== root && !target.startsWith(root + path.sep)) throw new Error("outside export");
    if ((await fs.stat(target)).isDirectory()) target = path.join(target, "index.html");
    response.writeHead(200, { "Content-Type": types[path.extname(target)] || "application/octet-stream", "Cache-Control": "no-store" });
    response.end(await fs.readFile(target));
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain" });
    response.end("Not found");
  }
});
server.listen(Number(process.env.PORT || 4177), "127.0.0.1");
process.on("SIGTERM", () => server.close(() => process.exit(0)));
