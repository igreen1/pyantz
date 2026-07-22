# Remote SSH Execution

Run the entire pipeline controller on a remote machine, connecting via SSH.

## How it works

1. pyantz connects to `remote_host` via SSH (using keys, falling back to password)
2. Bundles the resolved config into a tar archive and copies it via SFTP
3. Runs `uvx pyantz config.json` on the remote host
4. The remote host then runs the pipeline with a `local_proc` submitter

## Configuration

Update `pipeline.json` with your actual host and user:

```json
"host": {
  "type_": "ssh",
  "remote_host": "remote.example.com",
  "remote_user": "myuser",
  "working_dir": "/tmp/pyantz_remote"
}
```

## Run it

```bash
pyantz pipeline.json
```

If SSH key auth is not configured, you will be prompted for a password.

## What it demonstrates

### `run_async: false`
The local pyantz process waits for the remote command to complete before exiting.  Set to `true` to fire-and-forget (uses `nohup ... &`).

### `sync_data_at_end`
When `true` (requires `run_async: false`), rsyncs the remote `working_dir` back to `output_dir` on the local machine after the pipeline finishes. Requires `output_dir` to be set.

### `subsequent_host`
After reaching the remote machine, `subsequent_host` controls how jobs are actually run there. In this example it's `local` (the default). You could chain further to a container or another SSH hop.

### Copying project code

If your jobs reference local Python code not installed on the remote, set `copy_project_dir: true`. This tars up the current pyantz project directory and copies it to the remote.

```json
"host": {
  "type_": "ssh",
  "remote_host": "remote.example.com",
  "working_dir": "/tmp/pyantz_remote",
  "copy_project_dir": true,
  "requirements": ["numpy", "polars"]
}
```

### Container example

To run inside a Docker container instead:

```json
"host": {
  "type_": "container",
  "image": "python:3.14-slim",
  "name": "pyantz_run",
  "working_dir": "/workspace"
}
```
