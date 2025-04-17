"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_assocs_resp"""

from typing import Optional

from pydantic import BaseModel

from .assoc import Assoc
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiAssocsResp(BaseModel):
    """v0.0.42 OPENAPI_ASSOCS_RESP"""

    associations: list[Assoc]
    meta: Optional[OpenapiMeta]
    error: Optional[OpenapiError]
    warning: Optional[OpenapiWarning]
