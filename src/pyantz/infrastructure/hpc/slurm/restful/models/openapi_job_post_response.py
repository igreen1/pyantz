"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_job_post_response"""

from typing import Optional

from pydantic import BaseModel

from .job_array_response_msg_entry import JobArrayResponseMsgEntry
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiJobPostResponse(BaseModel):
    """v0.0.42 OPENAPI_JOB_POST_RESPONSE"""

    results: Optional[list[JobArrayResponseMsgEntry]]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
