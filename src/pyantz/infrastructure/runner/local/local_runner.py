"""A local runner executes code on the device."""

import logging
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import (
    InitialConfig,
    JobWithContext,
    LocalRunnerConfig,
)
from pyantz.infrastructure.distributed_queue.common.return_types import (
    CompleteReturn,
    JobReturn,
    JobStatus,
    PendingReturn,
)
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue
from pyantz.infrastructure.runner.job_manager import run_job

# seconds to wait for a job's process to start, and to stop after being asked to
STARTUP_WAIT_SECONDS = 60.0
STOP_WAIT_SECONDS = 5.0

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable
    from multiprocessing.synchronize import Event as SyncEvent


def start(config: InitialConfig[LocalRunnerConfig]) -> None:
    """Start the lcoal runner processes."""
    logger = logging.getLogger(__name__)

    queue_file = config.submitter.working_directory / "queue.db"
    if not config.submitter.working_directory.exists():
        config.submitter.working_directory.mkdir()
    logger.debug("Creating sqlite queue %s", queue_file)

    _fill_queue(config, SqliteQueue(queue_file))
    if config.submitter.use_same_proc:
        _run_within_same_proc(config, queue_file)
    else:
        _start_pool(config, queue_file)


def _run_within_same_proc(
    config: InitialConfig[LocalRunnerConfig], queue_file: Path
) -> None:
    """Run the local runner pool in this process.

    Mostly used for testing.
    """
    runner_config = config.submitter
    _worker(
        queue_file=queue_file,
        poll_time=runner_config.poll_timeout,
        timeout=runner_config.timeout,
    )


def _start_pool(config: InitialConfig[LocalRunnerConfig], queue_file: Path) -> None:
    """Start the local runner pool."""
    logger = logging.getLogger(__name__)
    runner_config = config.submitter

    logger.debug("Starting local runners")
    procs = [
        mp.Process(
            target=_worker,
            args=(
                queue_file,
                runner_config.poll_timeout,
                runner_config.timeout,
            ),
        )
        for _ in range(runner_config.number_processes)
    ]

    logger.debug("Running %s processes, starting", len(procs))
    for p in procs:
        p.start()
        logger.debug("Starting process %d", p.pid)

    for p in procs:
        p.join()
        logger.debug("Joined %d", p.pid)

    logger.debug("Local runner complete, shutting down.")


def _fill_queue(config: InitialConfig[Any], queue: SqliteQueue) -> None:
    """Fill the queue with the initial jobs to run."""
    logger = logging.getLogger(__name__)
    logger.debug("Filling queue with initial jobs to run.")
    for job in config.jobs:
        # add context to the job
        job_with_var = JobWithContext.model_validate(
            {
                **job.model_dump(),
                "variables": config.variables,
            },
        )
        logger.debug("adding job %s", job_with_var)
        queue.add_job(job_with_var, None)


def _make_submit_fn(
    queue: SqliteQueue,
) -> Callable[[JobWithContext, str | uuid.UUID | None], None]:
    """Create the function which jobs use to add jobs to the local queue.

    It needs to know which parent submitted a job.
    """
    logger = logging.getLogger(__name__)

    def submit_fn(
        submitted_job: JobWithContext,
        parent_job: str | uuid.UUID | None,
    ) -> None:
        """Add job to the local queue."""
        logger.debug("Job submitted %s", submitted_job)
        logger.info(
            "Adding job to queue with updated variables: %s",
            submitted_job.job_id,
        )
        queue.add_job(
            submitted_job,
            parent_job_id=parent_job,
        )

    return submit_fn


def _run_in_child(job_json: str, queue_file: str, ready: SyncEvent) -> None:
    """Run a job in this (child) process; exit with a failing status if it failed."""
    ready.set()  # the timeout starts now, not while this process was starting up
    job_config = JobWithContext.model_validate_json(job_json)
    submit_fn = _make_submit_fn(SqliteQueue(Path(queue_file)))
    sys.exit(0 if run_job(job_config, submit_fn) else 1)


def _run_with_timeout(
    job_config: JobWithContext, queue_file: Path, timeout: float
) -> bool:
    """Run the job in a separate process, which is stopped if it takes too long."""
    logger = logging.getLogger(__name__)
    context = mp.get_context("spawn")
    ready = context.Event()
    process = context.Process(
        target=_run_in_child,
        args=(job_config.model_dump_json(), os.fspath(queue_file), ready),
    )
    process.start()
    ready.wait(STARTUP_WAIT_SECONDS)
    process.join(timeout)
    if process.is_alive():
        logger.error(
            "Job %s timed out after %s seconds, stopping it",
            job_config.job_id,
            timeout,
        )
        process.terminate()
        process.join(STOP_WAIT_SECONDS)
        if process.is_alive():
            process.kill()
            process.join()
        return False
    return process.exitcode == 0


def _worker(
    queue_file: Path,
    poll_time: float,
    timeout: float | None,
) -> None:
    """Run a job."""
    logger = logging.getLogger(__name__)
    queue = SqliteQueue(queue_file)
    submit_fn = _make_submit_fn(queue)

    timeout_ctr = 0.0
    while True:
        # get job from the queue
        match queue.get_job().payload:
            case JobReturn(job=job_config):
                # set job to running
                queue.update_job_status(job_config.job_id, status=JobStatus.RUNNING)
                try:
                    if job_config.timeout_seconds is None:
                        result = run_job(job_config, submit_fn)
                    else:
                        result = _run_with_timeout(
                            job_config,
                            queue_file,
                            job_config.timeout_seconds,
                        )
                except Exception as exc:
                    logger.exception("Unknown error in job!", exc_info=exc)
                    result = False
                status = JobStatus.SUCCESS if result else JobStatus.ERROR
                queue.update_job_status(job_config.job_id, status=status)
                timeout_ctr = 0.0  # reset timer, we got and did a job :)
            case PendingReturn():
                time.sleep(poll_time)
                timeout_ctr += poll_time
            case CompleteReturn():
                return

        if timeout is not None and timeout_ctr > timeout:
            logger.warning("Worker died due to timeout - exiting")
            return
