"""Get the jobs as a list for the user."""

import inspect

from fastapi import APIRouter

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.infrastructure.config.job import serialize_function
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

from .models import GetJobResponse, JobInfo

router = APIRouter(prefix="/jobs")

NO_DESCRIPTION = "No description available."


def _describe(fn: object) -> str:
    """Get the first paragraph of the docstring, on one line."""
    doc = inspect.getdoc(fn)
    if not doc:
        return NO_DESCRIPTION
    return " ".join(doc.split("\n\n", maxsplit=1)[0].split())


@router.get("/get_all_jobs")
def get_jobs() -> GetJobResponse:
    """Get list of all the available jobs."""
    return GetJobResponse(
        jobs=[
            JobInfo(name=serialize_function(fn), description=_describe(fn))
            for fn in get_registered_functions()
        ]
    )
