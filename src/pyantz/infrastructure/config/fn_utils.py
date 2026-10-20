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
    if len(name_components) < 2 or not all(name_components):  # noqa: PLR2004
        msg = f"Cannot import '{key}': expected 'package.module.name'"
        raise ValueError(msg)

    # import the longest prefix that is a module and look the rest up on it,
    # which allows names like `package.module.Class.method`
    last_error: ImportError | None = None
    for split in range(len(name_components) - 1, 0, -1):
        mod_name = ".".join(name_components[:split])
        try:
            item: Any = importlib.import_module(mod_name)
        except ModuleNotFoundError as exc:
            if exc.name is not None and mod_name.startswith(exc.name):
                last_error = exc
                continue  # this prefix isn't a module, so try a shorter one
            msg = f"Cannot import '{key}': unable to import module '{mod_name}' ({exc})"
            raise ValueError(msg) from exc
        except ImportError as exc:
            msg = f"Cannot import '{key}': unable to import module '{mod_name}' ({exc})"
            raise ValueError(msg) from exc
        try:
            for attribute in name_components[split:]:
                item = getattr(item, attribute)
        except AttributeError as exc:
            msg = (
                f"Cannot import '{key}': Module '{mod_name}' has no attribute "
                f"'{attribute}'"
            )
            raise ValueError(msg) from exc
        return item

    mod_name = ".".join(name_components[:-1])
    msg = f"Cannot import '{key}': unable to import module '{mod_name}' ({last_error})"
    raise ValueError(msg) from last_error
