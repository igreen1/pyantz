"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_slurmdbd_jobs_resp"""

from typing import Optional
from pydantic import BaseModel

from .job import Job
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning

class OpenapiSlurmdbdJobsResp(BaseModel):
    """v0.0.42 OPENAPI_SLURMDBD_JOBS_RESP"""

    jobs: list[Job]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
