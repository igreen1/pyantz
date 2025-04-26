"""https://slurm.schedmd.com/rest_api.html#v0_0_42_rollup_stats_daily"""

from pydantic import BaseModel
from typing import Optional

from .rollup_stats_daily_duration import RollupStatsDailyDuration

class RollupStatsDaily(BaseModel):
    """v0.0.42 ROLLUP_STATS_DAILY"""
    count: Optional[int]
    last_run: Optional[int]
    duration: Optional[RollupStatsDailyDuration]
