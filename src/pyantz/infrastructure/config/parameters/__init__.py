"""Functionality to mark functions to strongly type the parameters."""

from .compile_check import get_params
from .decorators import (
    add_parameters,
    is_virtual,
    mark_virtual,
    no_submit_fn,
    update_deps,
)

__all__ = [
    "add_parameters",
    "get_params",
    "is_virtual",
    "mark_virtual",
    "no_submit_fn",
    "update_deps",
]
