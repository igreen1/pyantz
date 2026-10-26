"""Endpoints to validate, preview and run pipeline configurations."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import ValidationError

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.api.settings import get_runs_dir
from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.fn_utils import ALLOWED_MODULES_VARIABLE
from pyantz.infrastructure.config.job import serialize_function
from pyantz.infrastructure.config.runners import LocalRunnerConfig
from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

from .models import (
    CompiledJob,
    CompileResponse,
    JobState,
    RunLogResponse,
    RunResponse,
    StartRunResponse,
    ValidateResponse,
)

if TYPE_CHECKING:
    from pathlib import Path

router = APIRouter(prefix="/config")
"""Routes checking configurations."""

runs_router = APIRouter(prefix="/runs")
"""Routes starting and following runs."""

RUN_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
"""What a run id looks like (a uuid in hex)."""

MAX_LOG_BYTES = 1_000_000
"""The most of a run's log which one request can get."""

DEFAULT_LOG_BYTES = 20_000
"""How much of a run's log a request gets by default."""

_PROCESSES: dict[str, subprocess.Popen[bytes]] = {}
"""The processes started by this server, by run id; a restart forgets them."""

type ConfigBody = Annotated[dict[str, Any], Body()]
"""A configuration, sent as the request's json body."""


def _problems(config: dict[str, Any]) -> tuple[InitialConfig | None, list[str]]:
    """Validate the configuration and list what is wrong with it.

    Args:
        config: the configuration, as sent.

    Returns:
        tuple[InitialConfig | None, list[str]]: the validated configuration (None
        if invalid) and a message for each problem.

    Raises:
        None: problems are returned.

    Example:
        .. testcode::

            from pyantz.api.endpoints.pipelines.endpoints import _problems

            config, problems = _problems({"jobs": []})
            print(config, problems)

        .. testoutput::

            None ['submitter: Field required']

    """
    try:
        return InitialConfig.model_validate(config), []
    except ValidationError as exc:
        return None, [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
    except (ValueError, TypeError, ImportError, AttributeError) as exc:
        return None, [str(exc)]


@router.post("/validate")
def validate_config(config: ConfigBody) -> ValidateResponse:
    """Check a configuration and list its problems.

    \f
    Args:
        config: the configuration, as sent.

    Returns:
        ValidateResponse: whether it is valid, and its problems.

    Raises:
        None: problems are returned.

    Example:
        .. testcode::

            from pyantz.api.endpoints.pipelines.endpoints import validate_config

            result = validate_config(
                {
                    "submitter": {"type_": "local_proc", "working_directory": "."},
                    "jobs": [
                        {"function": "pyantz.jobs.testing.nop.do_nothing",
                         "parameters": {}, "depends_on": ["missing"]},
                    ],
                }
            )
            print(result.valid, len(result.errors))

        .. testoutput::

            False 1

    """  # noqa: D301
    _, errors = _problems(config)
    return ValidateResponse(valid=not errors, errors=errors)


@router.post("/compile")
def compile_config(config: ConfigBody) -> CompileResponse:
    """Compile a configuration into its concrete jobs and dependency edges.

    \f
    Args:
        config: the configuration, as sent.

    Returns:
        CompileResponse: the concrete jobs (virtual jobs expanded) and the edges
        between them.

    Raises:
        HTTPException: 422 if the configuration is invalid.

    Example:
        .. testcode::

            from pyantz.api.endpoints.pipelines.endpoints import compile_config

            nop = "pyantz.jobs.testing.nop.do_nothing"
            result = compile_config(
                {
                    "submitter": {"type_": "local_proc", "working_directory": "."},
                    "jobs": [
                        {"job_id": "a", "function": nop, "parameters": {}},
                        {"job_id": "b", "function": nop, "parameters": {},
                         "depends_on": ["a"]},
                    ],
                }
            )
            print(result.edges)

        .. testoutput::

            [('a', 'b')]

    """  # noqa: D301
    loaded, errors = _problems(config)
    if loaded is None:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=errors
        ) from None
    jobs = [
        CompiledJob(
            job_id=str(job.job_id),
            name=job.name,
            function=serialize_function(job.function),
            depends_on=sorted(str(dep) for dep in job.depends_on or ()),
        )
        for job in loaded.jobs
    ]
    edges = [(dep, job.job_id) for job in jobs for dep in job.depends_on]
    return CompileResponse(jobs=jobs, edges=edges)


@runs_router.post("")
def start_run(config: ConfigBody) -> StartRunResponse:
    """Start a run of the configuration in a new process, in its own directory.

    Only local runs are accepted, and the working directory is chosen by the server.
    Since a configuration can import and run any function, runs are refused unless
    the server limits the modules with `PYANTZ_ALLOWED_MODULES`.

    \f
    The run's directory (in :func:`~pyantz.api.settings.get_runs_dir`) holds its
    configuration, its log (``run.log``) and its working directory (``work``).

    Args:
        config: the configuration, as sent.

    Returns:
        StartRunResponse: the id of the new run.

    Raises:
        HTTPException: 403 if `PYANTZ_ALLOWED_MODULES` isn't set, 422 if the
            configuration is invalid or isn't a local run.
        OSError: if the run's directory can't be created.

    """  # noqa: D301
    if not os.environ.get(ALLOWED_MODULES_VARIABLE, "").strip():
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"Runs are disabled: set {ALLOWED_MODULES_VARIABLE} on the server",
        ) from None
    loaded, errors = _problems(config)
    if loaded is None:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=errors
        ) from None
    if not isinstance(loaded.submitter, LocalRunnerConfig) or loaded.host.type_ != (
        "local"
    ):
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="Only runs with a local_proc submitter on the local host work",
        ) from None

    run_id = uuid.uuid4().hex
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True)
    work_dir = run_dir / "work"
    submitter = {**config["submitter"], "working_directory": str(work_dir)}
    config_file = run_dir / "config.json"
    config_file.write_text(json.dumps({**config, "submitter": submitter}))
    with (run_dir / "run.log").open("wb") as log:
        _PROCESSES[run_id] = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "pyantz", str(config_file)],
            cwd=run_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return StartRunResponse(run_id=run_id)


