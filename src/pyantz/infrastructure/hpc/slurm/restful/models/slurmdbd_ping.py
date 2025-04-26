"""https://slurm.schedmd.com/rest_api.html#v0.0.42_slurmdbd_ping"""

from typing import Optional
from pydantic import BaseModel

class SlurmdbdPing(BaseModel):
    """v0.0.42 SLURMDBD_PING"""
    hostname: str
    responding: bool
    latency: int
    primary: bool
