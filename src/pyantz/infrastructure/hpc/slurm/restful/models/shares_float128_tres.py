"""https://slurm.schedmd.com/rest_api.html#v0.0.42_shares_float128_tres"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SharesFloat128Tres(BaseModel):
    """v0.0.42 SHARES_FLOAT128_TRES"""

    name: Optional[str]
    value: Optional[Decimal]
