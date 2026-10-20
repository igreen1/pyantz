"""Fill in variables in the parameters."""

import logging
import re
from collections.abc import Iterable, Mapping
from typing import Any, cast

VARIABLE_REGEX = re.compile(r"(%{[^%{}]+})")

# maximum nesting of variables referring to other variables
MAX_RESOLUTION_DEPTH = 32


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
        Mapping[str, Any]: parameters with the variables eagerly replaced
        bool: True if some variables were detected and not replaced

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

    Returns: value with variables interleaved and a boolean. if the boolean is true,
        a variable was detected but left unchanged.
    """
    if isinstance(some_val, str):
        return cast("tuple[T, bool]", _resolve_var_str(some_val, variables))  # type: ignore[return-value]
    if isinstance(some_val, Mapping):
        resolved_variables_and_var_flag: dict[str, tuple[Any, bool]] = {
            k: resolve_var_any(v, variables)  # pyright: ignore[reportUnknownArgumentType]
            for k, v in cast("dict[str, Any]", some_val).items()  # pyright: ignore[reportUnknownVariableType]
        }
        resolved_variables = {
            k: v[0] for k, v in resolved_variables_and_var_flag.items()
        }
        remaining_variable_flag = any(
            v[1] for v in resolved_variables_and_var_flag.values()
        )
        return cast("T", resolved_variables), remaining_variable_flag  # type: ignore[return-value]
    if isinstance(some_val, Iterable):
        iter_cls: type[T] = type(some_val)  # type: ignore[assignment] # pyright: ignore[reportUnknownVariableType]
        result: list[tuple[Any, bool]] = [
            resolve_var_any(i, variables) for i in cast("Iterable[Any]", some_val)
        ]

        some_val_variables_resolved: Iterable[Any]
        if not result:
            some_val_variables_resolved = []
            unmade_edits = [False]
        else:
            some_val_variables_resolved, unmade_edits = tuple(zip(*result, strict=True))
        unresolved_variables = any(unmade_edits)
        return iter_cls(some_val_variables_resolved), unresolved_variables  # type: ignore[return-value,call-arg]
    return some_val, False


def _resolve_var_str(v: str, variables: Mapping[str, Any]) -> tuple[Any, bool]:
    """Resolve the string by replacing variables.

    If the whole string is exactly one reference (``"%{n}"``) to a non-string
    variable, the variable's value is returned as is, preserving its type.
    Otherwise, values are converted to strings and interpolated.

    Returns the string with variables interleaved
        AND a boolean. If the boolean is true, then a variable substring was found
        but could not be replaced because the variable isn't set.
    """
    whole_reference = VARIABLE_REGEX.fullmatch(v)
    if whole_reference is not None:
        name = whole_reference.group(1)[2:-1]
        if name in variables and not isinstance(variables[name], str):
            return variables[name], False

    s = v

    unmade_change = False
    variable_detected = True
    passes = 0
    while variable_detected:
        passes += 1
        if passes > MAX_RESOLUTION_DEPTH:
            msg = f"Recursive variable reference while resolving {v!r}"
            raise ValueError(msg)
        variable_detected = False
        for match in VARIABLE_REGEX.finditer(s):
            start = match.start()
            end = match.end()
            substr = s[start:end]
            if substr[2:-1] in variables:
                variable_detected = True
                s = s.replace(substr, str(variables[substr[2:-1]]))
            else:
                unmade_change = True

    return s, unmade_change
