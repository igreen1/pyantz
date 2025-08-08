"""Configuration for the Local Submitter.

num_concurrent_jobs controls how many processes to spawn for the manager
"""

from typing import Literal

from pydantic import BaseModel


class LocalSubmitterConfig(BaseModel, frozen=True):
    """The configuration of the local submitter.

    num_concurrent_jobs (int): number of processes to run jobs
    """

    type: Literal["local"]
    name: str = "local submitter"
    num_concurrent_jobs: int = 1
