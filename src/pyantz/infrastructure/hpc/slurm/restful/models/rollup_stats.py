"""https://slurm.schedmd.com/rest_api.html#v0.0.42_rollup_stats"""

from pydantic import BaseModel
from typing import Optional

from .rollup_stats_hourly import RollupStatsHourly
from .rollup_stats_daily import RollupStatsDaily
from .rollup_stats_monthly import RollupStatsMonthly

class RollupStats(BaseModel):
    """v0.0.42 ROLLUP_STATS"""
    hourly: Optional[RollupStatsHourly]
    daily: Optional[RollupStatsDaily]
    monthly: Optional[RollupStatsMonthly]
