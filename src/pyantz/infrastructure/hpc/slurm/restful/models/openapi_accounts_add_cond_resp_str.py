"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_accounts_add_cond_resp_str"""

from typing import Optional

from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiAccountsAddCondRespStr(BaseModel):
    """v0.0.42 OPENAPI_ACCOUNTS_ADD_COND_RESP_STR"""

    added_accounts: str
    meta: Optional[OpenapiMeta]
    error: Optional[list[OpenapiError]]
    warning: Optional[list[OpenapiWarning]]
