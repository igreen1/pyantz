"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_msg"""

from typing import Optional

from pydantic import BaseModel

from .bf_exit_fields import BfExitFields
from .schedule_exit_fields import ScheduleExitFields
from .stats_msg_rpc_dump import StatsMsgRpcDump
from .stats_msg_rpc_queue import StatsMsgRpcQueue
from .stats_msg_rpc_type import StatsMsgRpcType
from .stats_msg_rpc_user import StatsMsgRpcUser
from .uint64_no_val_struct import Uint64NoValStruct


class StatsMsg(BaseModel):
    """v0.0.42 STATS_MSG"""

    parts_packed: Optional[int]
    req_time: Optional[Uint64NoValStruct]
    req_time_start: Optional[Uint64NoValStruct]
    server_thread_count: Optional[int]
    agent_queue_size: Optional[int]
    agent_count: Optional[int]
    agent_thread_count: Optional[int]
    dbd_agent_queue_size: Optional[int]
    gettimeofday_latency: Optional[int]
    schedule_cycle_max: Optional[int]
    schedule_cycle_last: Optional[int]
    schedule_cycle_sum: Optional[int]
    schedule_cycle_total: Optional[int]
    schedule_cycle_mean: Optional[int]
    schedule_cycle_mean_depth: Optional[int]
    schedule_cycle_per_minute: Optional[int]
    schedule_cycle_depth: Optional[int]
    schedule_exit: Optional[ScheduleExitFields]
    schedule_queue_length: Optional[int]
    jobs_submitted: Optional[int]
    jobs_starts: Optional[int]
    jobs_completed: Optional[int]
    jobs_canceled: Optional[int]
    jobs_failed: Optional[int]
    jobs_pending: Optional[int]
    jobs_running: Optional[int]
    jobs_states_ts: Optional[Uint64NoValStruct]
    bf_backfilled_jobs: Optional[int]
    bf_last_backfilled_jobs: Optional[int]
    bf_backfilled_het_jobs: Optional[int]
    bf_cycle_counter: Optional[int]
    bf_cycle_mean: Optional[int]
    bf_depth_mean: Optional[int]
    bf_depth_mean_try: Optional[int]
    bf_cycle_sum: Optional[int]
    bf_cycle_last: Optional[int]
    bf_cycle_max: Optional[int]
    bf_exit: Optional[BfExitFields]
    bf_last_depth: Optional[int]
    bf_last_depth_try: Optional[int]
    bf_depth_sum: Optional[int]
    bf_depth_try_sum: Optional[int]
    bf_queue_len: Optional[int]
    bf_queue_len_mean: Optional[int]
    bf_queue_len_sum: Optional[int]
    bf_table_size: Optional[int]
    bf_table_size_sum: Optional[int]
    bf_table_size_mean: Optional[int]
    bf_when_last_cycle: Optional[Uint64NoValStruct]
    bf_active: Optional[bool]
    rpcs_by_message_type: Optional[list[StatsMsgRpcType]]
    rpcs_by_user: Optional[list[StatsMsgRpcUser]]
    pending_rpcs: Optional[list[StatsMsgRpcQueue]]
    pending_rpcs_by_hostlist: Optional[list[StatsMsgRpcDump]]
