"""Conditional job execution based on a comparison between two values.

:func:`if_else` submits one of two jobs depending on whether
``left_side <comparator> right_side`` is true.

:func:`conditionally_execute` is a simpler variant that only executes a
job when the condition is true; it does nothing on the false branch.

Both jobs support template variables in ``left_side`` and ``right_side``,
making them useful for dynamic branching based on runtime state.
"""

import operator
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import JobConfig, SubmissionFnType, add_parameters

if TYPE_CHECKING:
    from collections.abc import Callable

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

    # the "if" part of the job
    if_true: JobConfig

    # the "else" part of the job
    if_false: JobConfig


@add_parameters(IfElseParams)
def if_else(params: IfElseParams, submit_fn: SubmissionFnType) -> bool:
    """Submit a job based on a conditional value."""
    # first compare which one we want to do
    op = op_mapping[params.comparator]

    if op(params.left_side, params.right_side):
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

    if_true: JobConfig


@add_parameters(ConditionalExecution)
def conditionally_execute(
    params: ConditionalExecution, submit_fn: SubmissionFnType
) -> bool:
    """Execute a job iff a condition is true."""
    op = op_mapping[params.comparator]

    if op(params.left_side, params.right_side):
        submit_fn(
            params.if_true,
        )
    return True


op_mapping: dict[ValidOperators, Callable[..., bool]] = {
    "=": operator.eq,
    "==": operator.eq,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
    "~=": operator.ne,
}
