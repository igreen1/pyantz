"""https://slurm.schedmd.com/rest_api.html#v0.0.42_accounts_add_cond"""

from typing import Optional

from pydantic import BaseModel

from .assoc_rec_set import AssocRecSet


class AccountsAddCond(BaseModel):
    """v0.0.42 ACCOUNTS_ADD_COND"""

    accounts: list[str]
    association: Optional[AssocRecSet]
    clusters: Optional[list[str]]
