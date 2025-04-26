"""https://slurm.schedmd.com/rest_api.html#v0.0.42_user"""

from typing import Optional, List
from pydantic import BaseModel

from .assoc_short import AssocShort
from .coord import Coord
from .user_default import UserDefault
from .wckey import Wckey

class User(BaseModel):
    """v0.0.42 USER"""
    administrator_level: Optional[list[str]]
    associations: Optional[list[AssocShort]]
    coordinators: Optional[List[Coord]]
    default: Optional[UserDefault]
    flags: Optional[list[str]]
    name: str
    old_name: Optional[str]
    wckeys: Optional[list[Wckey]]
