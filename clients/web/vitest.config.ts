import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Separate Vitest config so the vite / vitest type-hierarchy mismatch
// doesn't force @ts-ignores in vite.config.ts. This file is only
// consulted by `npm test` and `npm run test:watch`; `vite build` and
// `vite dev` do not read it.

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
