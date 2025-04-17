"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_error"""

from typing import Optional

from pydantic import BaseModel


class OpenapiError(BaseModel):
    """v0.0.42 OPENAPI_ERROR"""

    description: Optional[str]
    error_number: Optional[int]
    error: Optional[str]
    source: Optional[str]
