# PyAntz web UI

A React + TypeScript + Vite app to build a pyantz pipeline as a graph of jobs.
It talks to the FastAPI backend in `src/pyantz/api` (started by `pyantz-dev`).

## Running it

```bash
# terminal 1, from the repository root: the API (http://127.0.0.1:8000)
uv run pyantz-dev

# terminal 2, from this directory: the UI (http://localhost:5173)
npm ci
npm run dev
```

Vite proxies `/api` to the API. If the API listens elsewhere (`PYANTZ_PORT`,
`PYANTZ_HOST`), tell Vite where with `PYANTZ_API_URL`:

```bash
PYANTZ_PORT=9000 uv run pyantz-dev
PYANTZ_API_URL=http://127.0.0.1:9000 npm run dev
```

## Checks

| Command             | What it does                                                |
| ------------------- | ----------------------------------------------------------- |
| `npm run lint`      | ESLint (CI should use `-- --max-warnings=0`)                |
| `npm run typecheck` | TypeScript, including the e2e tests                         |
| `npm test`          | Vitest unit and component tests (jsdom)                     |
| `npm run e2e`       | Playwright against a real `pyantz-dev` and Vite (see below) |
| `npm run build`     | Typecheck and production build into `dist/`                 |

### End to end tests

`npm run e2e` starts the servers itself, so nothing needs to be running. Each
Playwright project has its own: `main` (plain), `auth` (the api wants a token),
`runs` (runs are allowed) and `prod` (`pyantz-prod` serving the built UI). They
listen on ports 8123 to 8126, on purpose not the default. The first time, install the browser and the
system libraries it needs:

```bash
npx playwright install chromium
npx playwright install-deps chromium   # Linux; uses sudo
```

## Layout

- `src/components` — the board, node cards, palette, inspector, panels
- `src/store` — Redux Toolkit slices (graph with undo and nesting, jobs, schemas, validation, compile, run, auth, ui)
- `src/model` — logic with no React in it: config ⇄ graph conversion (`convert.ts`), which parameters are jobs (`classify.ts`), checking parameters (`validate.ts`), layout. `convert.ts` and what it imports run under plain `node` too, which the python tests use.
- `src/hooks` — validation, run polling, shortcuts, adding jobs
- `src/services` — the axios client (token, base url), files, session storage
- `src/__fixtures__` — the example configs and `job-schemas.json`, a dump of every job's schema (regenerate with `uv run python -m pyantz.api.dump_schemas frontend/pyantz/src/__fixtures__/job-schemas.json`; a python test fails when it is stale)
- `scripts` — run by the python tests with node
- `e2e` — Playwright tests
- `src/theme.ts` — light or dark, following the browser (`prefers-color-scheme`). Colours come from Bootstrap's variables (`var(--bs-body-bg)`, ...), which follow `data-bs-theme`; don't hard-code colours in CSS

## How the editor keeps a pipeline

The graph is the source of truth. A job's dependencies are the edges of its level,
and nothing else. Parameters which are jobs (loops, `if_else`, ...) are found from
the job's schema and kept as levels of their own, which the board opens like folders;
everything else is in `parameters` as it was in the config. Keys the editor does not
know are kept, so opening and exporting a config loses nothing.

Exports can carry the positions of the jobs under `x-pyantz-ui`, which `pyantz`
ignores (a python test pins that).

The plan this was built from, with the findings and what is left, is in
[`PLAN-frontend.md`](../../PLAN-frontend.md) at the repository root.
