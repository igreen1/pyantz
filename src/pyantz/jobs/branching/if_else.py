"""Evaluate a conditional and submit a job depending on the result."""

from __future__ import annotations

import operator
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

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
