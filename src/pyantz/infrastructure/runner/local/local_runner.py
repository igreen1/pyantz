"""A local runner executes code on the device."""

import contextlib
import logging
import multiprocessing as mp
import signal
import threading
import time
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

# seconds workers get to mark their job as failed before being killed
WORKER_STOP_TIMEOUT = 10.0

if TYPE_CHECKING:
    import uuid
    from collections.abc import Generator
    from pathlib import Path


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
    with _sigterm_as_keyboard_interrupt():
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
            target=_worker_process,
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

    try:
        with _sigterm_as_keyboard_interrupt():
            for p in procs:
                p.join()
                logger.debug("Joined %d", p.pid)
    except KeyboardInterrupt:
        logger.warning("Interrupted, stopping %d worker processes", len(procs))
        _stop_workers(procs)
        raise

    logger.debug("Local runner complete, shutting down.")


def _stop_workers(procs: list[mp.Process]) -> None:
    """Ask the workers to stop (they mark their job as failed), then force them."""
    for p in procs:
        if p.is_alive():
            p.terminate()
    for p in procs:
        p.join(timeout=WORKER_STOP_TIMEOUT)
        if p.is_alive():
            p.kill()
            p.join()


@contextlib.contextmanager
def _sigterm_as_keyboard_interrupt() -> Generator[None]:
    """Treat SIGTERM like Ctrl+C while inside the context (main thread only)."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _handler(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, _handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


class WorkerTerminatedError(BaseException):
    """Raised inside a worker process when it is asked to terminate (SIGTERM).

    Deliberately not an ``Exception`` so that job code cannot swallow it.
    """


def _worker_process(queue_file: Path, poll_time: float, timeout: float | None) -> None:
    """Entry point of a worker process in the pool."""

    def _handler(_signum: int, _frame: object) -> None:
        raise WorkerTerminatedError

    signal.signal(signal.SIGTERM, _handler)
    try:
        _worker(queue_file, poll_time, timeout)
    except KeyboardInterrupt, WorkerTerminatedError:
        logging.getLogger(__name__).warning("Worker process interrupted, exiting")


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


def _worker(
    queue_file: Path,
    poll_time: float,
    timeout: float | None,
) -> None:
    """Run a job."""
    logger = logging.getLogger(__name__)
    queue = SqliteQueue(queue_file)

    # add wrapping context for the submitter
    # which needs to know which parent submitted a job
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

    timeout_ctr = 0.0
    while True:
        # get job from the queue
        match queue.get_job().payload:
            case JobReturn(job=job_config):
                # set job to running
                queue.update_job_status(job_config.job_id, status=JobStatus.RUNNING)
                try:
                    result = run_job(job_config, submit_fn)
                except Exception as exc:
                    logger.exception("Unknown error in job!", exc_info=exc)
                    result = False
                except KeyboardInterrupt, WorkerTerminatedError:
                    # don't leave the job RUNNING forever
                    logger.warning(
                        "Interrupted while running job %s", job_config.job_id
                    )
                    queue.update_job_status(job_config.job_id, status=JobStatus.ERROR)
                    raise
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
