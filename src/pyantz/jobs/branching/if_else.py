"""Conditional job execution based on a comparison between two values.

:func:`if_else` submits one of two jobs depending on whether
``left_side <comparator> right_side`` is true.

:func:`conditionally_execute` is a simpler variant that only executes a
job when the condition is true; it does nothing on the false branch.

Both jobs support template variables in ``left_side`` and ``right_side``,
making them useful for dynamic branching based on runtime state.
"""

from __future__ import annotations

import logging
import math
import operator
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import JobConfig, SubmissionFnType, add_parameters

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_REL_TOL = 1e-6
"""Default relative tolerance of ``~=``: values within one part per million are
equal."""

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
"""Comparators of ``left_side <comparator> right_side``.

``=``/``==``, ``!=``, ``<``, ``<=``, ``>`` and ``>=`` compare as usual; ``~=`` is
approximately equal (:func:`math.isclose`); ``in`` and ``not in`` check if the
left side is a substring of the right side; ``=~`` checks if the regular
expression on the right side matches anywhere in the left side.
"""

type Coercion = Literal["auto", "str", "float"]
"""How the sides are read before comparing: ``auto`` (numbers if both can be),
``str`` (text) or ``float`` (numbers)."""


class IfElseParams(BaseModel):
    """Parameters for the if/else job."""

    model_config = ConfigDict(frozen=True)

    left_side: str | float
    """Left side of the comparison."""

    right_side: str | float
    """Right side of the comparison."""

    comparator: ValidOperators
    """How to compare the sides, see :data:`ValidOperators`."""

    rel_tol: float = DEFAULT_REL_TOL
    """Relative tolerance of the ``~=`` (approximately equal) comparator, see
    :func:`math.isclose`."""

    abs_tol: float = 0.0
    """Absolute tolerance of the ``~=`` (approximately equal) comparator, see
    :func:`math.isclose`."""

    coerce: Coercion = "auto"
    """How the sides are read before comparing with ``=``, ``<``, ``>``, ...:
    ``auto`` as numbers if both can be, otherwise as they are; ``str`` as text;
    ``float`` as numbers (the job fails if one isn't a number). ``in``,
    ``not in`` and ``=~`` always compare text."""

    if_true: JobConfig
    """The "if" part of the job: submitted when the comparison is true."""

    if_false: JobConfig
    """The "else" part of the job: submitted when the comparison is false."""


@add_parameters(IfElseParams)
def if_else(params: IfElseParams, submit_fn: SubmissionFnType) -> bool:
    """Submit a job based on a conditional value.

    Either ``if_true`` or ``if_false`` is submitted, depending on whether
    ``left_side <comparator> right_side`` holds. The sides may use template
    variables, so the branch can depend on the results of earlier jobs.

    Args:
        params: the job's parameters, validated as :class:`IfElseParams`.
        submit_fn: function to submit the chosen job with.

    Parameters:
        left_side (str | float): left side of the comparison.
        right_side (str | float): right side of the comparison.
        comparator (str): one of :data:`ValidOperators`.
        rel_tol (float): relative tolerance of ``~=``. Defaults to
            :data:`DEFAULT_REL_TOL`.
        abs_tol (float): absolute tolerance of ``~=``. Defaults to 0.
        coerce (str): ``auto``, ``str`` or ``float``; see
            :attr:`IfElseParams.coerce`. Defaults to ``auto``.
        if_true (JobConfig): job to submit if the comparison is true.
        if_false (JobConfig): job to submit if the comparison is false.

    Returns:
        bool: True once a job is submitted.

    Raises:
        ValueError: if ``coerce`` is ``float`` and a side isn't a number.
        re.error: if ``comparator`` is ``=~`` and the right side isn't a valid
            regular expression.

    Example:
        .. testcode::

            from pyantz.jobs.branching.if_else import if_else

            submitted = []
            if_else(
                {
                    "left_side": "10",
                    "comparator": ">",
                    "right_side": 9,
                    "if_true": {
                        "name": "bigger",
                        "function": "pyantz.jobs.testing.nop.do_nothing",
                        "parameters": {},
                    },
                    "if_false": {
                        "name": "smaller",
                        "function": "pyantz.jobs.testing.nop.do_nothing",
                        "parameters": {},
                    },
                },
                submitted.append,
            )
            print([job.name for job in submitted])

        .. testoutput::

            ['bigger']

    """
    # first compare which one we want to do
    if _compare(params):
        logging.getLogger(__name__).debug(
            "Condition true, submitting job %s", params.if_true.job_id
        )
        submit_fn(
            params.if_true,
        )
    else:
        logging.getLogger(__name__).debug(
            "Condition false, submitting job %s", params.if_false.job_id
        )
        submit_fn(
            params.if_false,
        )

    return True


class ConditionalExecution(BaseModel):
    """Execute a job iff a condition is true."""

    model_config = ConfigDict(frozen=True)

    left_side: str | float
    """Left side of the comparison."""

    right_side: str | float
    """Right side of the comparison."""

    comparator: ValidOperators
    """How to compare the sides, see :data:`ValidOperators`."""

    rel_tol: float = DEFAULT_REL_TOL
    """Relative tolerance of the ``~=`` (approximately equal) comparator, see
    :func:`math.isclose`."""

    abs_tol: float = 0.0
    """Absolute tolerance of the ``~=`` (approximately equal) comparator, see
    :func:`math.isclose`."""

    coerce: Coercion = "auto"
    """How the sides are read before comparing, see :attr:`IfElseParams.coerce`."""

    if_true: JobConfig
    """Job submitted when the comparison is true."""


