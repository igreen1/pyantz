"""https://slurm.schedmd.com/rest_api.html#v0.0.42_kill_jobs_msg"""

from typing import Optional

from pydantic import BaseModel


class KillJobsMsg(BaseModel):
    """v0.0.42 KILL_JOBS_MSG"""

    account: Optional[str]
    flags: Optional[list[str]]
    job_name: Optional[str]
    jobs: Optional[list[str]]
    partition: Optional[str]
    qos: Optional[str]
    reservation: Optional[str]
    signal: Optional[str]
    job_state: Optional[list[str]]
    user_id: Optional[str]
    user_name: Optional[str]
    wckey: Optional[str]
    nodes: Optional[list[str]]
