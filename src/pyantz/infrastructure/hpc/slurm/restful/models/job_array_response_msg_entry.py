"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_array_response_msg_entry"""

from typing import Optional

from pydantic import BaseModel


class JobArrayResponseMsgEntry(BaseModel):
    """v0.0.42 JOB_ARRAY_RESPONSE_MSG_ENTRY"""

    job_id: Optional[int]
    step_id: Optional[str]
    error: Optional[str]
    error_code: Optional[int]
    why: Optional[str]
