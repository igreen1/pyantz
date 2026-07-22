# Variables

Three ways to inject variables into a pipeline.

## Run it

```bash
mkdir -p /tmp/pyantz_variables
pyantz pipeline.json
```

## What it demonstrates

### 1. Global variables (top-level `variables` field)

```json
{
  "variables": {"project": "my_analysis", "version": "v1"},
  "jobs": [...]
}
```

All jobs see `%{project}` and `%{version}` automatically.  Variables can be composed: `%{base_dir}/%{project}/%{version}` resolves to a full path.

### 2. `run_jobs_in_context` — scoped variables for a group of jobs

```json
{
  "function": "pyantz.jobs.wrappers.variables.run_jobs_in_context",
  "parameters": {
    "shared_variables": {"experiment": "baseline", "seed": "42"},
    "jobs": [...]
  }
}
```

The inner jobs see both global variables AND `experiment` / `seed`.  Jobs outside the wrapper cannot see the scoped variables.

### 3. `AddVariables` — virtual job that injects into downstream jobs

```json
{
  "function": "pyantz.virtual.add_variables.AddVariables",
  "virtual": true,
  "parameters": {"variables": {"run_id": "run_001"}}
}
```

`AddVariables` is a **virtual job** — it compiles away at startup and leaves no footprint at runtime.  Any job that `depends_on` `add_variables_virtual` (directly or transitively) will receive the injected variables.

## Variable syntax

- **Template**: `%{variable_name}` in any string parameter value
- **Nesting**: variables can reference other variables: `%{base_dir}/%{project}` resolves iteratively
- **Scope**: child jobs inherit parent variables; locally defined variables shadow globals
- **Missing variables**: left as-is at runtime (the literal `%{name}` string remains)
