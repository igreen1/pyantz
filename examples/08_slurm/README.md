# SLURM HPC Pipeline

Run a multi-stage pipeline on a SLURM cluster, with parallel preprocessing and dependency-aware job submission.

## Prerequisites

- Access to a SLURM cluster with `sbatch`, `squeue`, and `scontrol` in `$PATH`
- pyantz installed in the environment used for job scripts
- Adjust paths (`/scratch/myuser/...`) and SLURM args for your cluster

## Run it

From a login node or compute node with SLURM access:

```bash
pyantz pipeline.json
```

pyantz submits the initial jobs with `sbatch` (resolving the dependency graph up front), then each job submits its children when it runs.

## Pipeline graph

```
setup
├── preprocess_a ──┐
└── preprocess_b ──┤
                   └── merge
                         └── train_model
```

`preprocess_a` and `preprocess_b` run as independent SLURM jobs in parallel.

## Key SLURM configuration

### `slurm_args`

Passed verbatim to `sbatch`. Use these for resource requests:

```json
"slurm_args": [
  "--partition=gpu",
  "--gres=gpu:1",
  "--cpus-per-task=8",
  "--mem=32G",
  "--account=myproject"
]
```

### `max_job_time_seconds`

Global wall-time limit applied to every job. Slurm will kill jobs that exceed this.

### `inherit_dependencies`

When `true` (default), if job A depends on job B and B dynamically submits B1 and B2, then A will be updated to also depend on B1 and B2.  This ensures correct ordering even for dynamic pipelines.

Set to `false` if your cluster security policy forbids `scontrol update` on running jobs.

### `working_dir`

All job config JSON files are staged here. Must be accessible from all compute nodes (use a shared filesystem like `/scratch`).

## Running the controller remotely

You can also start the pipeline from your laptop and have it run entirely on the cluster:

```json
{
  "host": {
    "type_": "ssh",
    "remote_host": "cluster.example.com",
    "remote_user": "myuser",
    "working_dir": "/scratch/myuser/pyantz_ctrl",
    "run_async": true
  },
  "submitter": {
    "type_": "slurm_sbatch",
    "working_dir": "/scratch/myuser/pyantz_slurm"
  },
  "jobs": [...]
}
```
