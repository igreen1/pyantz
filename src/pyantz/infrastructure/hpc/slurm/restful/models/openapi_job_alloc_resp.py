"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_job_alloc_resp"""

from typing import Optional

from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiJobAllocResp(BaseModel):
    """v0.0.42 OPENAPI_JOB_ALLOC_RESP"""

    job_id: Optional[int]
    job_submit_user_msg: Optional[str]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
