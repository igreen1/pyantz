"""PyAntz is a simple local DAGster/Airflow-style data pipeline tool.

It is useful if you want to quickly run some small things locally or on a
slurm cluster without setting up specialized worker nodes.
"""

from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local

if TYPE_CHECKING:
    from collections.abc import Mapping


def start(config: _InitialConfig[Any] | Mapping[str, Any]) -> None:
    """Start running the various jobs.

    This is a blocking operation if running locally.
    """
    # if not loaded, check it
    loaded_config: _InitialConfig[Any] = _InitialConfig.model_validate(config) # pyright: ignore[reportUnknownVariableType]
    if loaded_config.submitter.type_ == "local_proc":
        # start local runner
        _start_local(loaded_config)
    else:
        raise ValueError


__all__ = [
    "start",
]
