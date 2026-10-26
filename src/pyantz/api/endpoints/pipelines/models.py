"""Data models of the pipeline endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidateResponse(BaseModel):
    """Result of checking a configuration."""

    valid: bool

    # one message per problem found, empty if valid
    errors: list[str] = Field(default_factory=list)


class CompiledJob(BaseModel):
    """A job of the compiled configuration."""

    job_id: str
    name: str | None = None
    function: str
    depends_on: list[str] = Field(default_factory=list)


class CompileResponse(BaseModel):
    """The jobs of a configuration once virtual jobs are expanded."""

    jobs: list[CompiledJob]

    # (dependency, dependent) pairs, ready to draw as a graph
    edges: list[tuple[str, str]]


class StartRunResponse(BaseModel):
    """A run was started."""

    run_id: str


class JobState(BaseModel):
    """Status of one job of a run."""

    job_id: str
    status: str
    details: str | None = None


class RunResponse(BaseModel):
    """Progress of a run."""

    run_id: str

    # running, succeeded, failed or unknown (e.g. the server restarted mid-run)
    state: str

    # counts of the jobs by status; None until the run has created its queue
    report: dict[str, Any] | None = None

    jobs: list[JobState] = Field(default_factory=list)


class RunLogResponse(BaseModel):
    """The end of what a run printed."""

    run_id: str

    # the last bytes of the log, decoded; may start in the middle of a line
    log: str

    # True if the log is longer than what is returned
    truncated: bool
