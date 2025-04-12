"""https://slurm.schedmd.com/rest_api.html#v0_0_42_accounting_allocated"""

from typing import Optional

from pydantic import BaseModel


class AccountingAllocated(BaseModel):
    """v0.0.42 ACCOUNTING_ALLOCATED"""

    seconds: Optional[int] = None
