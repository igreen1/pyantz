"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_rpc"""

from pydantic import BaseModel
from typing import Optional

from .stats_rpc_time import StatsRpcTime

class StatsRpc(BaseModel):
    """v0.0.42 StatsRpc"""
    rpc: Optional[str]
    count: Optional[int]
    time: Optional[StatsRpcTime]
