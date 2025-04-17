"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_msg_rpc_queue"""

from pydantic import BaseModel


class StatsMsgRpcQueue(BaseModel):
    """v0.0.42 STATS_MSG_RPC_QUEUE"""

    type_id: int
    message_type: str
    count: int
