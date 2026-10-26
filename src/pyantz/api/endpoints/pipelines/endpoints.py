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
runs_router = APIRouter(prefix="/runs")

RUN_ID_PATTERN = re.compile(r"[0-9a-f]{32}")

# the most of a run's log which one request can get
MAX_LOG_BYTES = 1_000_000
DEFAULT_LOG_BYTES = 20_000

# the processes started by this server; a restart forgets them
_PROCESSES: dict[str, subprocess.Popen[bytes]] = {}

type ConfigBody = Annotated[dict[str, Any], Body()]


def _problems(config: dict[str, Any]) -> tuple[InitialConfig | None, list[str]]:
    """Validate the configuration and list what is wrong with it."""
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
    """Check a configuration and list its problems."""
    _, errors = _problems(config)
    return ValidateResponse(valid=not errors, errors=errors)


@router.post("/compile")
def compile_config(config: ConfigBody) -> CompileResponse:
    """Compile a configuration into its concrete jobs and dependency edges."""
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
    """
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
    """Get the directory of a run, refusing ids which could escape the runs dir."""
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"No such run: {run_id}"
        ) from None
    return get_runs_dir() / run_id


@runs_router.get("/{run_id}")
def get_run(run_id: str) -> RunResponse:
    """Get the progress of a run: its state, job counts and per-job statuses."""
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
    """Get the end of what a run printed (its standard output and errors)."""
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
