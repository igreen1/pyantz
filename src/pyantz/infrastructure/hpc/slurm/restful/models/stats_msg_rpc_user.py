"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_msg_rpc_user"""

from pydantic import BaseModel

from .uint64_no_val_struct import Uint64NoValStruct


class StatsMsgRpcUser(BaseModel):
    """v0.0.42 STATS_MSG_RPC_USER"""

    user_id: int
    user: str
    count: int
    total_time: int
    average_time: Uint64NoValStruct
