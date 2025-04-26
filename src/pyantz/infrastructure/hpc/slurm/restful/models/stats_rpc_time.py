"""https://slurm.schedmd.com/rest_api.html#v0_0_42_stats_rpc_time"""

from pydantic import BaseModel
from typing import Optional

class StatsRpcTime(BaseModel):
    """v0.0.42 StatsRpcTime"""
    average: Optional[int]
    total: Optional[int]
