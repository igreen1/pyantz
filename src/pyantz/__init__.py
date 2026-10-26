"""PyAntz is a simple local DAGster/Airflow-style data pipeline tool.

It is useful if you want to quickly run some small things locally or on a
slurm cluster without setting up specialized worker nodes.
"""

from __future__ import annotations

from pyantz.infrastructure.runner.starter import start

__all__ = [
    "start",
]

__version__ = "2.0.1"
