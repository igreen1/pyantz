"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_tres_resp"""

from pydantic import BaseModel
from typing import Optional
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .tres import Tres

class OpenapiTresResp(BaseModel):
    """v0.0.42 OPENAPI_TRES_RESP"""
    TRES: list[Tres]
    meta: Optional[OpenapiMeta]
    warnings: Optional[list[OpenapiWarning]]
    errors: Optional[list[OpenapiError]]
