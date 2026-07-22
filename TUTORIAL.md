# PyAntz Tutorial

This tutorial walks through PyAntz from first install to advanced patterns. Each section builds on the last, with complete, runnable examples.

---

## 1. Installation

```bash
pip install pyantz
# or with uv (recommended for Python 3.14+):
uv add pyantz
```

Verify:

```bash
pyantz --help
```

---

## 2. Your First Pipeline

A pipeline lives in a single JSON file. The minimal structure has two required keys: `submitter` (how to run jobs) and `jobs` (what to run).

Save this as `first_pipeline.json`:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/tutorial_run"
  },
  "jobs": [
    {
      "function": "pyantz.jobs.testing.touch_file.touch_file",
      "parameters": {
        "path": "/tmp/tutorial_run/hello.txt"
      }
    }
  ]
}
```

Run it:

```bash
pyantz first_pipeline.json
```

Check the result:

```bash
ls /tmp/tutorial_run/
# hello.txt  queue.db
```

**What happened:**
- PyAntz created `/tmp/tutorial_run/` and a SQLite queue (`queue.db`) inside it.
- It started worker processes that pulled jobs from the queue.
- `touch_file` created `hello.txt`.
- When the queue was empty, all workers exited.

The `local_proc` submitter defaults to 2 worker processes. Increase with `"number_processes": 8`.

---

## 3. Working with Files

PyAntz ships with a full suite of file operation jobs. Let's build a pipeline that:
1. Creates an output directory
2. Writes a config file into it
3. Copies the config to a backup location
4. Verifies the backup exists

Save as `file_ops.json`:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/file_ops_run"
  },
  "jobs": [
    {
      "job_id": "make_dirs",
      "function": "pyantz.jobs.files.simple.mkdir",
      "parameters": {
        "dir_path": "/tmp/file_ops_run/output"
      }
    },
    {
      "job_id": "write_config",
      "depends_on": ["make_dirs"],
      "function": "pyantz.jobs.files.simple.create",
      "parameters": {
        "path": "/tmp/file_ops_run/output/config.txt",
        "contents": "key=value\nmode=production\n"
      }
    },
    {
      "job_id": "backup_config",
      "depends_on": ["write_config"],
      "function": "pyantz.jobs.files.simple.copy",
      "parameters": {
        "src": "/tmp/file_ops_run/output/config.txt",
        "dst": "/tmp/file_ops_run/output/config.bak"
      }
    },
    {
      "job_id": "verify_backup",
      "depends_on": ["backup_config"],
      "function": "pyantz.jobs.files.check.file_exists",
      "parameters": {
        "file": "/tmp/file_ops_run/output/config.bak"
      }
    }
  ]
}
```

```bash
pyantz file_ops.json
```

**Key points:**
- `"depends_on": ["make_dirs"]` ensures the directory exists before writing.
- `file_exists` returns `False` (failure) if the file is not found, which would mark that job as errored.
- Jobs without `depends_on` can run in parallel.

---

## 4. Using Variables

Hard-coding paths everywhere is fragile. Variables let you parameterise a pipeline:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/vars_run"
  },
  "variables": {
    "base_dir": "/tmp/vars_run",
    "project_name": "my_experiment"
  },
  "jobs": [
    {
      "job_id": "setup",
      "function": "pyantz.jobs.files.simple.mkdir",
      "parameters": {
        "dir_path": "%{base_dir}/%{project_name}/results"
      }
    },
    {
      "job_id": "write_marker",
      "depends_on": ["setup"],
      "function": "pyantz.jobs.files.simple.create",
      "parameters": {
        "path": "%{base_dir}/%{project_name}/results/done.txt",
        "contents": "Pipeline: %{project_name}\n"
      }
    }
  ]
}
```

`%{base_dir}` and `%{project_name}` are substituted at runtime. Change `"project_name"` once at the top and every job sees the new value.

**Variables can be nested.** If `base_dir=/data` and `project_name=exp1`, then `%{base_dir}/%{project_name}` becomes `/data/exp1`.

---

## 5. Adding Dependencies

In the examples above, `depends_on` creates a linear chain. You can also create a diamond or fan-in pattern where multiple jobs feed into one:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/deps_run",
    "number_processes": 4
  },
  "jobs": [
    {
      "job_id": "fetch_users",
      "function": "pyantz.jobs.testing.touch_file.touch_file",
      "parameters": {"path": "/tmp/deps_run/users.parquet"}
    },
    {
      "job_id": "fetch_orders",
      "function": "pyantz.jobs.testing.touch_file.touch_file",
      "parameters": {"path": "/tmp/deps_run/orders.parquet"}
    },
    {
      "job_id": "join_data",
      "depends_on": ["fetch_users", "fetch_orders"],
      "function": "pyantz.jobs.testing.nop.do_nothing",
      "parameters": {}
    }
  ]
}
```

