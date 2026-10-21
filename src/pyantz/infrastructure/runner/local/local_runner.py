"""A local runner executes code on the device."""

from __future__ import annotations

import contextlib
import logging
import multiprocessing as mp
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

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

# seconds workers get to mark their job as failed before being killed
WORKER_STOP_TIMEOUT = 10.0

# seconds to wait for a job's process to start, and to stop after being asked to
STARTUP_WAIT_SECONDS = 60.0
STOP_WAIT_SECONDS = 5.0

# python 3.14 starts processes with forkserver by default on POSIX except macOS;
# 3.13 forks, which is unsafe once the parent has threads (and warns about it)
_POOL_CONTEXT = (
    mp.get_context("forkserver")
    if sys.platform != "darwin" and "forkserver" in mp.get_all_start_methods()
    else mp.get_context()
)

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable, Generator, Sequence
    from multiprocessing.process import BaseProcess
    from multiprocessing.synchronize import Event as SyncEvent


def start(config: InitialConfig) -> JobsReport:
    """Start the local runner processes and return the final report of the jobs.

    Raises:
        TypeError: if the submitter of the configuration is not a local runner

    """
    logger = logging.getLogger(__name__)
    runner_config = config.submitter
    if not isinstance(runner_config, LocalRunnerConfig):
        msg = f"Expected a local_proc submitter, not {runner_config.type_!r}"
        raise TypeError(msg)

    queue_file = runner_config.working_directory / "queue.db"
    runner_config.working_directory.mkdir(parents=True, exist_ok=True)
    _remove_stale_queue(queue_file)
    logger.debug("Creating sqlite queue %s", queue_file)

    queue = SqliteQueue(queue_file)
    _fill_queue(config, queue)
    if runner_config.use_same_proc:
        _run_within_same_proc(runner_config, queue_file)
    else:
        _start_pool(runner_config, queue_file)

    report = queue.get_jobs_report()
    logger.info(
        "Run finished: %d total, %d succeeded, %d errored, %d unfinished",
        report.total,
        report.success,
        report.error,
        report.total - report.success - report.error,
    )
    _log_failures(queue)
    return report


def _log_failures(queue: SqliteQueue) -> None:
    """Log a table with each failed job and the first line of its error."""
    failed = queue.get_failed_jobs()
    if not failed:
        return
    rows = [
        (str(job.job_id), (job.status_details or "").strip().partition("\n")[0])
        for job in failed
    ]
    width = max(len(job_id) for job_id, _ in rows)
    table = "\n".join(f"  {job_id:<{width}}  {error}" for job_id, error in rows)
    logging.getLogger(__name__).error("%d job(s) failed:\n%s", len(failed), table)


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


def _run_within_same_proc(runner_config: LocalRunnerConfig, queue_file: Path) -> None:
    """Run the local runner pool in this process.

    Mostly used for testing.
    """
    with _sigterm_as_keyboard_interrupt():
        _worker(
            queue_file=queue_file,
            poll_time=runner_config.poll_timeout,
            timeout=runner_config.timeout,
        )


def _start_pool(runner_config: LocalRunnerConfig, queue_file: Path) -> None:
    """Start the local runner pool."""
    logger = logging.getLogger(__name__)

    logger.debug("Starting local runners")
    procs = [
        _POOL_CONTEXT.Process(
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
            _wait_for_workers(procs, queue_file, runner_config.progress_interval)
    except KeyboardInterrupt:
        logger.warning("Interrupted, stopping %d worker processes", len(procs))
        _stop_workers(procs)
        raise

    logger.debug("Local runner complete, shutting down.")
    for p in procs:
        logger.debug("Joined %d", p.pid)


def _wait_for_workers(
    procs: Sequence[BaseProcess],
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


def _stop_workers(procs: Sequence[BaseProcess]) -> None:
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
    except (KeyboardInterrupt, WorkerTerminatedError):
        logging.getLogger(__name__).warning("Worker process interrupted, exiting")


def _fill_queue(config: InitialConfig, queue: SqliteQueue) -> None:
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


def _record_result(
    queue: SqliteQueue, job_config: JobWithContext, result: JobResult
) -> None:
    """Store the outcome of a job, or put it back in the queue to be retried."""
    if result.success:
        queue.update_job_status(
            job_config.job_id,
            status=JobStatus.SUCCESS,
            details=result.details,
        )
    elif job_config.num_attempted_runs < job_config.max_retries:
        attempts = job_config.num_attempted_runs + 1
        logging.getLogger(__name__).warning(
            "Job %s failed, retrying (retry %d of %d)",
            job_config.job_id,
            attempts,
            job_config.max_retries,
        )
        queue.change_config_in_place(
            job_config.model_copy(update={"num_attempted_runs": attempts}),
        )
        queue.update_job_status(job_config.job_id, status=JobStatus.PENDING)
    else:
        queue.update_job_status(
            job_config.job_id,
            status=JobStatus.ERROR,
            details=result.details,
        )


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
        if not queue.add_job(
            submitted_job,
            parent_job_id=parent_job,
        ):
            msg = f"Could not add job {submitted_job.job_id} to the queue"
            raise RuntimeError(msg)

    return submit_fn


def _run_in_child(job_json: str, queue_file: str, ready: SyncEvent) -> None:
    """Run a job in this (child) process; exit with a failing status if it failed."""
    ready.set()  # the timeout starts now, not while this process was starting up
    job_config = JobWithContext.model_validate_json(job_json)
    submit_fn = _make_submit_fn(SqliteQueue(Path(queue_file)))
    sys.exit(0 if run_job_with_details(job_config, submit_fn).success else 1)


def _run_with_timeout(
    job_config: JobWithContext, queue_file: Path, timeout: float
) -> JobResult:
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
        return JobResult(
            success=False,
            details=f"Timed out after {timeout} seconds",
        )
    return JobResult(
        success=process.exitcode == 0,
        details=None if process.exitcode == 0 else "The job's process failed",
    )


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
    deadlocked_polls = 0
    while True:
        # get job from the queue
        match queue.get_job().payload:
            case JobReturn(job=job_config):
                # set job to running
                try:
                    queue.update_job_status(job_config.job_id, status=JobStatus.RUNNING)
                    queue.set_job_worker(job_config.job_id, os.getpid())
                    if job_config.timeout_seconds is None:
                        result = run_job_with_details(job_config, submit_fn)
                    else:
                        result = _run_with_timeout(
                            job_config,
                            queue_file,
                            job_config.timeout_seconds,
                        )
                except Exception as exc:
                    logger.exception("Unknown error in job!", exc_info=exc)
                    result = JobResult(
                        success=False,
                        details=f"{type(exc).__name__}: {exc}",
                    )
                except (KeyboardInterrupt, WorkerTerminatedError):
                    # don't leave the job RUNNING forever
                    logger.warning(
                        "Interrupted while running job %s", job_config.job_id
                    )
                    queue.update_job_status(job_config.job_id, status=JobStatus.ERROR)
                    raise
                _record_result(queue, job_config, result)
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
