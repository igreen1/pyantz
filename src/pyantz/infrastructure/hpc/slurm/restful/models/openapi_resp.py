"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_resp"""

from typing import Optional
from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning

class OpenapiResp(BaseModel):
    """v0.0.42 OPENAPI_RESP"""
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
