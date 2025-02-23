"""
Parameters may contain variables which need resolving. This module
    will handle resolving the variables
"""

import re
from collections.abc import Mapping as MappingABC
from operator import add, mul, sub, truediv
from typing import Mapping, overload, TYPE_CHECKING, Union

from pydantic import BaseModel

if TYPE_CHECKING:
    from pyantz.infrastructure.config.base import ParametersType, PrimitiveType

VARIABLE_PATTERN = re.compile(r"%{([^}]+)}")


def resolve_variables(
    parameters: 'ParametersType', variables: Mapping[str, 'PrimitiveType']
) -> 'ParametersType':
    """Provided paramters, return the parameters with any variables interpolated

    Args:
        parameters (ParametersType): ParametersType to a job
        variables (Mapping[str, PrimitiveType]): variables in scope for that job

    Returns:
        ParametersType: the job with variables interpolated
    """
    if parameters is None:
        return None
    if variables is None:
        return parameters
    params = parameters
    return {
        k: (
            _resolve_value(val, variables)
            if not isinstance(val, (MappingABC, BaseModel))
            else val
        )
        for k, val in params.items()
    }


def is_variable(token: 'PrimitiveType') -> bool:
    """Returns true if the provided token is a variable expression"""
    return VARIABLE_PATTERN.match(str(token)) is not None


@overload
def _resolve_value(
    val: 'PrimitiveType', variables: Mapping[str, 'PrimitiveType']
) -> 'PrimitiveType':
    pass


@overload
def _resolve_value(
    val: list['PrimitiveType'], variables: Mapping[str, 'PrimitiveType']
) -> list['PrimitiveType']:
    pass


def _resolve_value(
    val: Union['PrimitiveType', list['PrimitiveType']], variables: Mapping[str, 'PrimitiveType']
) -> Union['PrimitiveType', list['PrimitiveType']]:
    """Given a value return the value with any variables resolved/removed

    Args:
        val (PrimitiveType): value of the parameters from the configuration
        variables (Mapping[str, PrimitiveType]): variables in scope to resolve

    Returns:
        PrimitiveType: provided value with any variables tokens
            replaced with value of the variable
    """

    if isinstance(val, list):
        return [_resolve_value(elem, variables=variables) for elem in val]

    if not isinstance(val, str):
        return val  # only strings have variable tokens

    split_vars = VARIABLE_PATTERN.split(val)
    if len(split_vars) == 1:
        return val  # only unmatched will return a list of one
    for i in range(1, len(split_vars), 2):
        split_vars[i] = str(
            _resolve_variable_expression(split_vars[i], variables=variables)
        )

    val = "".join(split_vars)

    val = _infer_type(val)

    return val


def _infer_type(val: str) -> 'PrimitiveType':
    """Change type to best fitting primitive type

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
    variable_expression: str, variables: Mapping[str, 'PrimitiveType']
) -> 'PrimitiveType':
    """Turn expressions of variables into one literal

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
    print("parent call: ", variable_expression)
    return _resolve_variable_expression_recursive(
        variable_expression=variable_expression.strip(), variables=variables
    )


def _resolve_variable_expression_recursive(
    variable_expression: str, variables: Mapping[str, 'PrimitiveType']
) -> 'PrimitiveType':
    """Turn expressions of variables into one literal

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
    if variables is not None and variable_expression in variables:
        return variables[variable_expression]

    operations = [
        ("-", sub),
        ("+", add),
        ("/", truediv),
        ("*", mul),
    ]

    for op_char, op_fn in operations:
        if op_char in variable_expression:
            i = variable_expression.find(op_char)
            lval: 'PrimitiveType' = variable_expression[:i].rstrip()
            rval: 'PrimitiveType' = variable_expression[i + 1 :].lstrip()

            lval = _resolve_variable_expression_recursive(
                str(lval), variables=variables
            )
            rval = _resolve_variable_expression_recursive(
                str(rval), variables=variables
            )

            if not isinstance(lval, (int, float)):
                # try to convert to a numeric
                lval = _infer_type(lval)
                if not isinstance(lval, (int, float)):
                    raise RuntimeError(
                        f'Unable to resolve perform operation ({op_char})'
                        ' with "{lval}" and "{rval}"'
                    )

            if not isinstance(rval, (int, float)):
                # try to convert to a numeric
                rval = _infer_type(rval)
                if not isinstance(rval, (int, float)):
                    raise RuntimeError(
                        f'Unable to resolve perform operation ({op_char}) with "{rval}"'
                    )

            return op_fn(lval, rval)

    ret = _resolve_token(variable_expression, variables=variables)

    return ret


def _resolve_token(
    var_token: str, variables: Mapping[str, 'PrimitiveType']
) -> 'PrimitiveType':
    """For the provided token, if its a variable name return the variable

    Args:
        var_token (str): name of a variable
        variables (Mapping[str, PrimitiveType]): variables in scope to resolve

    Returns:
        str: if it exists, the value of the variable of the token provided
    """

    token: str = var_token.strip()
    if variables is None:
        return token
    return str(variables.get(token, token))
