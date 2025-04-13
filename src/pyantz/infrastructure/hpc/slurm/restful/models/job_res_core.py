"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_res_core"""

from pydantic import BaseModel


class JobResCore(BaseModel):
    """v0.0.42 JOB_RES_CORE"""

    index: int
    status: list[str]
