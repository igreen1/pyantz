"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job"""

from typing import Optional

from pydantic import BaseModel

from .assoc_short import AssocShort
from .job_array import JobArray
from .job_comment import JobComment
from .job_het import JobHet
from .job_mcs import JobMcs
from .job_required import JobRequired
from .job_reservation import JobReservation
from .job_state import JobState
from .job_time import JobTime
from .job_tres import JobTres
from .process_exit_code_verbose import ProcessExitCodeVerbose
from .step import Step
from .uint32_no_val_struct import Uint32NoValStruct
from .wckey_tag_struct import WckeyTagStruct


class Job(BaseModel):
    """v0.0.42 JOB"""

    account: Optional[str]
    comment: Optional[JobComment]
    allocation_nodes: Optional[int]
    array: Optional[JobArray]
    association: Optional[AssocShort]
    block: Optional[str]
    cluster: Optional[str]
    constraints: Optional[str]
    container: Optional[str]
    derived_exit_code: Optional[ProcessExitCodeVerbose]
    time: Optional[JobTime]
    exit_code: Optional[ProcessExitCodeVerbose]
    extra: Optional[str]
    failed_node: Optional[str]
    flags: Optional[list[str]]
    group: Optional[str]
    het: Optional[JobHet]
    job_id: Optional[int]
    name: Optional[str]
    licenses: Optional[str]
    mcs: Optional[JobMcs]
    nodes: Optional[str]
    partition: Optional[str]
    hold: Optional[bool]
    priority: Optional[Uint32NoValStruct]
    qos: Optional[str]
    qosreq: Optional[str]
    required: Optional[JobRequired]
    kill_request_user: Optional[str]
    restart_cnt: Optional[int]
    reservation: Optional[JobReservation]
    script: Optional[str]
    stdin_expanded: Optional[str]
    stdout_expanded: Optional[str]
    stderr_expanded: Optional[str]
    stdout: Optional[str]
    stderr: Optional[str]
    stdin: Optional[str]
    state: Optional[JobState]
    steps: Optional[list[Step]]
    submit_line: Optional[str]
    tres: Optional[JobTres]
    used_gres: Optional[str]
    user: Optional[str]
    wckey: Optional[WckeyTagStruct]
    working_directory: Optional[str]
