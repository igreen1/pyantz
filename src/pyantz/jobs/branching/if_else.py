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
]


class IfElseParams(BaseModel):
    """Parameters for the if/else job."""

    model_config = ConfigDict(frozen=True)

    left_side: str | float

    right_side: str | float

    comparator: ValidOperators

    # tolerances for the "~=" (approximately equal) comparator, see `math.isclose`
    rel_tol: float = DEFAULT_REL_TOL
    abs_tol: float = 0.0

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


def _compare(params: IfElseParams | ConditionalExecution) -> bool:
    """Evaluate ``left <comparator> right``.

    ``~=`` means approximately equal: both sides are read as numbers and compared
    with :func:`math.isclose` using the ``rel_tol`` and ``abs_tol`` parameters.
    """
    if params.comparator == "~=":
        try:
            return math.isclose(
                float(params.left_side),
                float(params.right_side),
                rel_tol=params.rel_tol,
                abs_tol=params.abs_tol,
            )
        except ValueError:
            return False  # not numbers, so they cannot be close
    return op_mapping[params.comparator](params.left_side, params.right_side)


op_mapping: dict[
    ValidOperators, Callable[..., bool]
] = {  # `~=` is handled in `_compare`
    "=": operator.eq,
    "==": operator.eq,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
}
