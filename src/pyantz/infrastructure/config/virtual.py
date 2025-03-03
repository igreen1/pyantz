"""Code for the setup of virtual configurations"""

from typing import Any, Literal, TYPE_CHECKING
from collections.abc import Mapping

from pydantic import BaseModel
from pyantz.infrastructure.config.get_functions import get_function_by_name
if TYPE_CHECKING:
    from pyantz.infrastructure.config.get_functions


class VirtualJobConfig(BaseModel, frozen=True):
    """VirtualJobConfig is a single node for a more complex assembly of jobs
    
    VirtualJobs don't have any job code to run; they just create a set of real
        jobs to run for user ease. 
    They are a **series** of jobs and will be placed in stages as such

    For example, a job may be "make_json_and_populate_fields" which will run
        1. `touch` json file to make the actual file
        2. a series of edit json jobs to edit the fields in that json

    or another job may be "filter_parquet_or" 
        1. adds a new index to the parquet file 
        2. Filters by each OR predicate
        3. Unions the OR predicates, dropping on the newly created index
        4. Drops the index column

    """
    type: Literal["virtual"]
    name: str
    parameters: Mapping[str, Any]


def resolve_virtual_config(virtual_config: VirtualJobConfig) -> "list[type[_AbtractJobConfig]]"