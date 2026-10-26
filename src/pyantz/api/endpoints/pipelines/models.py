"""Data models of the pipeline endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidateResponse(BaseModel):
    """Result of checking a configuration."""

    valid: bool
    """True if the configuration has no problems."""

    # one message per problem found, empty if valid
    errors: list[str] = Field(default_factory=list)
    """One message per problem found, empty if valid."""


class CompiledJob(BaseModel):
    """A job of the compiled configuration."""

    job_id: str
    """The job's id."""

    name: str | None = None
    """The job's human readable name."""

    function: str
    """Import path of the job's function."""

    depends_on: list[str] = Field(default_factory=list)
    """Ids of the jobs it depends on, sorted."""


class CompileResponse(BaseModel):
    """The jobs of a configuration once virtual jobs are expanded."""

    jobs: list[CompiledJob]
    """The concrete jobs."""

    # (dependency, dependent) pairs, ready to draw as a graph
    edges: list[tuple[str, str]]
    """(dependency, dependent) pairs, ready to draw as a graph."""


class StartRunResponse(BaseModel):
    """A run was started."""

    run_id: str
    """Id to ask about the run with."""


class JobState(BaseModel):
    """Status of one job of a run."""

    job_id: str
    """The job's id."""

    status: str
    """The job's status, in lower case (``ready``, ``pending``, ...)."""

    details: str | None = None
    """Why the job has this status, e.g., its error."""


class RunResponse(BaseModel):
    """Progress of a run."""

    run_id: str
    """The run's id."""

    # running, succeeded, failed or unknown (e.g. the server restarted mid-run)
    state: str
    """``running``, ``succeeded``, ``failed`` or ``unknown`` (e.g. the server
    restarted mid-run)."""

    # counts of the jobs by status; None until the run has created its queue
    report: dict[str, Any] | None = None
    """Counts of the jobs by status; None until the run has created its queue."""

    jobs: list[JobState] = Field(default_factory=list)
    """The status of each job."""


class RunLogResponse(BaseModel):
    """The end of what a run printed."""

    run_id: str
    """The run's id."""

    # the last bytes of the log, decoded; may start in the middle of a line
    log: str
    """The last bytes of the log, decoded; may start in the middle of a line."""

    # True if the log is longer than what is returned
    truncated: bool
    """True if the log is longer than what is returned."""
