"""https://slurm.schedmd.com/rest_api.html#v0.0.42_schedule_exit_fields"""

from typing import Optional

from pydantic import BaseModel


class ScheduleExitFields(BaseModel):
    """v0.0.42 SCHEDULE_EXIT_FIELDS"""

    end_job_queue: Optional[int]
    default_queue_depth: Optional[int]
    max_job_start: Optional[int]
    max_rpc_cnt: Optional[int]
    max_sched_time: Optional[int]
    licenses: Optional[int]
