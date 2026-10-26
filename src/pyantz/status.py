"""Show the progress of a run: ``pyantz-status <working directory>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

QUEUE_FILE_NAME = "queue.db"


def describe_run(working_directory: Path) -> str:
    """Summarize the queue of the run in *working_directory*.

    Raises:
        FileNotFoundError: if the directory has no queue (no run was started there)

    """
    queue_file = working_directory / QUEUE_FILE_NAME
    if not queue_file.is_file():
        msg = f"No run found: {queue_file} does not exist"
        raise FileNotFoundError(msg)

    queue = SqliteQueue(queue_file)
    report = queue.get_jobs_report()
    lines = [
        f"Jobs: {report.total}",
        f"  succeeded: {report.success}",
        f"  failed:    {report.error}",
        f"  running:   {report.running}",
        f"  ready:     {report.ready}",
        f"  waiting:   {report.pending}",
    ]
    failed = queue.get_job_ids_with_status(JobStatus.ERROR)
    if failed:
        lines.append("Failed jobs:")
        lines.extend(f"  {job_id}" for job_id in failed)
    return "\n".join(lines)


def main() -> None:
    """Entry point of ``pyantz-status``."""
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
