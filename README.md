# PyAntz

**A lightweight, local-first DAG pipeline runner for small data projects.**

PyAntz lets you define data pipelines as JSON configs that reference Python functions by their import path. Run them locally with multiprocessing or submit them to a SLURM HPC cluster — no dedicated worker nodes, no infrastructure setup required.

---

## Features

- **JSON-defined pipelines** — describe your entire pipeline in a single config file
- **Local multiprocessing** — uses a SQLite-backed queue to fan out jobs across processes
- **SLURM support** — submit jobs directly to an HPC grid via `sbatch`
- **Remote execution** — run pipelines on remote SSH hosts or inside Docker/Podman containers
- **Template variables** — parameterise any field with `%{variable_name}` substitution
- **Virtual jobs** — compile-time constructs that expand into concrete jobs before execution
- **Rich built-in job library** — file operations, data analysis, subprocess dispatch, branching, loops
- **Custom jobs** — drop in any Python function decorated with `@add_parameters`
- **Optional web UI** — visual pipeline builder via the bundled FastAPI + React frontend

---

## Installation

```bash
pip install pyantz
# or with uv (recommended):
uv add pyantz
```

**Requires Python ≥ 3.14.**

---

## Quick Start

1. Save the following as `hello.json`:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/hello_pyantz"
  },
  "jobs": [
    {
      "function": "pyantz.jobs.testing.touch_file.touch_file",
      "parameters": {
        "path": "/tmp/hello_pyantz/hello.txt"
      }
    }
  ]
}
```

2. Run it:

```bash
pyantz hello.json
```

PyAntz creates `/tmp/hello_pyantz/hello.txt` and exits. That's the full cycle: config → run → done.

---

## Core Concepts

### Jobs

A **job** is the atomic unit of work. Each job has:

| Field | Required | Description |
|-------|----------|-------------|
| `function` | yes | Fully-qualified Python import path to the job function |
| `parameters` | yes | Dict of arguments passed to the function |
| `job_id` | no | Unique string identifier (auto-generated UUID if omitted) |
| `depends_on` | no | List of `job_id` values this job must wait for |
| `name` | no | Human-readable label |
| `virtual` | no | If `true`, expands at config load time; never runs directly |
| `strict` | no | If `true`, validate parameters against the function's model at startup |

Job functions must follow this signature:

```python
def my_job(params: dict | BaseModel, submit_fn: Callable) -> bool:
    ...
    return True   # True = success, False = failure
