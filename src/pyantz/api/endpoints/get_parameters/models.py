"""Data models used by the `get_parameters` endpoints."""

from __future__ import annotations

from pydantic import BaseModel, JsonValue


class GetJsonSchemaResponse(BaseModel):
    """Response with the json schema for the function."""

    # path to the function
    fn_path: str
    """Full import path of the job."""

    # json schema for that function
    json_schema: JsonValue
    """Json schema of the job's parameters."""
