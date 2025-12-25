"""PyAntz is a simple local DAGster/Airflow-style data pipeline tool.

It is useful if you want to quickly run some small things locally or on a
slurm cluster without setting up specialized worker nodes.
"""

from collections.abc import Mapping
from typing import Any as _Any

from pyantz.infrastructure.config import AnyRunner as _AnyRunner
from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local


def start(config: _InitialConfig[_AnyRunner] | Mapping[str, _Any]) -> None:
    """Start running the various jobs.

    This is a blocking operation if running locally.
    """
    if not isinstance(config, _InitialConfig):  # pyright: ignore[reportUnnecessaryIsInstance]
        config = _InitialConfig[_AnyRunner].model_validate(config)
    if config.submitter.type_ == "local_proc":
        # start local runner
        _start_local(config)
    else:
        raise ValueError


__all__ = [
    "start",
]