```

The `submit_fn` argument allows a job to dynamically enqueue additional jobs at runtime (used by branching and loop wrappers).

### Pipelines

A pipeline is the ordered list of jobs in the `"jobs"` array. By default jobs run in parallel whenever their dependencies are satisfied. Use `"depends_on"` to enforce ordering:

```json
"jobs": [
  {"job_id": "a", "function": "...", "parameters": {}},
  {"job_id": "b", "depends_on": ["a"], "function": "...", "parameters": {}}
]
```

Job `b` will not start until `a` succeeds.

### Variables

Any string value in `parameters` can contain `%{variable_name}` placeholders. Variables are resolved at runtime from two sources:

- **Global variables** — defined in the top-level `"variables"` field of the config
- **Inherited variables** — injected by wrapper jobs like `run_jobs_in_context`

```json
{
  "variables": {"data_dir": "/mnt/data"},
  "jobs": [
    {
      "function": "pyantz.jobs.files.simple.mkdir",
      "parameters": {"dir_path": "%{data_dir}/output"}
    }
  ]
}
```

Variables can be nested: `%{base}/%{subdir}` resolves both substitutions in sequence.

### Virtual Jobs

Virtual jobs expand at config-load time into one or more concrete jobs. They leave no footprint at runtime. The canonical example is `AddVariables`, which injects shared variables into all downstream jobs:

```json
{
  "function": "pyantz.virtual.add_variables.AddVariables",
  "virtual": true,
  "parameters": {
    "variables": {"batch_size": 64, "model": "resnet50"}
  }
}
```

When this virtual job is followed by real jobs that `depends_on` it, those real jobs receive `batch_size` and `model` in their variable scope.

### Runners

The **submitter** controls how individual jobs are dispatched:

| `type_` | Description |
|---------|-------------|
| `local_proc` | Local multiprocessing via SQLite queue |
| `slurm_sbatch` | Submit each job as an `sbatch` batch script |

### Hosts

The **host** controls where the pipeline controller itself runs before dispatching jobs:

| `type_` | Description |
|---------|-------------|
| `local` | Run controller on this machine (default) |
| `ssh` | SSH to a remote host, copy config, run pyantz there |
| `container` | Exec into a running Docker/Podman container |

---

## Security: configurations are code

A configuration names Python functions by their dotted path (`function`,
`external_function`, `setter_job`, ...) and PyAntz imports and calls them, and jobs
such as `dispatch` run arbitrary commands. Only run configurations you trust, like
you would only run a script you trust.

If configurations can come from someone else (for example through the API), restrict
what they can import with the `PYANTZ_ALLOWED_MODULES` environment variable, a comma
separated list of module prefixes:

```bash
export PYANTZ_ALLOWED_MODULES=pyantz,my_company_jobs
```

A name outside of those modules is refused before anything is imported. This limits
which functions can be named, it is not a sandbox: the allowed functions (including
`dispatch` from `pyantz`) still do whatever they do.

## Built-in Jobs Reference

### File Operations

| Function | Parameters |
|----------|------------|
| `pyantz.jobs.files.simple.copy` | `src: Path, dst: Path` |
| `pyantz.jobs.files.simple.move` | `src: Path, dst: Path` |
| `pyantz.jobs.files.simple.delete` | `path: Path, missing_ok: bool = True` |
| `pyantz.jobs.files.simple.create` | `path: Path, contents: str \| None, overwrite: bool = True` |
| `pyantz.jobs.files.simple.mkdir` | `dir_path: Path` |
| `pyantz.jobs.files.moving.rsync` | `source: Path, destination: Path` |
| `pyantz.jobs.files.moving.copy` | `source: Path, destination: Path, overwrite: bool = True` |
| `pyantz.jobs.files.moving.move` | `source: Path, destination: Path, overwrite: bool = True` |
| `pyantz.jobs.files.check.file_exists` | `file: Path` |
| `pyantz.jobs.files.check.file_contains` | `file: Path, substring: str` |
| `pyantz.jobs.files.reformat.csv_to_parquet` | `csv_file: Path, parquet_file: Path` |
| `pyantz.jobs.files.reformat.excel_to_csv` | `excel_file: Path, sheet_name: str \| None, csv_file: Path` |
| `pyantz.jobs.files.edit.edit_json` | `file: Path, updates: dict` |
| `pyantz.jobs.files.edit.edit_yaml` | `file: Path, updates: dict` |

### Data Analysis

| Function | Parameters |
|----------|------------|
| `pyantz.jobs.analysis.simple.columnar_operation` | `source_parquet_file, result_parquet_file, left_col, right_col, result_col, operation: "+"\|"-"\|"*"\|"/"` |
| `pyantz.jobs.analysis.simple.join_parquets` | `left_parquet, right_parquet, how, output_parquet, on_` |
| `pyantz.jobs.analysis.external.save_from_external_extraction` | `external_function, function_args, function_kwargs, result_parquet_location` |
| `pyantz.jobs.analysis.external.external_simple` | `external_function, function_args, function_kwargs` |
| `pyantz.jobs.analysis.external.external_analysis` | `variable_names_to_parquets, lazy_or_eager, external_function, function_args, function_kwargs` |

### Subprocess

| Function | Parameters |
|----------|------------|
| `pyantz.jobs.subproc.dispatch.dispatch` | `cmd: list[str], timeout?, cwd?, env?, stdout_file?, stderr_file?` |

### Branching

| Function | Description |
|----------|-------------|
| `pyantz.jobs.branching.if_else.if_else` | Submit one of two jobs based on a comparison |
| `pyantz.jobs.branching.if_else.conditionally_execute` | Submit a job only if a condition is true |
| `pyantz.jobs.branching.case_matrix.create_case_matrix` | Create a Parquet case matrix from variable ranges |
| `pyantz.jobs.branching.case_matrix.pipeline_expansion` | Fan out a pipeline template once per row of a case matrix |
| `pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir` | Same, plus per-run output directories |

### Wrappers

| Function | Description |
|----------|-------------|
| `pyantz.jobs.wrappers.loops.local_for_loop` | Repeat a job list N times synchronously |
| `pyantz.jobs.wrappers.variables.run_jobs_in_context` | Submit jobs with shared variables injected |
| `pyantz.jobs.wrappers.variables.set_variables` | Call a function to compute variables, then submit jobs |
| `pyantz.jobs.wrappers.variables.run_jobs_with_temp_dir` | Create a temp directory and expose its path as a variable |
| `pyantz.jobs.wrappers.submit.submit` | Re-wrap jobs under a different submitter |
| `pyantz.jobs.wrappers.submit.new_host` | Run jobs on a different host/submitter |
| `pyantz.jobs.wrappers.local.run_pipeline` | Run jobs synchronously in-process (no queue overhead) |

### Virtual Jobs

| Function | Description |
|----------|-------------|
| `pyantz.virtual.add_variables.AddVariables` | Inject shared variables into downstream jobs at compile time |

### Testing / Debugging

| Function | Description |
|----------|-------------|
| `pyantz.jobs.testing.nop.do_nothing` | No-op job, always returns success |
| `pyantz.jobs.testing.touch_file.touch_file` | Create an empty file |

---

## Writing Custom Jobs

Any Python function that returns `bool` can be a pyantz job. The recommended pattern uses `@add_parameters` to bind a Pydantic model for type-checked parameters:

```python
# myproject/jobs.py
from pydantic import BaseModel
from pyantz.infrastructure.config import add_parameters, no_submit_fn