`fetch_users` and `fetch_orders` run in parallel. `join_data` waits for **both** to complete before starting.

---

## 6. Writing a Custom Job

Built-in jobs cover common operations, but most projects need domain-specific logic. Create a Python module with your job:

```python
# myproject/jobs.py
import logging
from pathlib import Path

from pydantic import BaseModel
from pyantz.infrastructure.config import add_parameters, no_submit_fn

logger = logging.getLogger(__name__)


class WordCountParams(BaseModel):
    input_file: Path
    output_file: Path


@add_parameters(WordCountParams)
@no_submit_fn
def word_count(params: WordCountParams) -> bool:
    if not params.input_file.exists():
        logger.error("Input file not found: %s", params.input_file)
        return False

    text = params.input_file.read_text()
    count = len(text.split())
    params.output_file.write_text(str(count))
    logger.info("Word count: %d -> %s", count, params.output_file)
    return True
```

Reference it in your config:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/custom_run"
  },
  "jobs": [
    {
      "function": "myproject.jobs.word_count",
      "parameters": {
        "input_file": "/tmp/readme.txt",
        "output_file": "/tmp/custom_run/count.txt"
      }
    }
  ]
}
```

**Key rules:**
- The module must be importable (i.e., on `sys.path` or installed).
- `@add_parameters(MyModel)` validates and casts the `parameters` dict to your model at runtime.
- `@no_submit_fn` drops the `submit_fn` argument — use it when your job does not enqueue child jobs.
- Return `True` for success, `False` for failure.

If you need to submit child jobs dynamically, accept `submit_fn` as the second argument and omit `@no_submit_fn`:

```python
@add_parameters(MyParams)
def my_branching_job(params: MyParams, submit_fn) -> bool:
    child = JobConfig(function="myproject.jobs.child_job", parameters={...})
    submit_fn(child)
    return True
```

---

## 7. Conditional Branching

`if_else` submits one of two jobs based on a comparison between two values. Both sides can be template variables, enabling runtime branching:

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/branch_run"
  },
  "variables": {
    "env": "production"
  },
  "jobs": [
    {
      "function": "pyantz.jobs.branching.if_else.if_else",
      "parameters": {
        "left_side": "%{env}",
        "right_side": "production",
        "comparator": "==",
        "if_true": {
          "function": "pyantz.jobs.files.simple.create",
          "parameters": {
            "path": "/tmp/branch_run/prod_marker.txt",
            "contents": "Running in production mode"
          }
        },
        "if_false": {
          "function": "pyantz.jobs.files.simple.create",
          "parameters": {
            "path": "/tmp/branch_run/dev_marker.txt",
            "contents": "Running in dev mode"
          }
        }
      }
    }
  ]
}
```

Supported comparators: `=`, `==`, `<`, `<=`, `>`, `>=`, `!=`, `~=`

Use `conditionally_execute` if you only want the true branch and want to do nothing on false:

```json
{
  "function": "pyantz.jobs.branching.if_else.conditionally_execute",
  "parameters": {
    "left_side": "%{retry_count}",
    "right_side": "3",
    "comparator": "<",
    "if_true": {
      "function": "myproject.jobs.retry_step",
      "parameters": {}
    }
  }
}
```

---

## 8. Parameter Sweeps (Case Matrix)

Run the same pipeline template for every combination of parameters — useful for hyperparameter search, sensitivity analysis, or processing multiple datasets.

**Step 1: Create the case matrix** (a Parquet file with one row per case):

```json
{
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/sweep_run"
  },
  "jobs": [
    {
      "job_id": "make_matrix",
      "function": "pyantz.jobs.branching.case_matrix.create_case_matrix",
      "parameters": {
        "save_file": "/tmp/sweep_run/cases.parquet",
        "variables": {
          "learning_rate": {
            "range": {
              "type_": "continuous",
              "min_value": 0.001,
              "max_value": 0.01,
              "step": 0.003
            }
          },
          "batch_size": {
            "range": {
              "type_": "discrete",
              "possible_values": [32, 64, 128]
            }
          }
        }
      }
    },
    {
      "job_id": "run_sweep",
      "depends_on": ["make_matrix"],
      "function": "pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir",
      "parameters": {
        "case_matrix_parquet": "/tmp/sweep_run/cases.parquet",
        "output_dir": "/tmp/sweep_run/results",
        "pipeline_template": [
          {
            "function": "pyantz.jobs.files.simple.create",
            "parameters": {
              "path": "%{output_dir}/params.txt",
              "contents": "lr=%{learning_rate} batch=%{batch_size}"
            }
          }
        ]
      }
    }
  ]
}
```

