"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_shares_resp"""


from typing import Optional
from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .shares_resp_msg import SharesRespMsg

class OpenapiSharesResp(BaseModel):
    """v0.0.42 OPENAPI_SHARES_RESP"""

    shares: SharesRespMsg
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
