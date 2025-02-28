"""Runs local configs"""

import logging.handlers
import multiprocessing as mp
import os
import queue
import threading
import time

from pyantz.infrastructure.config.base import Config, InitialConfig, LoggingConfig
from pyantz.infrastructure.core.manager import run_manager
from pyantz.infrastructure.log.multiproc_logging import ANTZ_LOG_ROOT_NAME, get_listener


def run_local_submitter(config: InitialConfig) -> threading.Thread:
    """Start the local submitter to accept jobs

    Args:
        config (InitialConfig): user configuration of all jobs

    Returns:
        Callable[[PipelineConfig], None]: callable that accepts a pipeline config
            and places it on the queue
    """
    try:
        # we have significant threading, so complete isolation is required
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    unified_task_queue: mp.Queue = mp.Queue()

    proc_ = LocalProcManager(
        task_queue=unified_task_queue,
        number_procs=config.submitter_config.num_concurrent_jobs,
        logging_config=config.logging_config,
    )

    def submit_pipeline(config: Config) -> None:
        """Closure for the unified task queue"""
        return unified_task_queue.put(config.model_dump())

    submit_pipeline(config.analysis_config)
    proc_.start()

    return proc_


class LocalProcManager(threading.Thread):
    """Holds the various local runners and issues them a kill command when done"""

    def __init__(
        self, task_queue: mp.Queue, number_procs: int, logging_config: LoggingConfig
    ) -> None:
        """Creates the local proc manager

        Args:
            task_queue (mp.Queue[PipelineConfig]): universal queue for job submission
            number_procs (int): number of parallel processes to start up
            logging_config (LoggingConfig): configuration of instance loggers
        """
        super().__init__()
        self.task_queue = task_queue
        self.number_procs = number_procs
        self.logger_queue, self.logger_proc = get_listener(logging_config)

    def run(self) -> None:
        """Run and issue kill command when nothing else to do and the jobs are complete"""

        children = [LocalProc(self.task_queue, logger_queue=self.logger_queue)]

        for child in children:
            child.start()

        while True:
            if self.task_queue.qsize() == 0 and all(
                not child.get_is_executing() for child in children
            ):
                for child in children:
                    child.set_dead(True)
                break
            time.sleep(1)  # only check every second

        for child in children:
            child.join()


class LocalProc(mp.Process):
    """Local proc is the node that actually runs the code"""

    def __init__(self, task_queue: mp.Queue, logger_queue: mp.Queue) -> None:
        """Initialize the process with the universal job queue"""

        super().__init__()

        self._queue = task_queue
        self._is_executing = mp.Value("b")
        with self._is_executing.get_lock():
            self._is_executing.value = 0

        self._is_dead = mp.Value("b")
        with self._is_dead.get_lock():
            self._is_dead.value = 0

        qh = logging.handlers.QueueHandler(logger_queue)
        self.logger = logging.getLogger(f"{ANTZ_LOG_ROOT_NAME}.localProc_{os.getpid()}")
        self.logger.addHandler(qh)

    def get_is_executing(self) -> bool:
        """Return if the current process is executing a pipeline"""
        with self._is_executing.get_lock():
            ret = self._is_executing.value
        return ret

    def set_dead(self, new_val) -> None:
        """Tell this process to kill itself"""
        with self._is_dead.get_lock():
            self._is_dead.value = new_val
        self.logger.info("Killing local process runner")

    def run(self):
        """Infinitely loop waiting for a new job on the queue until the set_dead(True)"""

        def submit_fn(config: Config) -> None:
            """Submit a pipeline to this submitter"""
            self._queue.put(config.model_dump())

        while not self._is_dead.value:
            try:
                next_config = Config.model_validate(self._queue.get(timeout=1))
                self.logger.info("Got next configuration %s", next_config.config.id)
                with self._is_executing.get_lock():
                    self._is_executing.value = True
                try:
                    run_manager(next_config, submit_fn=submit_fn, logger=self.logger)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self.logger.error(
                        "Unknown error when running manager", exc_info=exc
                    )

                with self._is_executing.get_lock():
                    self._is_executing.value = False
            except queue.Empty as _e:
                pass  # just waiting for another job
            time.sleep(0.5)  # only check every 1/2 second to reduce resource usage
        with self._is_executing.get_lock():
            self._is_executing = False
