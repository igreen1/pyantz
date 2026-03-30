"""Get parameters to help the user setup their function."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions

from .models import GetJsonSchemaResponse

if TYPE_CHECKING:
    from pydantic import BaseModel

router = APIRouter(prefix="/jobs")


def strip_format[T](s: T) -> T:
    """Strip `format` from string fields."""
    if isinstance(s, dict):
        return cast(
            "T",
            {
                k: strip_format(v)  # pyright: ignore[reportUnknownArgumentType]
                for k, v in s.items()  # pyright: ignore[reportUnknownVariableType]
                if s.get("type") != "string" or k != "format"  # ty: ignore[invalid-argument-type] # pyright: ignore[reportUnknownMemberType]
            },
        )

    return s


@router.get("/schema/{fn_name}")
def get_job_schema(fn_name: str) -> GetJsonSchemaResponse:
    """Get the schema of the parameters for the provided job."""
    matching_fn = get_registered_functions(fn_name)
    if len(matching_fn) == 0:
        raise HTTPException(status_code=404, detail=f"No such job: {fn_name}") from None
    if len(matching_fn) > 1:
        raise HTTPException(
            status_code=404, detail=f"Multiple matching jobs for: {fn_name}"
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

    raise HTTPException(status_code=500, detail="No parameter model for: {fn_name}")
