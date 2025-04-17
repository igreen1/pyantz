"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_instances_resp"""

from typing import Optional

from pydantic import BaseModel

from .instance import Instance
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiInstancesResp(BaseModel):
    """v0.0.42 OPENAPI_INSTANCES_RESP"""

    instances: list[Instance]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
