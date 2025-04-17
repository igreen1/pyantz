"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_msg_rpc_type"""

from pydantic import BaseModel

from .uint64_no_val_struct import Uint64NoValStruct


class StatsMsgRpcType(BaseModel):
    """v0.0.42 STATS_MSG_RPC_TYPE"""

    type_id: int
    message_type: str
    count: int
    queued: int
    dropped: int
    cycle_last: int
    cycle_max: int
    total_time: int
    average_time: Uint64NoValStruct
