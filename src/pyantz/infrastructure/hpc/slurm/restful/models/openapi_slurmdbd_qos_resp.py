"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_slurmdbd_qos_resp"""

from pydantic import BaseModel
from typing import Optional

from .qos import Qos
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .openapi_error import OpenapiError

class OpenapiSlurmdbdQosResp(BaseModel):
    """v0.0.42 OPENAPI_SLURMDBD_QOS_RESP"""
    qos: list[Qos]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
