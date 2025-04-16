"""https://slurm.schedmd.com/rest_api.html#v0.0.42_license"""

from typing import Optional

from pydantic import BaseModel


class License(BaseModel):
    """v0.0.42 License"""

    LicenseName: Optional[str]
    Total: Optional[int]
    User: Optional[int]
    Free: Optional[int]
    Remote: Optional[bool]
    Reserved: Optional[int]
    LastConsumed: Optional[int]
    LastDeficit: Optional[int]
    LastUpdate: Optional[int]