@add_parameters(ConditionalExecution)
def conditionally_execute(
    params: ConditionalExecution, submit_fn: SubmissionFnType
) -> bool:
    """Execute a job iff a condition is true.

    Like :func:`if_else` without an "else": nothing is submitted when the
    comparison is false, and the job still succeeds.

    Args:
        params: the job's parameters, validated as :class:`ConditionalExecution`.
        submit_fn: function to submit ``if_true`` with.

    Parameters:
        left_side (str | float): left side of the comparison.
        right_side (str | float): right side of the comparison.
        comparator (str): one of :data:`ValidOperators`.
        rel_tol (float): relative tolerance of ``~=``. Defaults to
            :data:`DEFAULT_REL_TOL`.
        abs_tol (float): absolute tolerance of ``~=``. Defaults to 0.
        coerce (str): ``auto``, ``str`` or ``float``; see
            :attr:`IfElseParams.coerce`. Defaults to ``auto``.
        if_true (JobConfig): job to submit if the comparison is true.

    Returns:
        bool: True, whether or not the job was submitted.

    Raises:
        ValueError: if ``coerce`` is ``float`` and a side isn't a number.
        re.error: if ``comparator`` is ``=~`` and the right side isn't a valid
            regular expression.

    Example:
        .. testcode::

            from pyantz.jobs.branching.if_else import conditionally_execute

            for log_line in ("all good", "ERROR: disk full"):
                submitted = []
                conditionally_execute(
                    {
                        "left_side": log_line,
                        "comparator": "=~",
                        "right_side": "^ERROR",
                        "if_true": {
                            "function": "pyantz.jobs.testing.nop.do_nothing",
                            "parameters": {},
                        },
                    },
                    submitted.append,
                )
                print(log_line, len(submitted))

        .. testoutput::

            all good 0
            ERROR: disk full 1

    """
    if _compare(params):
        logging.getLogger(__name__).debug(
            "Condition true, submitting job %s", params.if_true.job_id
        )
        submit_fn(
            params.if_true,
        )
    else:
        logging.getLogger(__name__).debug("Condition false, submitting nothing")
    return True


def _to_number(value: str | float) -> float | None:
    """Read a value as a number, or None if it isn't one.

    Args:
        value: the value to read.

    Returns:
        float | None: the value as a finite number, or None if it isn't one
        (``"nan"`` and ``"inf"`` count as text).

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.jobs.branching.if_else import _to_number

            print(_to_number("1.5"), _to_number(2), _to_number("nan"), _to_number("x"))

        .. testoutput::

            1.5 2.0 None None

    """
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None  # "nan" and "inf" are text


def _compare_text(left: str, right: str, comparator: str) -> bool:
    r"""Evaluate the comparators that read both sides as text.

    Args:
        left: the left side.
        right: the right side; for ``=~``, a regular expression.
        comparator: ``in``, ``not in`` or ``=~``.

    Returns:
        bool: for ``in``/``not in``, whether ``left`` is (not) a substring of
        ``right``; for ``=~``, whether ``right`` matches anywhere in ``left``.

    Raises:
        re.error: if ``comparator`` is ``=~`` and ``right`` isn't a valid regular
            expression.

    Example:
        .. testcode::

            from pyantz.jobs.branching.if_else import _compare_text

            print(_compare_text("ant", "pyantz", "in"))
            print(_compare_text("run_42", r"\d+$", "=~"))

        .. testoutput::

            True
            True

    """
    if comparator == "=~":
        return re.search(right, left) is not None
    return (left in right) == (comparator == "in")


def _compare(params: IfElseParams | ConditionalExecution) -> bool:
    """Evaluate ``left <comparator> right``.

    ``~=`` means approximately equal: both sides are read as numbers and compared
    with :func:`math.isclose` using the ``rel_tol`` and ``abs_tol`` parameters.

    Args:
        params: the parameters holding the sides, the comparator and how to read
            the sides.

    Returns:
        bool: the result of the comparison; False for ``~=`` when a side isn't a
        number.

    Raises:
        ValueError: if ``coerce`` is ``float`` and a side isn't a number.
        re.error: if ``comparator`` is ``=~`` and the right side isn't a valid
            regular expression.

    Example:
        .. testcode::

            from pyantz.jobs.branching.if_else import ConditionalExecution, _compare

            job = {"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}
            for coerce in ("auto", "str"):
                params = ConditionalExecution(
                    left_side="10",
                    comparator=">",
                    right_side="9",
                    coerce=coerce,
                    if_true=job,
                )
                print(coerce, _compare(params))

        .. testoutput::

            auto True
            str False

    """
    left, right = params.left_side, params.right_side
    comparator = params.comparator

    if comparator in {"in", "not in", "=~"}:
        return _compare_text(str(left), str(right), comparator)

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
    if params.coerce in {"float", "auto"}:
        left_number, right_number = _to_number(left), _to_number(right)
        if left_number is not None and right_number is not None:
            return op(left_number, right_number)
        if params.coerce == "float":
            msg = f"Cannot compare {left!r} and {right!r} as numbers"
            raise ValueError(msg)
    if params.coerce == "str" or isinstance(left, str) != isinstance(right, str):
        # text compared with text; a number against text is compared as text too
        return op(str(left), str(right))
    result = op(left, right)
    logging.getLogger(__name__).debug(
        "Compared %r %s %r: %s", left, comparator, right, result
    )
    return result


op_mapping: dict[ValidOperators, Callable[..., bool]] = {
    "=": operator.eq,
    "==": operator.eq,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
}
"""Function of each comparator which doesn't need special handling."""
