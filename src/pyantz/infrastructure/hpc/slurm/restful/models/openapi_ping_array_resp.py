"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_ping_array_resp"""

from typing import Optional

from pydantic import BaseModel

from .controller_ping import ControllerPing
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiPingArrayResp(BaseModel):
    """v0.0.42 OPENAPI_PING_ARRAY_RESP"""

    pings: list[ControllerPing]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
