"""https://slurm.schedmd.com/rest_api.html#v0_0_42_user_default"""

from typing import Optional
from pydantic import BaseModel


class UserDefault(BaseModel):
    """v0.0.42 User Default"""
    account: Optional[str]
    wckey: Optional[str]
