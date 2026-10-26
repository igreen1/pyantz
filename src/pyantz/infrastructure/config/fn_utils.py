"""Utilities for (de)serialising Python callables and class references.

Functions are stored in configs as fully-qualified dotted import paths
(e.g. ``"pyantz.jobs.files.simple.copy"``).  :func:`serialize_function`
converts a callable back to that string, and :func:`import_module_item_by_name`
dynamically imports it again at runtime.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema

if TYPE_CHECKING:
    from pyantz.infrastructure.config.job import JobFunctionType


ALLOWED_MODULES_VARIABLE = "PYANTZ_ALLOWED_MODULES"
"""Environment variable holding the comma separated module prefixes which
configurations may import functions from; see :func:`_check_import_allowed`."""


def serialize_function(fn: Callable[..., Any]) -> str:
    """Serialize the function so that others can import it dynamically.

    Args:
        fn: the function (or class) to serialize.

    Returns:
        str: the full dotted import path of ``fn``.

    Raises:
        ValueError: if the function can't be imported by name (lambdas,
            functions defined inside other functions, and functions without a
            module, such as those made by code run with ``exec``)

    Example:
        .. testcode::

            from pyantz.infrastructure.config.fn_utils import serialize_function
            from pyantz.jobs.files.simple import copy

            print(serialize_function(copy))
            try:
                serialize_function(lambda: None)
            except ValueError:
                print("lambdas can't be imported by name")

        .. testoutput::

            pyantz.jobs.files.simple.copy
            lambdas can't be imported by name

    """
    # None for functions made by code run without a module, e.g., with `exec`
    mod_name: str | None = getattr(fn, "__module__", None)
    qualified_name: str = str(
        getattr(fn, "__qualname__", getattr(fn, "__name__", "some_fn")),
    )
    if mod_name is None or "<lambda>" in qualified_name or "<locals>" in qualified_name:
        location = mod_name or "<no module>"
        msg = (
            f"Function {location}.{qualified_name} is not importable; "
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

    Args:
        key: the full dotted name to be imported.

    Returns:
        None.

    Raises:
        ValueError: if the name is not allowed

    Example:
        .. testcode::

            import os

            from pyantz.infrastructure.config.fn_utils import _check_import_allowed

            os.environ["PYANTZ_ALLOWED_MODULES"] = "pyantz, my_package"
            try:
                _check_import_allowed("pyantz.jobs.files.simple.copy")  # allowed
                _check_import_allowed("os.system")
            except ValueError:
                print("os.system is not allowed")
            finally:
                del os.environ["PYANTZ_ALLOWED_MODULES"]

        .. testoutput::

            os.system is not allowed

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
    """Import a function by its name.

    Used to validate the ``function`` of a job; a value which isn't a string
    (such as the function itself) is returned unchanged.

    Args:
        fn_path: the function's full dotted import path, or the function.

    Returns:
        JobFunctionType: the imported function.

    Raises:
        ValueError: if the name can't be imported or isn't allowed by
            :data:`ALLOWED_MODULES_VARIABLE`.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.fn_utils import import_function_by_name

            fn = import_function_by_name("pyantz.jobs.testing.nop.do_nothing")
            print(fn.__name__)

        .. testoutput::

            do_nothing

    """
    return import_module_item_by_name(fn_path)


def import_module_item_by_name(key: Any) -> Any:  # noqa: ANN401
    """Import a parameters model by its name.

    Any item of a module can be imported, including attributes of classes such as
    ``package.module.Class.method``: the longest prefix of the name which is a
    module is imported, and the rest is looked up on it.

    Args:
        key: the item's full dotted import path; anything which isn't a string is
            returned unchanged.

    Returns:
        Any: the imported item.

    Raises:
        ValueError: if the name has fewer than two parts, its module can't be
            imported, the module lacks the item, or the name isn't allowed by
            :data:`ALLOWED_MODULES_VARIABLE`.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.fn_utils import (
                import_module_item_by_name,
            )

            print(import_module_item_by_name("pathlib.Path.home").__qualname__)
            try:
                import_module_item_by_name("pathlib.Missing")
            except ValueError as exc:
                print(exc)

        .. testoutput::

            Path.home
            Cannot import 'pathlib.Missing': Module 'pathlib' has no attribute 'Missing'

    """
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


_F = TypeVar("_F", bound=Callable[..., Any])

# a plain alias rather than a `type` statement: pydantic inlines it in the json
# schemas (a `type` alias becomes a named definition, losing the field's title)
ImportedCallable = Annotated[
    _F,
    BeforeValidator(import_function_by_name),
    PlainSerializer(serialize_function, return_type=str),
    WithJsonSchema({"type": "string", "format": "base64"}),
]
"""A field holding a function, given (and serialized) as its full import path.

Example:
    .. testcode::

        from collections.abc import Callable

        from pydantic import BaseModel

        from pyantz.infrastructure.config.fn_utils import ImportedCallable

        class Call(BaseModel):
            func: ImportedCallable[Callable[..., object]]

        call = Call(func="json.dumps")
        print(call.func([1]), call.model_dump())

    .. testoutput::

        [1] {'func': 'json.dumps'}

"""
