"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_slurmdbd_ping_resp"""

from typing import Optional
from pydantic import BaseModel

from .slurmdbd_ping import SlurmdbdPing
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiSlurmdbdPingResp(BaseModel):
    """v0.0.42 OPENAPI_SLURMDBD_PING_RESP"""
    pints: list[SlurmdbdPing]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
