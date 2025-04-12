"""https://slurm.schedmd.com/rest_api.html#v0.0.42_controller_ping"""

from typing import Optional

from pydantic import BaseModel


class ControllerPing(BaseModel):
    """v0.0.42 CONTROLLER_PING"""

    hostname: Optional[str]
    pinged: Optional[str]
    responding: Optional[bool]
    latency: Optional[int]
    mode: Optional[str]
    primary: Optional[bool]
