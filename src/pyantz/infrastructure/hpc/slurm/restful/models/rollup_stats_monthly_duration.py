"""https://slurm.schedmd.com/rest_api.html#v0_0_42_rollup_stats_monthly_duration"""

from pydantic import BaseModel, Field
from typing import Optional

class RollupStatsMonthlyDuration(BaseModel):
    """v0.0.42 ROLLUP_STATS_MONTHLY_DURATION"""
    last: Optional[int]
    max_: Optional[int] = Field(..., alias='max')
    time: Optional[int]
