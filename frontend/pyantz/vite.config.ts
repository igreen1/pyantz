import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Where the pyantz API server (`pyantz-dev`) listens; matches PYANTZ_HOST/PORT
const apiTarget = process.env.PYANTZ_API_URL ?? "http://127.0.0.1:8000";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // The API serves everything under /api/v1.0, so forward as is
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // Explicitly include ajv and the 2019-09 distribution
    include: ["ajv", "ajv/dist/2019.js"],
  },
  build: {
    commonjsOptions: {
      // Ensure CommonJS modules are transformed properly
      include: [/node_modules/],
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/__fixtures__/**",
        "src/main.tsx",
      ],
      reporter: ["text-summary", "text"],
      thresholds: { statements: 90, lines: 90, branches: 85, functions: 85 },
    },
  },
});
