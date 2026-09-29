import { cpSync, existsSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve, sep } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const STORY_DIR = resolve(__dirname, "../story");
const TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
  ".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml",
};

/** Serves ../story at /story/ (dev and preview) and copies it into dist/story on build,
 *  so the dashboard's "Back to story" link works from one origin. */
function story(): Plugin {
  const serve = (req: { url?: string }, res: any, next: () => void) => {
    const url = (req.url ?? "").split("?")[0];
    if (url !== "/story" && !url.startsWith("/story/")) return next();
    if (url === "/story") { res.statusCode = 302; res.setHeader("Location", "/story/"); return res.end(); }
    const rel = decodeURIComponent(url.slice("/story/".length)) || "index.html";
    const file = resolve(join(STORY_DIR, rel));
    if (!file.startsWith(STORY_DIR + sep) || !existsSync(file) || !statSync(file).isFile()) return next();
    res.setHeader("Content-Type", TYPES[extname(file)] ?? "application/octet-stream");
    res.end(readFileSync(file));
  };
  return {
    name: "smaran-story",
    configureServer(s) { s.middlewares.use(serve); },
    configurePreviewServer(s) { s.middlewares.use(serve); },
    closeBundle() {
      if (existsSync(STORY_DIR)) {
        cpSync(STORY_DIR, resolve(__dirname, "dist/story"), { recursive: true, filter: (p) => !p.includes("_logo-preview") });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), story()],
  server: { port: 5173, host: "127.0.0.1" },
});
