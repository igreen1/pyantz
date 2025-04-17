"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_accounts_add_cond_resp"""

from typing import Optional

from pydantic import BaseModel


class OpenapiWarning(BaseModel):
    """v0.0.42 OPENAPI_WARNING"""

    description: Optional[str]
    source: Optional[str]
