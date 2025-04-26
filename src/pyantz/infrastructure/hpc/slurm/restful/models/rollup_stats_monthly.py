"""https://slurm.schedmd.com/rest_api.html#v0_0_42_rollup_stats_monthly"""

from pydantic import BaseModel
from typing import Optional

from .rollup_stats_monthly_duration import RollupStatsMonthlyDuration

class RollupStatsMonthly(BaseModel):
    """v0.0.42 ROLLUP_STATS_MONTHLY"""
    count: Optional[int]
    last_run: Optional[int]
    duration: Optional[RollupStatsMonthlyDuration]
