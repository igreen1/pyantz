"""https://slurm.schedmd.com/rest_api.html#v0.0.42_account_short"""

from typing import Optional

from pydantic import BaseModel


class AccountShort(BaseModel):
    """v0.0.42 ACCOUNT_SHORT"""

    description: Optional[str]
    organziation: Optional[str]
