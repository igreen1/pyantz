"""https://slurm.schedmd.com/rest_api.html#v0.0.42_account"""

from typing import Optional

from pydantic import BaseModel

from .assoc_short import AssocShort
from .coord import Coord


class Account(BaseModel):
    """v0.0.v42 ACCOUNT"""

    associations: Optional[AssocShort] = None
    coordinators: Optional[Coord] = None
    description: str
    name: str
    organization: str
    flags: Optional[list[str]] = None
