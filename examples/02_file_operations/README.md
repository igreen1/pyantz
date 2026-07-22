# File Operations

A linear pipeline that creates, copies, verifies, renames, and deletes files.

## Run it

```bash
mkdir -p /tmp/pyantz_files
pyantz pipeline.json
```

## Pipeline graph

```
make_work_dir
    └── create_source
            └── copy_source
                    └── check_backup
                            └── move_backup
                                    └── delete_source
```

## What it demonstrates

- **`depends_on`** — explicit dependency declaration creates a linear chain
- **`pyantz.jobs.files.simple.mkdir`** — create a directory tree
- **`pyantz.jobs.files.simple.create`** — write a file with string contents
- **`pyantz.jobs.files.simple.copy`** — copy a file
- **`pyantz.jobs.files.check.file_contains`** — assert a file contains a substring; the pipeline halts on failure
- **`pyantz.jobs.files.simple.move`** — rename/move a file
- **`pyantz.jobs.files.simple.delete`** — remove a file (`missing_ok: false` makes it fail if absent)
- **`number_processes: 2`** — two workers pick from the queue, but since each step depends on the previous, they effectively run in serial
