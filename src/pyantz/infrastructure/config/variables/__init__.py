"""Fill in variables in the parameters.

Strings in a job's parameters may refer to variables as ``%{name}``. Variables may
refer to other variables, up to :data:`MAX_RESOLUTION_DEPTH` levels deep.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast

VARIABLE_REGEX = re.compile(r"(%{[^%{}]+})")
"""Matches a reference to a variable, such as ``%{name}``."""

MAX_RESOLUTION_DEPTH = 32
"""Maximum nesting of variables referring to other variables."""


def resolve_parameters(
    job_parameters: Mapping[str, Any],
    variables: Mapping[str, Any],
) -> tuple[Mapping[str, Any], bool]:
    """Resolve any variables in the job_parameters.

    Variables are demarked with %{VARIABLE_NAME}

    Args:
        job_parameters (Mapping[str, Any]): parameters to be passed to the function
        variables (Mapping[str, Any]): variables to put in the parameters

    Returns:
        tuple[Mapping[str, Any], bool]: parameters with the variables eagerly
        replaced, and True if some variables were detected and not replaced

    Raises:
        ValueError: if a variable refers to itself, directly or not.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.variables import resolve_parameters

            parameters, unresolved = resolve_parameters(
                {"path": "%{root}/%{name}.txt", "count": "%{n}", "other": "%{unset}"},
                {"root": "/data", "name": "run_%{n}", "n": 3},
            )
            print(parameters, unresolved)

        .. testoutput::

            {'path': '/data/run_3.txt', 'count': 3, 'other': '%{unset}'} True

    """
    logger = logging.getLogger(__name__)
    logger.debug("Resolving parameters")
    logger.debug("Pre resolution: %s", job_parameters)
    result = resolve_var_any(job_parameters, variables=variables)
    logger.debug("Post resolution %s", result)
    return result


def resolve_var_any[T](
    some_val: T,
    variables: Mapping[str, Any],
) -> tuple[T, bool]:
    """Resolve the variable and return it.

    Strings are resolved, and mappings, lists, tuples and sets are searched at
    any depth; anything else is returned unchanged.

    Args:
        some_val: the value to resolve.
        variables: the variables to fill in.

    Returns:
        tuple[T, bool]: value with variables interleaved and a boolean. if the
        boolean is true, a variable was detected but left unchanged.

    Raises:
        ValueError: if a variable refers to itself, directly or not.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.variables import resolve_var_any

            print(resolve_var_any(("%{a}", ["%{a}-%{b}"], 7), {"a": 1, "b": "x"}))

        .. testoutput::

            ((1, ['1-x'], 7), False)

    """
    if isinstance(some_val, str):
        return cast("tuple[T, bool]", _resolve_var_str(some_val, variables))  # type: ignore[return-value]
    if isinstance(some_val, Mapping):
        resolved_items = {
            k: resolve_var_any(v, variables)  # pyright: ignore[reportUnknownArgumentType]
            for k, v in cast("Mapping[str, Any]", some_val).items()  # pyright: ignore[reportUnknownVariableType]
        }
        return (
            cast("T", {k: v[0] for k, v in resolved_items.items()}),
            any(v[1] for v in resolved_items.values()),
        )
    if isinstance(some_val, _SEQUENCE_AND_SET_TYPES):
        resolved_list = [
            resolve_var_any(i, variables) for i in cast("Iterable[Any]", some_val)
        ]
        items = [item for item, _ in resolved_list]
        container = _rebuild(some_val, items)
        return cast("T", container), any(unresolved for _, unresolved in resolved_list)
    # anything else (numbers, bytes, paths, models, generators, ...) is left as is
    return some_val, False


_SEQUENCE_AND_SET_TYPES = (list, tuple, set, frozenset)
"""Containers whose items are searched for variables."""


def _rebuild(original: Iterable[Any], items: list[Any]) -> Any:  # noqa: ANN401
    """Make a container like *original* from *items*.

    Args:
        original: the container the items came from.
        items: the new items.

    Returns:
        Any: a container of the type of ``original`` holding ``items``, or of its
        base type (list, tuple, set or frozenset) if that type can't be built from
        a list, such as a namedtuple.

    Raises:
        StopIteration: if ``original`` isn't a list, tuple, set or frozenset.

    Example:
        .. testcode::

            from collections import namedtuple

            from pyantz.infrastructure.config.variables import _rebuild

            Point = namedtuple("Point", "x y")
            print(_rebuild(frozenset(), [1]), _rebuild(Point(0, 0), [1, 2]))

        .. testoutput::

            frozenset({1}) (1, 2)

    """
    base = next(base for base in _SEQUENCE_AND_SET_TYPES if isinstance(original, base))
    try:
        return cast("Callable[[list[Any]], Any]", type(original))(items)
    except TypeError:  # for example, a namedtuple needs separate arguments
        return base(items)


def _resolve_var_str(v: str, variables: Mapping[str, Any]) -> tuple[Any, bool]:
    """Resolve the string by replacing variables.

    If the whole string is exactly one reference (``"%{n}"``) to a non-string
    variable, the variable's value is returned as is, preserving its type.
    Otherwise, values are converted to strings and interpolated.

    Args:
        v: the string to resolve.
        variables: the variables to fill in.

    Returns:
        tuple[Any, bool]: the string with variables interleaved (or the value of
        a whole reference) AND a boolean. If the boolean is true, then a variable
        substring was found but could not be replaced because the variable isn't
        set.

    Raises:
        ValueError: if resolving needs more than :data:`MAX_RESOLUTION_DEPTH`
            passes, i.e., a variable refers to itself.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.variables import _resolve_var_str

            print(_resolve_var_str("%{n}", {"n": 5}))
            print(_resolve_var_str("%{a}-%{b}", {"a": 1, "b": "x"}))
            print(_resolve_var_str("%{a}-%{unset}", {"a": 1}))
            try:
                _resolve_var_str("%{a}", {"a": "%{b}", "b": "%{a}"})
            except ValueError as exc:
                print(exc)

        .. testoutput::

            (5, False)
            ('1-x', False)
            ('1-%{unset}', True)
            Recursive variable reference while resolving '%{a}'

    """
    whole_reference = VARIABLE_REGEX.fullmatch(v)
    if whole_reference is not None:
        name = whole_reference.group(1)[2:-1]
        if name in variables and not isinstance(variables[name], str):
            return variables[name], False

    s = v
    for _ in range(MAX_RESOLUTION_DEPTH):
        replaced = False
        unresolved = False

        def _replace(match: re.Match[str]) -> str:
            """Replace one reference by its variable's value, if it is set.

            Args:
                match: a reference to a variable, such as ``%{name}``.

            Returns:
                str: the variable's value as text, or the reference if unset.

            Raises:
                None.

            """
            nonlocal replaced, unresolved
            name = match.group(1)[2:-1]
            if name in variables:
                replaced = True
                return str(variables[name])
            unresolved = True
            return match.group(1)

        # every reference of the pass is replaced in one go, so replacing one
        # can't shift the others (values may hold references for the next pass)
        s = VARIABLE_REGEX.sub(_replace, s)
        if not replaced:
            return s, unresolved

    msg = f"Recursive variable reference while resolving {v!r}"
    raise ValueError(msg)
