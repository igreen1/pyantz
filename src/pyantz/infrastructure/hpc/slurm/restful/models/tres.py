"""https://slurm.schedmd.com/rest_api.html#v0.0.42_tres"""

from typing import Optional

from pydantic import BaseModel


class Tres(BaseModel):
    """v0.0.42 TRES"""

    type: str
    name: Optional[str] = None
    id: Optional[int] = None
    count: Optional[int] = None
