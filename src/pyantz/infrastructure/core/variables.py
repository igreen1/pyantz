"""Resolve variables in parameters to their correct values."""

import re
from collections.abc import Callable, Mapping
from operator import add, mul, sub, truediv
from typing import TYPE_CHECKING, Any, Union, overload

from pydantic import BaseModel, JsonValue, ValidationError

import pyantz.infrastructure.config.base as config_base

if TYPE_CHECKING:
    from pyantz.infrastructure.config.base import (
        AntzConfig,
        ParametersType,
        PrimitiveType,
    )

VARIABLE_PATTERN = re.compile(r"%{([^}]+)}")


def resolve_variables(
    parameters: "ParametersType", variables: Mapping[str, "PrimitiveType"] | None
) -> "ParametersType":
    """Return parameters with the variables replaced by their values from the provided scope.

    Args:
        parameters (ParametersType): ParametersType to a job
        variables (Mapping[str, PrimitiveType]): variables in scope for that job

    Returns:
        ParametersType: the job with variables interpolated

    """
    if parameters is None or variables is None or variables == {}:
        return parameters

    # eliminate any self-referencing in the variables
    # variables is a sub-type of parameters types
    # and _resolve_variables will return of the same form
    # but type annotating that is insanely tough because JsonValue != PrimitiveType
    variables = _resolve_variables(variables, variables)  # type: ignore[assignment]

    return _resolve_variables(parameters, variables)


def _resolve_variables(
    parameters: "ParametersType",
    variables: Mapping[str, "PrimitiveType"] | None,
) -> "ParametersType":
    """Return parameters with the variables replaced by their values from the provided scope.

    Args:
        parameters (ParametersType): ParametersType to a job
        variables (Mapping[str, PrimitiveType]): variables in scope for that job

    Returns:
        ParametersType: the job with variables interpolated

    """
    if parameters is None or variables is None or variables == {}:
        return parameters

    return {
        key: _recursive_resolve_variables(value, variables=variables)
        for key, value in parameters.items()
    }


@overload
def _recursive_resolve_variables(
    parameters: "AntzConfig", variables: Mapping[str, "PrimitiveType"]
) -> "AntzConfig": ...
@overload
def _recursive_resolve_variables(
    parameters: list["AntzConfig"], variables: Mapping[str, "PrimitiveType"]
) -> list["AntzConfig"]: ...
@overload
def _recursive_resolve_variables(
    parameters: "JsonValue", variables: Mapping[str, "PrimitiveType"]
) -> "JsonValue": ...


def _recursive_resolve_variables(
    parameters: Union["AntzConfig", list["AntzConfig"], JsonValue],
    variables: Mapping[str, "PrimitiveType"],
) -> Union["AntzConfig", list["AntzConfig"], JsonValue]:
    """Adjust variables in the values within a parameter dictionary."""
    if isinstance(parameters, list):
        # mypy doesn't understand that list[JsonValue] is just a JsonValue, so ignore return check
        return [_recursive_resolve_variables(val, variables) for val in parameters]  # type: ignore[return-value] # pylint: disable=line-too-long
    if isinstance(parameters, str):
        return _resolve_value(parameters, variables=variables)
    if isinstance(parameters, (int, float, bool)) or parameters is None:
        return parameters
    if is_config(parameters):
        return parameters
    if isinstance(parameters, Mapping):
        return {
            key: _recursive_resolve_variables(value, variables=variables)
            for key, value in parameters.items()
        }

    return parameters


def is_config(parameters: Union[Mapping[str, Any], "AntzConfig"]) -> bool:
    """Check if parameters is a config pydantic model."""
    if isinstance(parameters, BaseModel):
        return True
    for model_name in [
        "JobConfig",
        "SubmitterJobConfig",
        "MutableJobConfig",
        "Config",
        "PipelineConfig",
    ]:
        try:
            getattr(config_base, model_name).model_validate(parameters)
        except ValidationError:
            continue
        else:
            return True
    return False


def is_variable(token: Any) -> bool:  # noqa: ANN401
    """Return true if the provided token is a variable expression."""
    if isinstance(token, list):
        return any(is_variable(val) for val in token)  # pyright: ignore[reportUnknownVariableType]
    if isinstance(token, str):
        return VARIABLE_PATTERN.match(token) is not None
    return False


@overload
def _resolve_value(
    val: "PrimitiveType", variables: Mapping[str, "PrimitiveType"]
) -> "PrimitiveType":
    pass


@overload
def _resolve_value(
    val: list["PrimitiveType"], variables: Mapping[str, "PrimitiveType"]
) -> list["PrimitiveType"]:
    pass


@overload
def _resolve_value(val: "AntzConfig", variables: Mapping[str, "PrimitiveType"]) -> "AntzConfig":
    pass


@overload
def _resolve_value(
    val: list["AntzConfig"], variables: Mapping[str, "PrimitiveType"]
) -> list["AntzConfig"]:
    pass


