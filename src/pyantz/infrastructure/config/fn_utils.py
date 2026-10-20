"""Utilities for (de)serialising Python callables and class references.

Functions are stored in configs as fully-qualified dotted import paths
(e.g. ``"pyantz.jobs.files.simple.copy"``).  :func:`serialize_function`
converts a callable back to that string, and :func:`import_module_item_by_name`
dynamically imports it again at runtime.
"""

import importlib
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pyantz.infrastructure.config.job import JobFunctionType


# comma separated module prefixes which configurations may import functions from
ALLOWED_MODULES_VARIABLE = "PYANTZ_ALLOWED_MODULES"


def serialize_function(fn: Callable[..., Any]) -> str:
    """Serialize the function so that others can import it dynamically."""
    mod_name: str = fn.__module__ if hasattr(fn, "__module__") else "anonymous"
    fn_name: str = str(fn.__name__) if hasattr(fn, "__name__") else "some_fn"
    return mod_name + "." + fn_name


def _check_import_allowed(key: str) -> None:
    """Refuse names outside of the modules listed in `PYANTZ_ALLOWED_MODULES`.

    The variable holds comma separated module prefixes (``pyantz,my_package``); a name
    is allowed if it is one of them or inside one (``pyantz.jobs.x`` for ``pyantz``).
    Unset or empty, everything is allowed: a configuration is code, and the person who
    runs it is trusted. Set it wherever configurations come from someone else. The
    check happens before importing, so modules that are not allowed never run.

    Raises:
        ValueError: if the name is not allowed

    """
    allowed = [
        prefix.strip()
        for prefix in os.environ.get(ALLOWED_MODULES_VARIABLE, "").split(",")
        if prefix.strip()
    ]
    if allowed and not any(
        key == prefix or key.startswith(prefix + ".") for prefix in allowed
    ):
        msg = (
            f"Cannot import '{key}': it is not inside one of the modules allowed by "
            f"{ALLOWED_MODULES_VARIABLE} ({', '.join(allowed)})"
        )
        raise ValueError(msg)


def import_function_by_name(fn_path: Any) -> JobFunctionType:  # noqa: ANN401
    """Import a function by its name."""
    return import_module_item_by_name(fn_path)


def import_module_item_by_name(key: Any) -> Any:  # noqa: ANN401
    """Import a parameters model by its name."""
    if not isinstance(key, str):
        return key

    _check_import_allowed(key)

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
