"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_accounts_removed_resp"""

from typing import Optional

from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiAccountsRemovedResp(BaseModel):
    """v0.0.42 OPENAPI_ACCOUNTS_REMOVED_RESP"""

    removed_accounts: list[str]
    meta: Optional[OpenapiMeta]
    error: Optional[OpenapiError]
    warning: Optional[OpenapiWarning]
