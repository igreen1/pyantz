"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_job_submit_response"""

from typing import Optional

from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiJobSubmitResponse(BaseModel):
    """v0.0.42_openapi_job_submit_response"""

    job_id: Optional[int]
    step_id: Optional[str]
    job_submit_user_msg: Optional[str]
    meta: Optional[OpenapiMeta]
    error: Optional[list[OpenapiError]]
    warning: Optional[list[OpenapiWarning]]
