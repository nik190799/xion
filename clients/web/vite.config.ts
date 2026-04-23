import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Phase 5g-v web client Vite config.
//
// Production: `vite build` emits a static bundle into `dist/`. FastAPI
// serves it same-origin under `/app/*` via StaticFiles when the operator
// flips XION_WEB_CLIENT_ENABLED=true. No CORS.
//
// Dev: `vite dev` serves on :5173 with a proxy to the orchestrator on
// :8000. The cross-origin posture exists only on the developer's own
// machine and never ships. Every API route the client calls is listed
// here; extending the client with a new route requires extending this
// list (so the dev-mode failure is a proxy 404 on the new route, not a
// silent CORS failure against port :8000).

const API_ROUTES = ["/chat", "/drive", "/sensorium", "/health", "/pricing"];

export default defineConfig({
  plugins: [react()],
  // Same-origin production serve uses the FastAPI StaticFiles mount at
  // `/app/*`; Vite's build therefore emits assets with the `/app/` base.
  // Dev mode overrides this to `/` (below) so HMR works against the
  // Vite dev server without the `/app` prefix.
  base: "/app/",
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
    target: "es2022",
    emptyOutDir: true,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      API_ROUTES.map((route) => [
        route,
        {
          target: "http://127.0.0.1:8000",
          changeOrigin: false,
          secure: false,
        },
      ]),
    ),
  },
});
