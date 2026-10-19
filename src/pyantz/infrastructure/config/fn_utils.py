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
    """Serialize the function so that others can import it dynamically.

    Raises:
        ValueError: if the function can't be imported by name (lambdas and
            functions defined inside other functions)

    """
    mod_name: str = fn.__module__ if hasattr(fn, "__module__") else "anonymous"
    qualified_name: str = str(
        getattr(fn, "__qualname__", getattr(fn, "__name__", "some_fn")),
    )
    if "<lambda>" in qualified_name or "<locals>" in qualified_name:
        msg = (
            f"Function {mod_name}.{qualified_name} is not importable; "
            "define it at module level"
        )
        raise ValueError(msg)
    return mod_name + "." + qualified_name


def import_function_by_name(fn_path: Any) -> JobFunctionType:  # noqa: ANN401
    """Import a function by its name."""
    return import_module_item_by_name(fn_path)


def import_module_item_by_name(key: Any) -> Any:  # noqa: ANN401
    """Import a parameters model by its name."""
    if not isinstance(key, str):
        return key

    name_components = key.split(".")
    # import the longest prefix that is a module and look the rest up on it,
    # which allows names like `package.module.Class.method`
    for split in range(len(name_components) - 1, 0, -1):
        mod_name = ".".join(name_components[:split])
        try:
            item: Any = importlib.import_module(mod_name)
        except ModuleNotFoundError as exc:
            if exc.name is not None and mod_name.startswith(exc.name):
                continue  # this prefix isn't a module, so try a shorter one
            raise
        for attribute in name_components[split:]:
            item = getattr(item, attribute)
        return item

    return importlib.import_module(".".join(name_components[:-1]))
