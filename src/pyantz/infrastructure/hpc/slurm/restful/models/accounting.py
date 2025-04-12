"""https://slurm.schedmd.com/rest_api.html#v0.0.42_accounting"""

from typing import Optional

from pydantic import BaseModel

from .accounting_allocated import AccountingAllocated
from .tres import Tres


class Accounting(BaseModel):
    """v0.0.42 ACCOUNTING"""

    allocated: Optional[AccountingAllocated] = None
    id: Optional[int] = None
    id_alt: Optional[int] = None
    start: Optional[int] = None
    TRES: Optional[Tres] = None
