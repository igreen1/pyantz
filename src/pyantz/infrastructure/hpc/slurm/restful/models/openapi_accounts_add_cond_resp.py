"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_accounts_add_cond_resp"""

from typing import Optional

from pydantic import BaseModel

from .account_short import AccountShort
from .accounts_add_cond import AccountsAddCond
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiAccountsAddCondResp(BaseModel):
    """v0.0.42 OpenapiAccountsAddCondResp"""

    association_condition: Optional[AccountsAddCond]
    account: Optional[AccountShort]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
