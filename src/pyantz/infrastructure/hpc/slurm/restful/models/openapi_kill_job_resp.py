"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_kill_job_resp"""

from typing import Optional

from pydantic import BaseModel

from .kill_jobs_resp_job import KillJobsRespJob


class OpenapiKillJobResp(BaseModel):
    """v0.0.42 OPENAPI_KILL_JOB_RESP"""

    status: list[KillJobsRespJob]
    meta: Optional[dict]
    error: Optional[list[str]]
    warning: Optional[list[str]]
