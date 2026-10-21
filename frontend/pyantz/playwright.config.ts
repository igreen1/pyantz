import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, type PlaywrightTestConfig } from "@playwright/test";

type WebServers = Extract<
  NonNullable<PlaywrightTestConfig["webServer"]>,
  unknown[]
>;

// The apis deliberately listen on ports other than the default, so the tests fail
// if the frontend assumes port 8000. Each flavour of server has an api and a UI:
//   main  - plain: no token, and runs are switched off
//   runs  - runs are allowed
//   auth  - the api wants a token
const SERVERS: Record<
  string,
  { api: number; ui: number; env: Record<string, string> }
> = {
  main: { api: 8123, ui: 5174, env: {} },
  auth: { api: 8124, ui: 5175, env: { PYANTZ_API_TOKEN: "e2e-secret" } },
  runs: {
    api: 8125,
    ui: 5176,
    env: {
      PYANTZ_ALLOWED_MODULES: "pyantz",
      PYANTZ_RUNS_DIR: join(tmpdir(), "pyantz-e2e-runs"),
    },
  },
};

// The production way: one server, which has the built UI as well as the api
const PROD_PORT = 8126;

export const API_URL = (name: "main" | "auth" | "runs") =>
  `http://127.0.0.1:${SERVERS[name].api}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  timeout: 60_000,
  use: { trace: "retain-on-failure" },
  projects: [
    {
      name: "main",
      testMatch: /(smoke|editing|nested|checks|norun|theme)\.spec\.ts/,
      use: { baseURL: `http://127.0.0.1:${SERVERS.main.ui}` },
    },
    {
      name: "auth",
      testMatch: /auth\.spec\.ts/,
      use: { baseURL: `http://127.0.0.1:${SERVERS.auth.ui}` },
    },
    {
      name: "prod",
      testMatch: /prod\.spec\.ts/,
      use: { baseURL: `http://127.0.0.1:${PROD_PORT}` },
    },
    {
      name: "runs",
      testMatch: /runs\.spec\.ts/,
      use: { baseURL: `http://127.0.0.1:${SERVERS.runs.ui}` },
    },
  ],
  webServer: [
    {
      // builds the ui, and serves it with the api as `pyantz-prod` does
      command: "npm run build && cd ../.. && uv run pyantz-prod",
      env: {
        PYANTZ_PORT: String(PROD_PORT),
        PYANTZ_FRONTEND_DIR: join(import.meta.dirname, "dist"),
      },
      url: `http://127.0.0.1:${PROD_PORT}/`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    ...allServers(),
  ],
});

function allServers(): WebServers {
  return Object.values(SERVERS).flatMap(({ api, ui, env }): WebServers => [
    {
      command: "uv run pyantz-dev",
      cwd: "../..",
      env: { PYANTZ_PORT: String(api), ...env },
      url: `http://127.0.0.1:${api}/docs`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${ui} --strictPort`,
      env: { PYANTZ_API_URL: `http://127.0.0.1:${api}` },
      url: `http://127.0.0.1:${ui}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ]);
}
