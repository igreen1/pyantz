"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_slurmdbd_qos_removed_resp"""

from typing import Optional
from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_warning import OpenapiWarning
from .openapi_meta import OpenapiMeta

class OpenapiSlurmdbdQosRemovedResp(BaseModel):
    """v0.0.42 OPENAPI_SLURMDBD_QOS_REMOVED_RESP"""
    removed: list[str]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
