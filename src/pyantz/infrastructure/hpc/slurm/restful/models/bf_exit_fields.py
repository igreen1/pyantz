"""https://slurm.schedmd.com/rest_api.html#v0.0.42_bf_exit_fields"""

from typing import Optional

from pydantic import BaseModel


class BfExitFields(BaseModel):
    """v0.0.42 BF_EXIT_FIELDS"""

    end_job_queue: Optional[int]
    bf_max_job_start: Optional[int]
    bf_max_job_test: Optional[int]
    bf_max_time: Optional[int]
    bf_node_space_size: Optional[int]
    state_changed: Optional[int]
