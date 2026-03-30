"""PyAntz is a simple local DAGster/Airflow-style data pipeline tool.

It is useful if you want to quickly run some small things locally or on a
slurm cluster without setting up specialized worker nodes.
"""

from typing import TYPE_CHECKING
from typing import Any as _Any

from pyantz.infrastructure.config import AnyRunner as _AnyRunner
from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local

if TYPE_CHECKING:
    from collections.abc import Mapping


def start(config: _InitialConfig[_AnyRunner] | Mapping[str, _Any]) -> None:
    """Start running the various jobs.

    This is a blocking operation if running locally.
    """
    # if not loaded, check it
    loaded_config = _InitialConfig[_AnyRunner].model_validate(config)
    if loaded_config.submitter.type_ == "local_proc":
        # start local runner
        print(loaded_config)
        _start_local(loaded_config)
    else:
        raise ValueError


__all__ = [
    "start",
]
