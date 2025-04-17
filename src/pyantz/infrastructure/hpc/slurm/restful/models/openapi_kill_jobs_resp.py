"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_kill_jobs_resp"""

from typing import Optional

from pydantic import BaseModel

from .kill_jobs_resp_job import KillJobsRespJob


class OpenapiKillJobsResp(BaseModel):
    """v0.0.42 OPENAPI_KILL_JOBS_RESP"""

    status: list[KillJobsRespJob]
    meta: Optional[dict]
    error: Optional[list[str]]
    warning: Optional[list[str]]
