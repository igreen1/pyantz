"""https://slurm.schedmd.com/rest_api.html#v0.0.42_reservation_core_spec"""

from typing import Optional

from pydantic import BaseModel


class ReservationCoreSpec(BaseModel):
    """v0.0.42 RESERVATION_CORE_SPEC"""

    node: Optional[str]
    core: Optional[str]
