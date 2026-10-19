# Parameter Sweep (Case Matrix)

Run a pipeline once for every combination of hyperparameters using a case matrix.

## Run it

```bash
mkdir -p /tmp/pyantz_sweep
pyantz pipeline.json
```

After running, `/tmp/pyantz_sweep/runs/` will contain one `run_N/` directory per parameter combination, each holding a `params.txt` file showing which hyperparameters were used.

With `learning_rate` at 3 values and `batch_size` at 3 values, you get **9 runs** in total (the cartesian product).

## Pipeline graph

```
setup
  └── create_matrix
          └── run_sweep  ──> [run_0/params.txt]
                         ──> [run_1/params.txt]
                         ──> ...
                         ──> [run_8/params.txt]
```

## What it demonstrates

- **`create_case_matrix`** — generates the cartesian product of parameter ranges and saves to Parquet
  - `ContinuousRange` — arange-style: `min_value`, `max_value`, `step`
  - `DiscreteRange` — explicit list of values
- **`pipeline_expansion_with_output_dir`** — reads the matrix Parquet and submits one copy of `pipeline_template` per row; injects:
  - Each column value as a variable (e.g., `%{learning_rate}`, `%{batch_size}`)
  - `%{pipeline_id}` — a unique integer per run
  - `%{output_dir}` — a unique subdirectory under `output_dir`
- **`pipeline_template`** — a list of job configs that get cloned with fresh UUIDs for each run
- With `number_processes: 4`, up to 4 parameter combinations run in parallel

## Replacing the template

Swap the `pipeline_template` steps with your actual workload (model training script, simulation dispatch, etc.):

```json
"pipeline_template": [
  {
    "function": "pyantz.jobs.subproc.dispatch.dispatch",
    "parameters": {
      "cmd": ["python", "train.py",
              "--lr", "%{learning_rate}",
              "--batch", "%{batch_size}",
              "--outdir", "%{output_dir}"],
      "stdout_file": "%{output_dir}/stdout.log"
    }
  }
]
```