def _resolve_value(
    val: Union["PrimitiveType", list["PrimitiveType"], "AntzConfig", list["AntzConfig"]],
    variables: Mapping[str, "PrimitiveType"],
) -> Union["PrimitiveType", list["PrimitiveType"], "AntzConfig", list["AntzConfig"]]:
    """Return the value with variables resolved into their assigned value.

    Args:
        val (PrimitiveType): value of the parameters from the configuration
        variables (Mapping[str, PrimitiveType]): variables in scope to resolve

    Returns:
        PrimitiveType: provided value with any variables tokens
            replaced with value of the variable

    """
    if isinstance(val, BaseModel):
        return val

    if isinstance(val, list):
        if any(isinstance(subval, BaseModel) for subval in val):
            return val
        result: list[PrimitiveType] = []
        for elem in val:
            if not isinstance(elem, (int, float, bool, str)):
                err_msg: str = "Mixed types in list. Please pass only primitives or pydantic models"
                raise TypeError(err_msg)
            result.append(_resolve_value(elem, variables=variables))
        return result

    if not isinstance(val, str):
        return val  # only strings have variable tokens

    split_vars = VARIABLE_PATTERN.split(val)
    if len(split_vars) == 1:
        return val  # only unmatched will return a list of one
    for i in range(1, len(split_vars), 2):
        split_vars[i] = str(_resolve_variable_expression(split_vars[i], variables=variables))

    val = "".join(split_vars)
    return _infer_type(val)


def _infer_type(val: str) -> "PrimitiveType":
    """Change type to best fitting primitive type.

    Examples:
        _infer_type('1') -> 1 # int
        _infer_type('1.0') -> 1.0 # float
        _infer_type('true') -> True # bool
        _infer_type('True') -> True # bool
        _infer_type('TrUe') -> True
        _infer_type('hello') -> 'hello' # str
        _infer_type("1x") -> '1x' # str


    Args:
        val (str): the value with its variables resolved
    Returns:
        the value cast to the best fittign primitive type

    """
    try:
        return int(val)
    except ValueError:
        pass

    try:
        return float(val)
    except ValueError:
        pass

    if val.lower() in "true":
        return True
    if val.lower() in "false":
        return False

    return val


def _resolve_variable_expression(
    variable_expression: str, variables: Mapping[str, "PrimitiveType"]
) -> "PrimitiveType":
    """Turn expressions of variables into one literal.

    Variables can be expressions, combining literals and variables with simple math
        this function will resolve those expressions


    This function will first split by multiplication, then division, then addition, then subtraction
        NOT quite PEMDAS

    Examples:
    Given
        a = 1, b = 2, c = 3, d = 4
        %{a + b} => 3
        %{a * b + c} => 5
        %{a * b / c} => 2/3

    Args:
        variable_expression (str): an expression involving variables inside  %{}
        variables (Mapping[str, PrimitiveType]): variables in scope to resolve

    Returns:
        PrimitiveType: the variable expression as simplified as possible

    """
    return _resolve_variable_expression_recursive(
        variable_expression=variable_expression.strip(), variables=variables
    )


def _resolve_variable_expression_recursive(
    variable_expression: str, variables: Mapping[str, "PrimitiveType"]
) -> "PrimitiveType":
    """Turn expressions of variables into one literal.

    Variables can be expressions, combining literals and variables with simple math
        this function will resolve those expressions


    This function will first split by multiplication, then division, then addition, then subtraction
        NOT quite PEMDAS

    Examples:
    Given
        a = 1, b = 2, c = 3, d = 4
        %{a + b} => 3
        %{a * b + c} => 5
        %{a * b / c} => 2/3

    Args:
        variable_expression (str): an expression involving variables inside  %{}
        variables (Mapping[str, PrimitiveType]): variables in scope to resolve

    Returns:
        PrimitiveType: the variable expression as simplified as possible

    """
    # shortcut allows variables with +,-,/,*
    if variables is not None and variable_expression in variables:  # pyright: ignore[reportUnnecessaryComparison] # pylint: disable=line-too-long
        # must check if our variable itself references other variables!
        return variables[variable_expression]

    operations: list[tuple[str, Callable[[Any, Any], bool]]] = [
        ("-", sub),
        ("+", add),
        ("/", truediv),
        ("*", mul),
    ]

    err_msg: str
    for op_char, op_fn in operations:
        if op_char in variable_expression:
            i = variable_expression.find(op_char)
            # ruff improperly asking to remove quotes around types
            # to avoid circular imports, these are TYPE_CHECKING guarded
            lval: "PrimitiveType" = variable_expression[:i].rstrip()  # noqa: UP037
            rval: "PrimitiveType" = variable_expression[i + 1 :].lstrip()  # noqa: UP037

            lval = _resolve_variable_expression_recursive(str(lval), variables=variables)
            rval = _resolve_variable_expression_recursive(str(rval), variables=variables)

            err_msg = (
                f'Unable to resolve perform operation ({{op_char}}) with "{lval}" and "{rval}"'
            )
            if not isinstance(lval, (int, float)):
                # try to convert to a numeric
                if lval is None:
                    raise TypeError(err_msg)
                lval = _infer_type(lval)
                if not isinstance(lval, (int, float)):
                    raise TypeError(err_msg)

            if not isinstance(rval, (int, float)):
                # try to convert to a numeric
                if rval is None:
                    raise TypeError(err_msg)
                rval = _infer_type(rval)
                if not isinstance(rval, (int, float)):
                    raise TypeError(err_msg)

            return op_fn(lval, rval)

    return _resolve_token(variable_expression, variables=variables)


def _resolve_token(var_token: str, variables: Mapping[str, "PrimitiveType"]) -> "PrimitiveType":
    """Return variable given token (possible variable name).

    Args:
        var_token (str): name of a variable
        variables (Mapping[str, PrimitiveType]): variables in scope to resolve

    Returns:
        str: if it exists, the value of the variable of the token provided

    """
    token: str = var_token.strip()
    if variables is None:  # pyright: ignore[reportUnnecessaryComparison]
        return token
    return str(variables.get(token, token))
