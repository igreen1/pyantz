"""https://slurm.schedmd.com/rest_api.html#v0.0.42_assoc"""

from typing import Optional

from pydantic import BaseModel

from .accounting import Accounting
from .assoc_default import AssocDefault
from .assoc_max import AssocMax
from .assoc_min import AssocMin


class Assoc(BaseModel):
    """v0.0.42 ASSOC"""

    accounting: Optional[Accounting]
    account: Optional[str]
    cluster: Optional[str]
    comment: Optional[str]
    default: Optional[AssocDefault]
    flags: Optional[list[str]]
    max: Optional[AssocMax]
    id: Optional[int]
    is_default: Optional[bool]
    lineage: Optional[str]
    min: Optional[AssocMin]
    parent_account: Optional[str]
    partition: Optional[str]
    qos: Optional[list[str]]
    shares_raw: Optional[int]
    user: str
