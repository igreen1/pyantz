"""https://slurm.schedmd.com/rest_api.html#v0.0.42_kill_jobs_resp_job"""

from typing import Optional

from pydantic import BaseModel

from .kill_jobs_resp_job_error import KillJobsRespJobError
from .kill_jobs_resp_job_federation import KillJobsRespJobFederation
from .uint32_no_val_struct import Uint32NoValStruct


class KillJobsRespJob(BaseModel):
    """v0.0.42 KILL_JOBS_RESP_JOB"""

    error: Optional[KillJobsRespJobError]
    step_id: str
    job_id: Uint32NoValStruct
    federation: Optional[KillJobsRespJobFederation]
