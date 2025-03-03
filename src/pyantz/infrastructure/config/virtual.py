"""Code for the setup of virtual configurations"""

from typing import Any, Literal, Mapping

from pydantic import BaseModel


class VirtualJobConfig(BaseModel, frozen=True):
    type: Literal["virtual_config"]
    name: str
    parameters: Mapping[str, Any]
