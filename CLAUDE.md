# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

PyAntz is a local-first DAG pipeline runner. Pipelines are JSON/dict configs whose jobs reference Python functions by import path. They run via local multiprocessing (SQLite-backed queue) or SLURM `sbatch`, optionally on a remote host (SSH or Docker/Podman container). Requires Python >= 3.13 (uses PEP 695 syntax such as `def f[T: ...]`); development defaults to 3.14 (`.python-version`). Package manager is `uv`; source is in `src/pyantz`.

## Commands

```bash
uv sync                                   # install deps (incl. dev group)
uv run pytest                             # full test suite
uv run pytest tests/jobs/test_x.py::test_name   # single test
uv run pytest -n auto                     # parallel (pytest-xdist)
uv run ruff format                        # format (enforced by tests/test_formatting.py)
uv run ruff check                         # lint (select = ALL, see pyproject.toml)
uv run ty check                           # primary type checker; get this passing first
uv run mypy src                           # secondary type checker; run once ty passes
make test                                 # sphinx doctests (docs/) + pytest
make doc                                  # build sphinx html docs
cd frontend/pyantz && npm run dev -- --host   # web UI (React/Vite); API via `pyantz-dev` / `pyantz-prod`
make frontend-check                       # web UI: lint, typecheck, unit tests, build
make e2e                                  # web UI: Playwright tests against real servers
make frontend-bundle                      # build the UI into packages/pyantz-frontend (for `pyantz-frontend` in a checkout)
uv run pytest tests/frontend              # the UI's model agrees with the python models (needs node >= 22.18)
```

Entry points: `pyantz <config.json>`, `pyantz-status`, `pyantz-dev`, `pyantz-prod`, `pyantz-frontend` (api + built UI; needs the `frontend` extra).

Pytest markers `docker`, `ssh`, `slow` mark tests that need a docker daemon / ssh server / long runtime (skipped when unavailable). `tests/` also contains meta-tests: formatting (ruff), spelling (codespell), and job registration (checks in a fresh interpreter that `import pyantz.jobs` registers everything and has no circular imports). Docstrings in `src` are executed as Sphinx doctests (`.. testcode::`), so keep them runnable.

## Architecture

Flow: `pyantz.start(config)` (`infrastructure/runner/starter.py`) validates into `InitialConfig` and routes on `host.type_` (local / ssh / container) then `submitter.type_` (`local_proc` / `slurm_sbatch`).

- **`infrastructure/config/`** — pydantic models. `InitialConfig` (`initial.py`) is the root: jobs + submitter + host + variables. Its `jobs` validator `make_and_compile` builds typed job configs, then runs `infrastructure/virtual/compile.py` to expand *virtual jobs* (compile-time constructs) into concrete jobs. `graph_validation.py` checks the job dependency graph. `runners/` holds submitter configs; `host_config.py` holds host configs.
- **Job registry** — `parameters/decorators.py` provides `@add_parameters` (and `no_submit_fn`), which registers a job function into the global `PYANTZ_REGISTERED_FUNCTION` and ties it to a pydantic parameters model; `compile_check.py` validates params at compile time. Jobs are referenced in configs by full import path, and the registry is only populated when the module is imported — hence `pyantz/jobs/__init__.py` must import every job module (tests enforce this).
- **`infrastructure/runner/`** — `local/` (multiprocessing runner), `slurm/` (sbatch submission), `_remotes/` (ssh, container, file transfers), `job_manager.py`.
- **`infrastructure/distributed_queue/`** — queue interface (`common/`) with a SQLAlchemy/SQLite implementation (`sql/`) used for job fan-out and status; `JobsReport` return types live in `common/return_types.py`.
- **`jobs/`** — built-in job library grouped by area (`files`, `analysis`, `branching`, `subproc`, `wrappers` for loop/submit, `testing`). Jobs receive their params plus a submit function so they can enqueue follow-on jobs.
- **`virtual/`** — built-in virtual job definitions (e.g. `add_variables`). Configs support `%{var}` template substitution.
- **`api/`** — FastAPI backend for the optional web UI; `frontend/pyantz` is the React app (see its README). `PYANTZ_FRONTEND_DIR` makes the server serve the built app. The `frontend` extra (`pyantz[frontend]`) pulls in `pyantz-frontend`, a second distribution in `packages/pyantz-frontend` (uv workspace member) whose hatch build hook runs `npm run build` and ships the result; `pyantz-frontend` (`api/frontend_server.py`) serves it. `make build` builds both; the versions move together via bumpver. `python -m pyantz.api.dump_schemas` regenerates `frontend/pyantz/src/__fixtures__/job-schemas.json`, which a test checks. The UI's `src/model/types.ts` lists the config fields and `tests/frontend` compares them with the pydantic models: change both when you add a field.

Note: both `config/abstract_job.py` and `config/abtrast_job.py` exist; import `AbstractJobConfig` from `abstract_job`.

## Conventions

- Ruff runs with `select = ["ALL"]` (ignoring D203, D213, COM812): all public code needs Google-style docstrings and full type hints; asserts are only allowed under `tests/`. Imports used only for typing go under `TYPE_CHECKING` (pydantic models are treated as runtime-evaluated).
- Docstrings (Google style, `convention = "google"`): every function has `Args`, `Returns` and `Raises` sections; job functions also list their parameters model's fields under `Parameters` (napoleon custom section, shown as "Job parameters"); fields and constants get attribute docstrings. Examples are `.. testcode::`/`.. testoutput::` blocks in a named group, with a hidden `testsetup` that `chdir`s into a temp dir, because `make test` runs them all (private members too). Don't put examples in pydantic model class docstrings (pydantic copies them into the JSON schemas the API serves; put them in the module docstring), and FastAPI endpoints keep `\f` after their summary so the rest stays out of the OpenAPI description. Changing a job's first docstring paragraph or a parameters model's docstring changes `job-schemas.json`: regenerate it.
- Code must run on Python 3.13: every module starts with `from __future__ import annotations` (ruff `required-imports` adds it) because 3.13 has no deferred annotations (PEP 649); no 3.14-only syntax such as unparenthesized `except A, B` (PEP 758) or modules such as `annotationlib`. To test on 3.13: `UV_PROJECT_ENVIRONMENT=.venv-3.13 uv run --python 3.13 pytest`.
- Version lives in `src/pyantz/__init__.py` and `pyproject.toml`, bumped via `bumpver` (`make build`) — don't edit by hand.
- More user-facing docs: `README.md`, `TUTORIAL.md`, `docs/source`.
