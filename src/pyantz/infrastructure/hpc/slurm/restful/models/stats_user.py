"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_user"""

from pydantic import BaseModel
from typing import Optional

from .stats_rpc_time import StatsRpcTime

class StatsUser(BaseModel):
    """v0.0.42 STATS_USER"""
    user: Optional[str]
    count: Optional[int]
    time: Optional[StatsRpcTime]