`create_case_matrix` produces the Cartesian product of all variable ranges. With 4 learning rates and 3 batch sizes, that is 12 cases. `pipeline_expansion_with_output_dir` clones the `pipeline_template` 12 times, injects the case's values as variables, and creates a unique `output_dir` for each run.

Each child pipeline also receives a `pipeline_id` variable (0, 1, 2, …) for disambiguation.

---

## 9. Running on SLURM

To submit each job as a separate SLURM batch job, change the submitter:

```json
{
  "submitter": {
    "type_": "slurm_sbatch",
    "working_dir": "/scratch/myuser/pipeline_workdir",
    "max_job_time_seconds": 7200,
    "slurm_args": [
      "--partition=compute",
      "--mem=8G",
      "--cpus-per-task=4"
    ],
    "inherit_dependencies": true
  },
  "jobs": [
    {
      "job_id": "preprocess",
      "function": "myproject.jobs.preprocess",
      "parameters": {"input": "/scratch/data/raw.parquet"}
    },
    {
      "job_id": "train",
      "depends_on": ["preprocess"],
      "function": "myproject.jobs.train",
      "parameters": {"data": "/scratch/data/processed.parquet"}
    }
  ]
}
```

Run the controller locally — it submits the initial jobs to SLURM and exits:

```bash
pyantz slurm_pipeline.json
```

**How it works:**
- The controller resolves the dependency graph topologically and calls `sbatch` for each job in dependency order.
- Each child job receives its config as a JSON file in `working_dir`.
- SLURM's `--dependency=afterok:JOBID` enforces the DAG.
- If a job dynamically submits children (`submit_fn`), it uses `scontrol update` to add the new child as a dependency for any jobs that were waiting on the parent (controlled by `inherit_dependencies`).

**SLURM + SSH:** If your login node is remote, combine `host: ssh` with `submitter: slurm_sbatch`:

```json
{
  "host": {
    "type_": "ssh",
    "remote_host": "hpc-login.university.edu",
    "remote_user": "myuser",
    "working_dir": "/scratch/myuser/pyantz_staging",
    "run_async": true
  },
  "submitter": {
    "type_": "slurm_sbatch",
    "working_dir": "/scratch/myuser/pyantz_staging",
    "slurm_args": ["--partition=gpu", "--gres=gpu:1"]
  },
  "jobs": [...]
}
```

PyAntz SSHes in, copies the config, and runs `uvx pyantz config.json` on the login node, which then submits to SLURM.

---

## 10. Running on a Remote Host via SSH

For cases where you want to run the entire local-proc pipeline on a remote machine (rather than SLURM):

```json
{
  "host": {
    "type_": "ssh",
    "remote_host": "worker.example.com",
    "remote_user": "deploy",
    "working_dir": "/tmp/pyantz_remote",
    "run_async": false,
    "requirements": ["polars>=1.0", "scikit-learn"],
    "sync_data_at_end": true,
    "output_dir": "/local/results"
  },
  "submitter": {
    "type_": "local_proc",
    "working_directory": "/tmp/pyantz_remote/queue",
    "number_processes": 8
  },
  "jobs": [...]
}
```

**What happens:**
1. PyAntz connects to `worker.example.com` via SSH.
2. It copies a tarball containing the resolved config and `requirements.txt` to `/tmp/pyantz_remote/`.
3. It runs `uvx --with-requirements requirements.txt pyantz config.json` on the remote.
4. If `run_async: false` and `sync_data_at_end: true`, it waits for the remote pipeline to finish, then rsyncs `working_dir` back to `output_dir` on the local machine.

**Authentication:** PyAntz tries SSH keys first (via `~/.ssh/`). If that fails, it prompts for a password.

**Chaining hosts:** Use `subsequent_host` to chain hops (e.g. bastion → container):

```json
{
  "host": {
    "type_": "ssh",
    "remote_host": "bastion.corp.com",
    "working_dir": "/tmp/stage",
    "subsequent_host": {
      "type_": "container",
      "image": "myrepo/myimage:latest",
      "working_dir": "/workspace"
    }
  }
}
```

---

## What Next?

- Browse `examples/` for complete, runnable DAG configs covering common patterns.
- Read the [API docs](docs/) generated from the source.
- Open an issue or PR at the project repository if you find something missing.
