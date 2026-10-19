"""Utilities for (de)serialising Python callables and class references.

Functions are stored in configs as fully-qualified dotted import paths
(e.g. ``"pyantz.jobs.files.simple.copy"``).  :func:`serialize_function`
converts a callable back to that string, and :func:`import_module_item_by_name`
dynamically imports it again at runtime.
"""

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
    return import_module_item_by_name(fn_path)


def import_module_item_by_name(key: Any) -> Any:  # noqa: ANN401
    """Import a parameters model by its name."""
    if not isinstance(key, str):
        return key

    name_components = key.split(".")
    mod_name = ".".join(name_components[:-1])
    fn_name = name_components[-1]
    if not mod_name or not fn_name:
        msg = f"Cannot import '{key}': expected 'package.module.name'"
        raise ValueError(msg)

    try:
        mod = importlib.import_module(mod_name)
    except ImportError as exc:
        msg = f"Cannot import '{key}': unable to import module '{mod_name}' ({exc})"
        raise ValueError(msg) from exc
    try:
        return getattr(mod, fn_name)
    except AttributeError as exc:
        msg = f"Cannot import '{key}': Module '{mod_name}' has no attribute '{fn_name}'"
        raise ValueError(msg) from exc
