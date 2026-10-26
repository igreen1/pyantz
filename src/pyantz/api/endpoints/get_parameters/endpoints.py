"""Get parameters to help the user setup their function."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import APIRouter, HTTPException

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

from .models import GetJsonSchemaResponse

if TYPE_CHECKING:
    from pydantic import BaseModel

router = APIRouter(prefix="/jobs")
"""Routes giving the parameters' schemas of the jobs."""


def strip_format[T](s: T) -> T:
    """Strip `format` from string fields.

    The web ui's forms reject formats they don't know, such as ``path``.

    Args:
        s: a json schema, or part of one.

    Returns:
        T: a copy without the ``format`` of ``string`` fields, at any depth.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.api.endpoints.get_parameters.endpoints import strip_format

            schema = {"anyOf": [{"type": "string", "format": "path"}, {"type": "null"}]}
            print(strip_format(schema))

        .. testoutput::

            {'anyOf': [{'type': 'string'}, {'type': 'null'}]}

    """
    if isinstance(s, dict):
        return cast(
            "T",
            {
                k: strip_format(v)  # pyright: ignore[reportUnknownArgumentType]
                for k, v in s.items()  # pyright: ignore[reportUnknownVariableType]
                if s.get("type") != "string" or k != "format"  # ty: ignore[invalid-argument-type] # pyright: ignore[reportUnknownMemberType]
            },
        )

    if isinstance(s, list):
        # json schemas keep alternatives in lists (anyOf, oneOf, allOf, prefixItems)
        return cast("T", [strip_format(v) for v in s])  # pyright: ignore[reportUnknownVariableType]

    return s


@router.get("/schema/{fn_name}")
def get_job_schema(fn_name: str) -> GetJsonSchemaResponse:
    """Get the schema of the parameters for the provided job.

    \f
    Args:
        fn_name: the job's full import path, or its trailing parts (such as
            ``simple.copy``) if they name one job.

    Returns:
        GetJsonSchemaResponse: the job's full name and the json schema of its
        parameters.

    Raises:
        HTTPException: 404 if no job (or no parameters model) matches, 409 if
            several jobs match.

    Example:
        .. testcode::

            from fastapi import HTTPException

            from pyantz.api.endpoints.get_parameters.endpoints import get_job_schema

            print(get_job_schema("simple.copy").fn_path)
            try:
                get_job_schema("copy")
            except HTTPException as exc:
                print(exc.status_code)

        .. testoutput::

            pyantz.jobs.files.simple.copy
            409

    """  # noqa: D301
    matching_fn = get_registered_functions(fn_name)
    if len(matching_fn) == 0:
        raise HTTPException(status_code=404, detail=f"No such job: {fn_name}") from None
    if len(matching_fn) > 1:
        candidates = sorted(fn.PYANTZ_NAME for fn in matching_fn)  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
        raise HTTPException(
            status_code=409,
            detail=f"Multiple matching jobs for {fn_name}: {', '.join(candidates)}",
        ) from None

    fn = matching_fn[0]

    if hasattr(fn, "PYANTZ_VALIDATION_MODEL"):
        param_mod: BaseModel = fn.PYANTZ_VALIDATION_MODEL  # type: ignore[attr-defined] # ty: ignore[invalid-assignment]

        json_schema = param_mod.model_json_schema()
        json_schema = strip_format(json_schema)

        return GetJsonSchemaResponse(
            fn_path=fn.PYANTZ_NAME,  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
            json_schema=json_schema,
        )

    raise HTTPException(status_code=404, detail=f"No parameter model for: {fn_name}")
