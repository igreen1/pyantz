# Hello World

The simplest possible pyantz pipeline: a single job that touches a file.

## Run it

```bash
mkdir -p /tmp/pyantz_hello_world
pyantz pipeline.json
```

After running, `/tmp/pyantz_hello_world/hello.txt` will exist.

## What it demonstrates

- Minimal `InitialConfig` structure: `submitter` + `jobs`
- The `local_proc` submitter with one worker process
- A single job identified by `job_id` and referencing a built-in function
- How parameters are passed as a plain dict
