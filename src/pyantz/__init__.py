"""PyAntz is a simple local DAGster/Airflow-style data pipeline tool.

It is useful if you want to quickly run some small things locally or on a
slurm cluster without setting up specialized worker nodes.
"""

from pyantz.infrastructure.config import AnyRunner as _AnyRunner
from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local


def start(config: _InitialConfig[_AnyRunner]) -> None:
    """Start running the various jobs.

    This is a blocking operation if running locally.
    """
    if config.submitter.type_ == "local_proc":
        # start local runner
        _start_local(config)
    else:
        raise ValueError


__all__ = [
    "start",
]
