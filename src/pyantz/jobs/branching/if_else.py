"""Conditional job execution based on a comparison between two values.

:func:`if_else` submits one of two jobs depending on whether
``left_side <comparator> right_side`` is true.

:func:`conditionally_execute` is a simpler variant that only executes a
job when the condition is true; it does nothing on the false branch.

Both jobs support template variables in ``left_side`` and ``right_side``,
making them useful for dynamic branching based on runtime state.
"""

import math
import operator
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import JobConfig, SubmissionFnType, add_parameters

if TYPE_CHECKING:
    from collections.abc import Callable

# default relative tolerance of "~=": values within one part per million are equal
DEFAULT_REL_TOL = 1e-6

type ValidOperators = Literal[
    "=",
    "==",
    "<",
    "<=",
    ">",
    ">=",
    "!=",
    "~=",
    "in",
    "not in",
    "=~",
]

type Coercion = Literal["auto", "str", "float"]


class IfElseParams(BaseModel):
    """Parameters for the if/else job."""

    model_config = ConfigDict(frozen=True)

    left_side: str | float

    right_side: str | float

    comparator: ValidOperators

    # tolerances for the "~=" (approximately equal) comparator, see `math.isclose`
    rel_tol: float = DEFAULT_REL_TOL
    abs_tol: float = 0.0
    # how the sides are read before comparing with =, <, >, ...:
    # auto: as numbers if both can be, otherwise as they are
    # str: as text; float: as numbers (the job fails if one isn't a number)
    # `in`, `not in` and `=~` always compare text
    coerce: Coercion = "auto"

    # the "if" part of the job
    if_true: JobConfig

    # the "else" part of the job
    if_false: JobConfig


@add_parameters(IfElseParams)
def if_else(params: IfElseParams, submit_fn: SubmissionFnType) -> bool:
    """Submit a job based on a conditional value."""
    # first compare which one we want to do
    if _compare(params):
        submit_fn(
            params.if_true,
        )
    else:
        submit_fn(
            params.if_false,
        )

    return True


class ConditionalExecution(BaseModel):
    """Execute a job iff a condition is true."""

    model_config = ConfigDict(frozen=True)

    left_side: str | float

    right_side: str | float

    comparator: ValidOperators

    # tolerances for the "~=" (approximately equal) comparator, see `math.isclose`
    rel_tol: float = DEFAULT_REL_TOL
    abs_tol: float = 0.0
    # see IfElseParams.coerce
    coerce: Coercion = "auto"

    if_true: JobConfig


@add_parameters(ConditionalExecution)
def conditionally_execute(
    params: ConditionalExecution, submit_fn: SubmissionFnType
) -> bool:
    """Execute a job iff a condition is true."""
    if _compare(params):
        submit_fn(
            params.if_true,
        )
    return True


def _to_number(value: str | float) -> float | None:
    """Read a value as a number, or None if it isn't one."""
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None  # "nan" and "inf" are text


def _compare(params: IfElseParams | ConditionalExecution) -> bool:
    """Evaluate ``left <comparator> right``.

    ``~=`` means approximately equal: both sides are read as numbers and compared
    with :func:`math.isclose` using the ``rel_tol`` and ``abs_tol`` parameters.
    """
    left, right = params.left_side, params.right_side
    comparator = params.comparator

    if comparator in {"in", "not in", "=~"}:
        left_text, right_text = str(left), str(right)
        if comparator == "=~":
            return re.search(right_text, left_text) is not None
        return (left_text in right_text) == (comparator == "in")

    if comparator == "~=":
        # approximately equal: both sides are numbers, compared with `math.isclose`
        left_number, right_number = _to_number(left), _to_number(right)
        if left_number is None or right_number is None:
            return False  # not numbers, so they cannot be close
        return math.isclose(
            left_number,
            right_number,
            rel_tol=params.rel_tol,
            abs_tol=params.abs_tol,
        )

    op = op_mapping[comparator]
    if params.coerce == "float":
        left_number, right_number = _to_number(left), _to_number(right)
        if left_number is None or right_number is None:
            msg = f"Cannot compare {left!r} and {right!r} as numbers"
            raise ValueError(msg)
        return op(left_number, right_number)
    if params.coerce == "auto":
        left_number, right_number = _to_number(left), _to_number(right)
        if left_number is not None and right_number is not None:
            return op(left_number, right_number)
    if params.coerce == "str" or isinstance(left, str) != isinstance(right, str):
        # text compared with text; a number against text is compared as text too
        return op(str(left), str(right))
    return op(left, right)


op_mapping: dict[ValidOperators, Callable[..., bool]] = {
    "=": operator.eq,
    "==": operator.eq,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
}
