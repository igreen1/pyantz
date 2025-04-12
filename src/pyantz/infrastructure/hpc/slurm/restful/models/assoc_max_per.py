"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max_per"""

from typing import Optional

from pydantic import BaseModel

from .assoc_max_per_account import AssocMaxPerAccount


class AssocMaxPer(BaseModel):
    """v0.0.42 ASSOC_MAX_PER"""

    account: Optional[AssocMaxPerAccount]
