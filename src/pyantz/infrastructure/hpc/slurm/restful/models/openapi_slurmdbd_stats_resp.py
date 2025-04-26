"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_slurmdbd_stats_resp"""

from pydantic import BaseModel
from typing import Optional

from .stats_rec import StatsRec
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .openapi_error import OpenapiError

class OpenapiSlurmdbdStatsResp(BaseModel):
    """v0.0.42 OPENAPI_SLURMDBD_STATS_RESP"""
    statistisc: Optional[StatsRec]
    meta: Optional[OpenapiMeta]
    warnings: Optional[list[OpenapiWarning]]
    errors: Optional[list[OpenapiError]]
