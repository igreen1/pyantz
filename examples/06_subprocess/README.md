# Subprocess Dispatch

Run shell commands and external programs as pipeline jobs.

## Run it

```bash
mkdir -p /tmp/pyantz_subprocess
pyantz pipeline.json
```

Output files appear in `/tmp/pyantz_subprocess/`:
- `ls_output.txt` — directory listing of `/tmp`
- `count_output.txt` — number of files in `/tmp`
- `python_output.txt` — timestamp from the Python one-liner

## Pipeline graph

```
setup
├── list_tmp     ──> check_list_output
├── count_files
└── python_script
```

The three dispatch jobs run in parallel (no dependency between them beyond `setup`).

## What it demonstrates

- **`pyantz.jobs.subproc.dispatch.dispatch`** — wraps `subprocess.run`
- **`cmd`** — list of strings; the first element is the executable
- **`stdout_file` / `stderr_file`** — capture output to files instead of losing it
- **`timeout`** — kill and fail the job if it runs longer than N seconds
- **Shell features** — use `["bash", "-c", "..."]` to run shell pipelines (`|`, `&&`, etc.)
- **`cwd`** — (not shown) set the working directory for the subprocess
- **`env`** — (not shown) replace the subprocess's environment entirely

## Integrating with existing scripts

```json
{
  "function": "pyantz.jobs.subproc.dispatch.dispatch",
  "parameters": {
    "cmd": ["python", "my_script.py", "--config", "%{config_file}"],
    "cwd": "%{project_dir}",
    "stdout_file": "%{output_dir}/stdout.log",
    "stderr_file": "%{output_dir}/stderr.log",
    "timeout": 3600
  }
}
```
