"""https://slurm.schedmd.com/rest_api.html#v0.0.42_coord"""

from typing import Optional

from pydantic import BaseModel


class Coord(BaseModel):
    """V0.0.42 Coord"""

    name: str
    direct: Optional[bool] = None
