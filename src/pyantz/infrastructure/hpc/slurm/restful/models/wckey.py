"""https://slurm.schedmd.com/rest_api.html#v0.0.42_wckey"""

from typing import Optional
from pydantic import BaseModel

from .accounting import Accounting

class Wckey(BaseModel):
    accounting: Optional[list[Accounting]]
    cluster: str
    id: Optional[int]
    name: str
    user: str
    flags: Optional[list[str]]
