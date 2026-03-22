"""Get the jobs as a list for the user."""

from fastapi import APIRouter

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.infrastructure.config.job import serialize_function
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

from .models import GetJobReponse

router = APIRouter(prefix="/jobs")


@router.get("/get_all_jobs")
def get_jobs() -> GetJobReponse:
    """Get list of all the available jobs."""
    all_fn = get_registered_functions()

    fn_docstrings = [
        fn.__doc__ if fn.__doc__ is not None else "No description available."
        for fn in all_fn
    ]

    fn_summary_only = [doc.split("\n")[0] for doc in fn_docstrings]

    fn_summary_only = [doc.lstrip(".") for doc in fn_summary_only]

    return GetJobReponse(
        pyantz_jobs=[serialize_function(fn) for fn in all_fn],
        pyantz_job_descriptions=fn_summary_only,
    )
