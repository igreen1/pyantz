# pyantz Examples

Each subdirectory is a self-contained example with a `pipeline.json` and a `README.md` explaining what it demonstrates.

## Quick index

| Directory | What it shows |
|-----------|---------------|
| [`01_hello_world`](01_hello_world/) | Minimal single-job pipeline |
| [`02_file_operations`](02_file_operations/) | Copy, move, verify, delete files in a linear chain |
| [`03_data_analysis`](03_data_analysis/) | Parallel CSV→Parquet conversion, join, and columnar operation |
| [`04_conditional_branching`](04_conditional_branching/) | `if_else` and `conditionally_execute` for runtime routing |
| [`05_parameter_sweep`](05_parameter_sweep/) | Cartesian-product sweep over hyperparameters with `create_case_matrix` + `pipeline_expansion_with_output_dir` |
| [`06_subprocess`](06_subprocess/) | Run shell commands with `dispatch`; capture stdout/stderr |
| [`07_variables`](07_variables/) | Global variables, `run_jobs_in_context`, and the `AddVariables` virtual job |
| [`08_slurm`](08_slurm/) | Submit to a SLURM HPC grid with dependency inheritance |
| [`09_remote_ssh`](09_remote_ssh/) | Run the controller on a remote machine via SSH |
| [`10_custom_jobs`](10_custom_jobs/) | Write and use your own `@add_parameters` job functions |

## Running an example

```bash
# From the repo root
pyantz examples/01_hello_world/pipeline.json
```

Some examples require setup steps (creating sample data, adjusting paths). Check the `README.md` in each directory.

## Building on the examples

1. Copy the closest example to your project
2. Replace the `working_directory` / `working_dir` paths
3. Swap in your own job functions and parameters
4. Adjust `number_processes` or switch to `slurm_sbatch` as needed
