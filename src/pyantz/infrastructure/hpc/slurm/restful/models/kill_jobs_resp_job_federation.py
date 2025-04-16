"""https://slurm.schedmd.com/rest_api.html#v0_0_42_kill_jobs_resp_job_federation"""

from typing import Optional

from pydantic import BaseModel


class KillJobsRespJobFederation(BaseModel):
    """v0.0.42 KILL_JOBS_RESP_JOB_FEDERATION"""

    sibling: Optional[str]
