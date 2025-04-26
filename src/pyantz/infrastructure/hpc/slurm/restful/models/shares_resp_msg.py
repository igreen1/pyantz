"""https://slurm.schedmd.com/rest_api.html#v0.0.42_shares_resp_msg"""


from .assoc_shares_obj_wrap import AssocSharesObjWrap

from pydantic import BaseModel
from typing import Optional

class SharesRespMsg(BaseModel):
    """v0.0.42 SHARES_RESP_MSG"""

    shares: Optional[list[AssocSharesObjWrap]]
    total_shares: Optional[int]
