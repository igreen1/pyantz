"""A local runner executes code on the device."""

import logging
import multiprocessing as mp
import time
from typing import TYPE_CHECKING

from pyantz.infrastructure.config import (
    AnyRunner,
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

if TYPE_CHECKING:
    import uuid
    from pathlib import Path


def start(config: InitialConfig[LocalRunnerConfig]) -> None:
    """Start the lcoal runner processes."""
    logger = logging.getLogger(__name__)

    runner_config = config.submitter
    queue_file = runner_config.working_directory / "queue.db"
    logger.debug("Creating sqlite queue %s", queue_file)

    _fill_queue(config, SqliteQueue(queue_file))

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


def _fill_queue(config: InitialConfig[AnyRunner], queue: SqliteQueue) -> None:
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