class ProcessDataParams(BaseModel):
    input_file: str
    output_file: str
    threshold: float = 0.5


@add_parameters(ProcessDataParams)
@no_submit_fn
def process_data(params: ProcessDataParams) -> bool:
    import polars as pl
    df = pl.read_parquet(params.input_file)
    df.filter(pl.col("score") > params.threshold).write_parquet(params.output_file)
    return True
```

Reference it in your config:

```json
{
  "function": "myproject.jobs.process_data",
  "parameters": {
    "input_file": "data/raw.parquet",
    "output_file": "data/filtered.parquet",
    "threshold": 0.7
  }
}
```

Use `@no_submit_fn` when your job does not need to enqueue child jobs. Omit it (and accept the `submit_fn` argument) if your job will dynamically submit more work.

---

## CLI Reference

```bash
# Run a pipeline from a config file
pyantz config.json

# Start the development API server (see "Web UI" below)
pyantz-dev

# Start the production API server (also serves the web UI if you built it)
pyantz-prod
```

---

## Web UI

A visual pipeline builder: add jobs from a searchable list, connect them to set
dependencies, edit their parameters in forms made from their schemas, open the jobs
inside loops and branches, check the pipeline against the server, see what virtual
jobs compile to, and run it and watch each job. It reads and writes the same JSON
as `pyantz config.json` (*Import JSON* / *Export JSON*).

**Development** (two terminals):

```bash
uv run pyantz-dev                               # the api, on http://127.0.0.1:8000
cd frontend/pyantz && npm ci && npm run dev     # the UI, on http://localhost:5173
```

**Installed** (the UI is an optional feature, so a plain `pip install pyantz` stays small):

```bash
uv pip install "pyantz[frontend]"
uv run pyantz-frontend                          # the api and the UI, on http://127.0.0.1:8000
```

**One server from a checkout** (the api serves the built UI at `/`):

```bash
cd frontend/pyantz && npm ci && npm run build
PYANTZ_FRONTEND_DIR=frontend/pyantz/dist uv run pyantz-prod   # http://127.0.0.1:8000
```

The servers read their settings from the environment:

| Variable | Meaning |
| --- | --- |
| `PYANTZ_HOST`, `PYANTZ_PORT` | Where the server listens (default `127.0.0.1:8000`). A host other than localhost needs a token. |
| `PYANTZ_API_TOKEN` | If set, the api needs `Authorization: Bearer <token>`; the UI asks for it and keeps it for the tab. |
| `PYANTZ_ALLOWED_MODULES` | Comma separated module prefixes which configs may run functions from, e.g. `pyantz`. **Runs from the UI are refused until this is set**, since a config is code. |
| `PYANTZ_RUNS_DIR` | Where runs started from the UI keep their files (default: a directory in the system's temp directory). |
| `PYANTZ_FRONTEND_DIR` | The built UI (`frontend/pyantz/dist`) to serve at `/`; `pyantz-frontend` uses the installed one if this is not set. The page itself is served without the token, so that it can ask for it. |
| `PYANTZ_CORS_ORIGINS` | Origins allowed to call the api from another address. |
| `PYANTZ_API_URL` | For the Vite dev server only: where the api is, if not on port 8000. |

`pyantz-dev` does not reload when the code changes.

A run from the UI always uses a local process and a working directory chosen by the
server; the working directory in the pipeline settings is for when you run the
exported file yourself. See `frontend/pyantz/README.md` for the tests.

---

## Running on SLURM

Switch the submitter to `slurm_sbatch`:

```json
{
  "submitter": {
    "type_": "slurm_sbatch",
    "working_dir": "/scratch/myuser/pipeline_workdir",
    "max_job_time_seconds": 7200,
    "slurm_args": ["--partition=gpu", "--mem=16G", "--cpus-per-task=4"],
    "inherit_dependencies": true
  },
  "jobs": [...]
}
```

Each job is serialised to a JSON file in `working_dir` and submitted via `sbatch`. The `run.sh` entry script is bundled with pyantz and handles deserialization and execution on the compute node.

`inherit_dependencies` (default `true`) ensures that if a job dynamically submits child jobs, downstream jobs in the DAG will automatically wait for those children to complete. Set to `false` if your cluster security policy prohibits `scontrol update` after job submission.

---

## Running on a Remote SSH Host

```json
{
  "host": {
    "type_": "ssh",
    "remote_host": "login.cluster.example.com",
    "remote_user": "myuser",
    "working_dir": "/scratch/myuser/pyantz_run",
    "run_async": true
  },
  "submitter": {
    "type_": "slurm_sbatch",
    "working_dir": "/scratch/myuser/pyantz_run",
    "slurm_args": ["--partition=compute"]
  },
  "jobs": [...]
}
```

PyAntz will:
1. Connect via SSH (using system host keys; falls back to password prompt)
2. Copy the config tarball to `working_dir` on the remote
3. Run `uvx pyantz config.json` on the remote
4. Disconnect (the remote process continues independently when `run_async: true`)

---

## Running in a Docker Container

```json
{
  "host": {
    "type_": "container",
    "image": "ghcr.io/astral-sh/uv:alpine",
    "working_dir": "/workspace",
    "output_dir": "/local/results"
  },
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/workspace/queue"
  },
  "jobs": [...]
}
```

PyAntz creates a container from the image, copies the config in, runs the pipeline, and (if `output_dir` is set) copies results back to the host.

---

## Development

```bash
# Install with dev dependencies
uv sync --all-groups

# Run tests
pytest

# Run linter
ruff check src/

# Type check
mypy src/
```

Tests live in `tests/`. Integrated tests in `tests/integrated/` run actual pipelines end-to-end using the local runner. Unit tests in `tests/config/` and `tests/queue/` cover individual components.
