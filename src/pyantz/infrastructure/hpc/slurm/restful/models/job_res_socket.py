"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_res_socket"""

from pydantic import BaseModel

from .job_res_core import JobResCore


class JobResSocket(BaseModel):
    """v0.0.42 JOB_RES_SOCKET"""

    index: int
    cores: list[JobResCore]
