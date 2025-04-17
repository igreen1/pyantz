"""https://slurm.schedmd.com/rest_api.html#v0.0.42_stats_msg_rpc_dump"""

from pydantic import BaseModel


class StatsMsgRpcDump(BaseModel):
    """v0.0.42 STATS_MSG_RPC_DUMP"""

    type_id: int
    message_type: str
    count: list[str]
