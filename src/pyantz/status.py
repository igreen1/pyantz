"""Show the progress of a run: ``pyantz-status <working directory>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

QUEUE_FILE_NAME = "queue.db"
"""Name of the queue file the local runner keeps in its working directory."""


def describe_run(working_directory: Path) -> str:
    """Summarize the queue of the run in *working_directory*.

    Args:
        working_directory: the working directory of a local run.

    Returns:
        str: the number of jobs in each status, and the ids of the failed jobs.

    Raises:
        FileNotFoundError: if the directory has no queue (no run was started there)

    Example:
        .. testsetup:: status-describe

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: status-describe

            from pathlib import Path

            from pyantz import start
            from pyantz.status import describe_run

            start(
                {
                    "submitter": {"type_": "local_proc", "working_directory": "run"},
                    "jobs": [
                        {
                            "job_id": "check",
                            "function": "pyantz.jobs.files.check.file_exists",
                            "parameters": {"file": "missing.txt"},
                        },
                    ],
                }
            )
            print(describe_run(Path("run")))

        .. testoutput:: status-describe

            Jobs: 1
              succeeded: 0
              failed:    1
              running:   0
              ready:     0
              waiting:   0
            Failed jobs:
              check

        .. testcleanup:: status-describe

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    queue_file = working_directory / QUEUE_FILE_NAME
    if not queue_file.is_file():
        msg = f"No run found: {queue_file} does not exist"
        raise FileNotFoundError(msg)

    with SqliteQueue(queue_file) as queue:
        report = queue.get_jobs_report()
        failed = queue.get_job_ids_with_status(JobStatus.ERROR)
    lines = [
        f"Jobs: {report.total}",
        f"  succeeded: {report.success}",
        f"  failed:    {report.error}",
        f"  running:   {report.running}",
        f"  ready:     {report.ready}",
        f"  waiting:   {report.pending}",
    ]
    if failed:
        lines.append("Failed jobs:")
        lines.extend(f"  {job_id}" for job_id in failed)
    return "\n".join(lines)


def main() -> None:
    """Entry point of ``pyantz-status``.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: with status 1 if the directory has no run, 2 if the
            arguments are invalid.

    """
    parser = argparse.ArgumentParser(
        "pyantz-status",
        description="Show how far a pipeline has got.",
    )
    parser.add_argument("working_directory", help="working directory of the run")
    args = parser.parse_args()

    try:
        print(describe_run(Path(args.working_directory)))  # noqa: T201
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
