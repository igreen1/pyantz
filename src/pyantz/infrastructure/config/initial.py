"""Configuration of the analysis overall."""

from pydantic import BaseModel

from .pipeline import PipelineConfig

class InitialConfig(BaseModel):
    """Configuration of the overall system.

    Passed by the user and used to setup the system. This is the
    primary user configuration.
    """

    pipeline: PipelineConfig

    submitter: dict[str, None] # TODO