def _run_dir(run_id: str) -> Path:
    """Get the directory of a run, refusing ids which could escape the runs dir.

    Args:
        run_id: the run's id.

    Returns:
        Path: the run's directory (which may not exist).

    Raises:
        HTTPException: 404 if the id isn't a valid run id.

    Example:
        .. testcode::

            from fastapi import HTTPException

            from pyantz.api.endpoints.pipelines.endpoints import _run_dir

            try:
                _run_dir("../../etc")
            except HTTPException as exc:
                print(exc.status_code)

        .. testoutput::

            404

    """
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"No such run: {run_id}"
        ) from None
    return get_runs_dir() / run_id


@runs_router.get("/{run_id}")
def get_run(run_id: str) -> RunResponse:
    """Get the progress of a run: its state, job counts and per-job statuses.

    \f
    Args:
        run_id: the run's id.

    Returns:
        RunResponse: the run's state, the counts of its jobs and their statuses.

    Raises:
        HTTPException: 404 if there is no such run.

    Example:
        .. testsetup:: api-get-run

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: api-get-run

            import os
            from pathlib import Path

            from pyantz.api.endpoints.pipelines.endpoints import get_run

            os.environ["PYANTZ_RUNS_DIR"] = "runs"
            run_id = "0" * 32
            Path("runs", run_id).mkdir(parents=True)
            try:
                print(get_run(run_id).state)  # this server didn't start it
            finally:
                del os.environ["PYANTZ_RUNS_DIR"]

        .. testoutput:: api-get-run

            unknown

        .. testcleanup:: api-get-run

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """  # noqa: D301
    run_dir = _run_dir(run_id)
    if not run_dir.is_dir():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"No such run: {run_id}"
        ) from None

    queue_file = run_dir / "work" / "queue.db"
    report = None
    jobs: list[JobState] = []
    if queue_file.is_file():
        queue = SqliteQueue(queue_file)
        report = queue.get_jobs_report()
        for status in JobStatus:
            for job_id in queue.get_job_ids_with_status(status):
                details = queue.get_job_status(job_id).status_details
                jobs.append(
                    JobState(job_id=job_id, status=status.name.lower(), details=details)
                )

    process = _PROCESSES.get(run_id)
    if process is not None:
        exit_code = process.poll()
        state = (
            "running"
            if exit_code is None
            else "succeeded"
            if exit_code == 0
            else "failed"
        )
    elif report is not None and report.all_succeeded:
        state = "succeeded"
    elif report is not None and report.error:
        state = "failed"
    else:
        state = "unknown"
    return RunResponse(
        run_id=run_id,
        state=state,
        report=report.model_dump() if report else None,
        jobs=jobs,
    )


@runs_router.get("/{run_id}/log")
def get_run_log(
    run_id: str,
    max_bytes: Annotated[int, Query(ge=1, le=MAX_LOG_BYTES)] = DEFAULT_LOG_BYTES,
) -> RunLogResponse:
    """Get the end of what a run printed (its standard output and errors).

    \f
    Args:
        run_id: the run's id.
        max_bytes: how many bytes of the end of the log to return.

    Returns:
        RunLogResponse: the end of the log, and whether it was cut.

    Raises:
        HTTPException: 404 if the run has no log.
        OSError: if the log can't be read.

    Example:
        .. testsetup:: api-get-run-log

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: api-get-run-log

            import os
            from pathlib import Path

            from pyantz.api.endpoints.pipelines.endpoints import get_run_log

            os.environ["PYANTZ_RUNS_DIR"] = "runs"
            run_id = "0" * 32
            Path("runs", run_id).mkdir(parents=True)
            Path("runs", run_id, "run.log").write_text("starting... all done")
            try:
                result = get_run_log(run_id, max_bytes=8)
                print(result.log, result.truncated)
            finally:
                del os.environ["PYANTZ_RUNS_DIR"]

        .. testoutput:: api-get-run-log

            all done True

        .. testcleanup:: api-get-run-log

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """  # noqa: D301
    run_dir = _run_dir(run_id)
    log_file = run_dir / "run.log"
    if not log_file.is_file():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"No log for run: {run_id}"
        ) from None
    with log_file.open("rb") as log:
        size = log.seek(0, os.SEEK_END)
        log.seek(max(0, size - max_bytes))
        tail = log.read()
    return RunLogResponse(
        run_id=run_id,
        log=tail.decode("utf-8", errors="replace"),
        truncated=size > max_bytes,
    )
