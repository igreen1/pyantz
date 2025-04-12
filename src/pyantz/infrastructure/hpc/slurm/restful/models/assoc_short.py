"""https://slurm.schedmd.com/rest_api.html#v0.0.42_assoc_short"""

from typing import Optional

from pydantic import BaseModel


class AssocShort(BaseModel):
    """v0.0.42 ASSOC_SHORT"""

    account: Optional[str] = None
    cluster: Optional[str] = None
    partition: Optional[str] = None
    user: str
    id: Optional[int] = None
