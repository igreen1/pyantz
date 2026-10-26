"""Get the jobs as a list for the user."""

from __future__ import annotations

import inspect

from fastapi import APIRouter

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.infrastructure.config.job import serialize_function
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

from .models import GetJobResponse, JobInfo

router = APIRouter(prefix="/jobs")
"""Routes listing the jobs."""

NO_DESCRIPTION = "No description available."
"""Description of jobs without a docstring."""


def describe_job(fn: object) -> str:
    """Get the first paragraph of the docstring, on one line.

    Args:
        fn: the job function.

    Returns:
        str: the first paragraph of its docstring, or :data:`NO_DESCRIPTION`.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.api.endpoints.get_jobs.endpoint import describe_job
            from pyantz.jobs.files.simple import mkdir

            print(describe_job(mkdir))
            print(describe_job(lambda: None))

        .. testoutput::

            Create the directory, and any missing parents (it may already exist).
            No description available.

    """
    doc = inspect.getdoc(fn)
    if not doc:
        return NO_DESCRIPTION
    return " ".join(doc.split("\n\n", maxsplit=1)[0].split())


@router.get("/get_all_jobs")
def get_jobs() -> GetJobResponse:
    """Get list of all the available jobs.

    \f
    Args:
        None.

    Returns:
        GetJobResponse: the name and description of each registered job.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.api.endpoints.get_jobs.endpoint import get_jobs

            names = [job.name for job in get_jobs().jobs]
            print("pyantz.jobs.files.simple.copy" in names)

        .. testoutput::

            True

    """  # noqa: D301
    return GetJobResponse(
        jobs=[
            JobInfo(name=serialize_function(fn), description=describe_job(fn))
            for fn in get_registered_functions()
        ]
    )
