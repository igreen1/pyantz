"""https://slurm.schedmd.com/rest_api.html#v0_0_42_rollup_stats_hourly"""

from pydantic import BaseModel
from typing import Optional
from .rollup_stats_hourly_duration import RollupStatsHourlyDuration

class RollupStatsHourly(BaseModel):
    """v0.0.42 ROLLUP_STATS_HOURLY"""
    count: Optional[int]
    last_run: Optional[int]
    duration: Optional[RollupStatsHourlyDuration]
