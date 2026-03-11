"""Utilities for (de)serializing functions."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pyantz.infrastructure.config.job import JobFunctionType


def serialize_function(fn: Callable[..., Any]) -> str:
    """Serialize the function so that others can import it dynamically."""
    mod_name: str = fn.__module__ if hasattr(fn, "__module__") else "anonymous"
    fn_name: str = str(fn.__name__) if hasattr(fn, "__name__") else "some_fn"
    return mod_name + "." + fn_name


def import_function_by_name(fn_path: Any) -> JobFunctionType:  # noqa: ANN401
    """Import a function by its name."""
    if not isinstance(fn_path, str):
        return fn_path

    name_components = fn_path.split(".")
    mod_name = ".".join(name_components[:-1])
    fn_name = name_components[-1]

    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)
