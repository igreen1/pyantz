"""A local runner executes code on the device."""

import logging
import multiprocessing as mp
import os
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
    JobsReport,
    JobStatus,
    PendingReturn,
)
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue
from pyantz.infrastructure.runner.job_manager import JobResult, run_job_with_details

# consecutive polls with only pending jobs before they are declared deadlocked
DEADLOCK_POLLS = 3

# how often the pool checks whether a worker died
DEATH_CHECK_SECONDS = 0.2

if TYPE_CHECKING:
    import uuid
    from pathlib import Path


def start(config: InitialConfig[LocalRunnerConfig]) -> JobsReport:
    """Start the local runner processes and return the final report of the jobs."""
    logger = logging.getLogger(__name__)

    queue_file = config.submitter.working_directory / "queue.db"
    config.submitter.working_directory.mkdir(parents=True, exist_ok=True)
    _remove_stale_queue(queue_file)
    logger.debug("Creating sqlite queue %s", queue_file)

    queue = SqliteQueue(queue_file)
    _fill_queue(config, queue)
    if config.submitter.use_same_proc:
        _run_within_same_proc(config, queue_file)
    else:
        _start_pool(config, queue_file)

    report = queue.get_jobs_report()
    logger.info(
        "Run finished: %d total, %d succeeded, %d errored, %d unfinished",
        report.total,
        report.success,
        report.error,
        report.total - report.success - report.error,
    )
    return report


def _remove_stale_queue(queue_file: Path) -> None:
    """Delete the queue (and sqlite side files) left behind by a previous run.

    Every run starts from an empty queue, otherwise old jobs and statuses would
    mix with the new run and re-adding jobs with the same ids would fail.
    """
    logger = logging.getLogger(__name__)
    stale = [
        queue_file.with_name(queue_file.name + suffix)
        for suffix in ("", "-wal", "-shm")
    ]
    if queue_file.exists():
        logger.warning("Removing queue left over from a previous run: %s", queue_file)
    for path in stale:
        path.unlink(missing_ok=True)


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

    _wait_for_workers(procs, queue_file, runner_config.progress_interval)
    logger.debug("Local runner complete, shutting down.")
    for p in procs:
        logger.debug("Joined %d", p.pid)


def _wait_for_workers(
    procs: list[mp.Process],
    queue_file: Path,
    progress_interval: float | None = None,
) -> None:
    """Wait for all the workers, failing the jobs of those which die abnormally.

    A worker killed while running a job (out of memory, a crash in a C extension)
    can never report back, so its job would stay RUNNING and the other workers
    would wait for it forever.
    """
    logger = logging.getLogger(__name__)
    queue = SqliteQueue(queue_file)
    handled: set[int] = set()
    last_report = time.monotonic()
    while any(p.is_alive() for p in procs):
        if (
            progress_interval is not None
            and time.monotonic() - last_report >= progress_interval
        ):
            last_report = time.monotonic()
            _log_progress(queue)
        for p in procs:
            if p.pid is None or p.pid in handled or p.is_alive():
                continue
            handled.add(p.pid)
            if p.exitcode != 0:
                failed = queue.fail_jobs_of_worker(p.pid)
                logger.error(
                    "Worker %d died (exit code %s); failed its jobs: %s",
                    p.pid,
                    p.exitcode,
                    failed,
                )
        time.sleep(DEATH_CHECK_SECONDS)
    for p in procs:
        p.join()
        if p.pid is not None and p.pid not in handled and p.exitcode != 0:
            queue.fail_jobs_of_worker(p.pid)


def _log_progress(queue: SqliteQueue) -> None:
    """Log a one-line progress report of the queue."""
    report = queue.get_jobs_report()
    logging.getLogger(__name__).info(
        "Progress: %d of %d jobs done (%d succeeded, %d failed); "
        "%d running, %d ready, %d waiting",
        report.success + report.error,
        report.total,
        report.success,
        report.error,
        report.running,
        report.ready,
        report.pending,
    )


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


def _check_for_deadlock(
    queue: SqliteQueue,
    report: JobsReport,
    deadlocked_polls: int,
) -> int:
    """Fail jobs which can never run and return the updated deadlocked poll count.

    A queue with only pending jobs cannot make progress. To avoid racing with another
    worker that is between two queue updates, the state must persist for a few
    consecutive polls before the pending jobs are marked as ERROR.
    """
    if report.running != 0 or report.ready != 0 or report.pending == 0:
        return 0
    deadlocked_polls += 1
    if deadlocked_polls < DEADLOCK_POLLS:
        return deadlocked_polls
    stuck = queue.fail_deadlocked_jobs()
    if stuck:
        logging.getLogger(__name__).error(
            "Jobs can never run (unknown or unsatisfiable dependencies); "
            "marking as ERROR: %s",
            stuck,
        )
    return 0


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
        if not queue.add_job(
            submitted_job,
            parent_job_id=parent_job,
        ):
            msg = f"Could not add job {submitted_job.job_id} to the queue"
            raise RuntimeError(msg)

    timeout_ctr = 0.0
    deadlocked_polls = 0
    while True:
        # get job from the queue
        match queue.get_job().payload:
            case JobReturn(job=job_config):
                # set job to running
                queue.update_job_status(job_config.job_id, status=JobStatus.RUNNING)
                queue.set_job_worker(job_config.job_id, os.getpid())
                try:
                    result = run_job_with_details(job_config, submit_fn)
                except Exception as exc:
                    logger.exception("Unknown error in job!", exc_info=exc)
                    result = JobResult(
                        success=False,
                        details=f"{type(exc).__name__}: {exc}",
                    )
                status = JobStatus.SUCCESS if result.success else JobStatus.ERROR
                queue.update_job_status(
                    job_config.job_id,
                    status=status,
                    details=result.details,
                )
                timeout_ctr = 0.0  # reset timer, we got and did a job :)
            case PendingReturn(jobs_report=report):
                deadlocked_polls = _check_for_deadlock(queue, report, deadlocked_polls)
                time.sleep(poll_time)
                timeout_ctr += poll_time
            case CompleteReturn():
                return

        if timeout is not None and timeout_ctr > timeout:
            logger.warning("Worker died due to timeout - exiting")
            return
