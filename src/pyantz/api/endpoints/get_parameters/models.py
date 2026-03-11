"""Data models used by the `get_parameters` endpoints."""

from pydantic import BaseModel, JsonValue


class GetJsonSchemaResponse(BaseModel):
    """Response with the json schema for the function."""

    # path to the function
    fn_path: str

    # json schema for that function
    json_schema: JsonValue
