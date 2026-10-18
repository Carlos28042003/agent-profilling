import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `npm run build` writes the static site to ../docs, which GitHub Pages serves and the
// backend's `agentic-ui` server also serves. In `npm run dev`, /api goes to the backend.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  build: { outDir: "../docs", emptyOutDir: true },
  server: { proxy: { "/api": "http://localhost:8000" } },
});
