"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_rec"""

from pydantic import BaseModel
from typing import Optional

from .rollup_stats import RollupStats
from .stats_rpc import StatsRpc
from .stats_user import StatsUser

class StatsRec(BaseModel):
    """v0.0.42 STATS_REC"""
    time_start: Optional[int]
    rollups: Optional[RollupStats]
    RPCs: Optional[list[StatsRpc]]
    users: Optional[list[StatsUser]]
