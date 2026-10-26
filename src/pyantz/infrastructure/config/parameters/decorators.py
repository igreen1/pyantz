"""Decorate functions and strongly enforce parameter types."""

from __future__ import annotations

import logging
import uuid
from functools import wraps
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel

from pyantz.infrastructure.config.fn_utils import serialize_function

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pyantz.infrastructure.config.job import (
        JobConfig,
        JobFunctionType,
        ParametersType,
        SubmissionFnType,
    )

PYANTZ_REGISTERED_FUNCTION: Final[dict[str, JobFunctionType]] = {}
"""Every function registered by :func:`add_parameters`, keyed by its full name, so
registering a function again (a module reload) replaces it."""

VIRTUAL_MARKER: Final[str] = "__PYANTZ_VIRTUAL__"
"""Attribute set by :func:`mark_virtual` on virtual job parameter models."""


def no_submit_fn[T: (BaseModel | ParametersType)](
    fn: Callable[[T], bool],
) -> Callable[[T, SubmissionFnType], bool]:
    """Wrap a function that doesn't want submit function.

    Every job is called with its parameters and a submit function; this lets a
    job which never submits other jobs take only its parameters. Apply it below
    :func:`add_parameters`.

    Args:
        fn: the job function, taking only its parameters.

    Returns:
        Callable[[T, SubmissionFnType], bool]: a function taking the parameters
        and a submit function, which it ignores.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import no_submit_fn

            @no_submit_fn
            def check(params):
                return params["value"] > 0

            print(check({"value": 1}, lambda job: None))

        .. testoutput::

            True

    """

    @wraps(fn)
    def _ignore_submitter(params: T, _submit_fn: SubmissionFnType) -> bool:
        """Wrap the function to allow the caller to pass submit function.

        Args:
            params: the job's parameters.
            _submit_fn: the submit function (ignored).

        Returns:
            bool: the result of ``fn``.

        Raises:
            Exception: anything raised by ``fn``.

        """
        return fn(params)

    return _ignore_submitter


def get_registered_functions(fn_name: str | None = None) -> list[JobFunctionType]:
    """Get the functions which have used the `add_parameters` decorator.

    A new list is returned each time, so callers can't change the registry.

    Args:
        fn_name: if given, only the functions with this full dotted name, or whose
            name ends with it at a `.` boundary (so `copy` finds `x.simple.copy` and
            `y.moving.copy`, but `py` finds nothing). All matches are returned.

    Returns:
        list[JobFunctionType]: the matching registered functions.

    Raises:
        None.

    Example:
        .. testcode::

            import pyantz.jobs
            from pyantz.infrastructure.config.parameters.decorators import (
                get_registered_functions,
            )

            names = sorted(fn.PYANTZ_NAME for fn in get_registered_functions("copy"))
            print(names)

        .. testoutput::

            ['pyantz.jobs.files.moving.copy', 'pyantz.jobs.files.simple.copy']

    """
    if fn_name is None:
        return list(PYANTZ_REGISTERED_FUNCTION.values())
    return [
        fn
        for fn in PYANTZ_REGISTERED_FUNCTION.values()
        if _name_matches(fn.PYANTZ_NAME, fn_name)  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
    ]


def _name_matches(registered_name: str, query: str) -> bool:
    """Check if the query is the whole name or a trailing part split on dots.

    Args:
        registered_name: the full dotted name of a registered function.
        query: the name searched for.

    Returns:
        bool: True if ``query`` is ``registered_name`` or its trailing parts.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.parameters.decorators import (
                _name_matches,
            )

            print(_name_matches("a.simple.copy", "simple.copy"))
            print(_name_matches("a.simple.copy", "py"))

        .. testoutput::

            True
            False

    """
    return registered_name == query or registered_name.endswith("." + query)


def trace_fn[**P, T](fn: Callable[P, T]) -> Callable[P, T]:
    """Log when a function starts and finishes.

    The messages are logged at debug level, to a logger named after the function.

    Args:
        fn: the function to wrap.

    Returns:
        Callable[P, T]: the function, logging each call.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.parameters.decorators import trace_fn

            @trace_fn
            def add(a, b):
                return a + b

            print(add(1, 2))

        .. testoutput::

            3

    """
    logger = logging.getLogger(getattr(fn, "__name__", __name__))

    @wraps(fn)
    def _log_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        """Run the function, debug logging start/end.

        Args:
            *args: positional arguments for ``fn``.
            **kwargs: keyword arguments for ``fn``.

        Returns:
            T: the result of ``fn``.

        Raises:
            BaseException: anything raised by ``fn`` is logged and raised again.

        """
        logger.debug("Starting function: %s", str(fn))
        try:
            result = fn(*args, **kwargs)
        except:
            logger.debug("Exception in function: %s", str(fn))
            raise
        else:
            logger.debug("Finished function %s", str(fn))
        return result

    return _log_wrapper


def add_parameters[T: BaseModel](
    param_cls: type[T],
    *,
    check_at_startup: bool = False,
) -> Callable[[Callable[[T, SubmissionFnType], bool]], JobFunctionType]:
    """Use the provided pydantic model to type check the parameters.

    Also registers the functions in a global static function list for the API

    At runtime, it will cast the parameters to the provided parameter class and
    pass that pydantic model to the wrapped function. Useful to enforce
    strict typing in a function.

    Args:
        param_cls: basemodel to use to validate
        check_at_startup: if True, will check the parameters class at startup.
            this disallows variables as those won't be set yet. Instead, prefer
            setting this value in the configuration as part of the initial params.

    Returns:
        Callable[[Callable[[T, SubmissionFnType], bool]], JobFunctionType]: the
        decorator, which returns the registered job function.

    Raises:
        None.

    Example:
        .. testcode:: decorators-add-parameters

            from pydantic import BaseModel

            from pyantz.infrastructure.config import add_parameters

            class GreetParams(BaseModel):
                name: str
                times: int = 1

            @add_parameters(GreetParams)
            def greet(params, submit_fn):
                print(" ".join([f"hello {params.name}"] * params.times))
                return True

            greet({"name": "ant", "times": 2}, lambda job: None)
            print(greet.PYANTZ_VALIDATION_MODEL.__name__)

        .. testoutput:: decorators-add-parameters

            hello ant hello ant
            GreetParams

    """

    def _decorate_fn_with_params(
        fn: Callable[[T, SubmissionFnType], bool],
    ) -> JobFunctionType:
        """Wrap *fn* with a parameter-casting layer and register it globally.

        Args:
            fn: the job function, taking its typed parameters and a submit
                function.

        Returns:
            JobFunctionType: the wrapped function, registered in
            :data:`PYANTZ_REGISTERED_FUNCTION`.

        Raises:
            None.

        """

        @wraps(fn)
        @trace_fn
        def _fn_with_checker(
            untyped_params: ParametersType, submit_fn: SubmissionFnType
        ) -> bool:
            """Check the parameters against the parameter class at runtime.

            Args:
                untyped_params: the job's parameters, as given.
                submit_fn: function the job may submit other jobs with.

            Returns:
                bool: the result of ``fn``.

            Raises:
                pydantic.ValidationError: if the parameters don't fit the model.
                Exception: anything raised by ``fn``.

            """
            typed_params = param_cls.model_validate(untyped_params)
            return fn(typed_params, submit_fn)

        # add special variables so that we can check if a function has been marked
        _fn_with_checker.PYANTZ_CHECKED = True  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        _fn_with_checker.PYANTZ_CHECK_AT_STARTUP = check_at_startup  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        _fn_with_checker.PYANTZ_VALIDATION_MODEL = param_cls  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
        try:
            name = serialize_function(_fn_with_checker)
        except ValueError:
            # not importable by name (e.g., defined inside a function), so it can
            # still run in-process but can't be sent to other processes
            module = getattr(fn, "__module__", None) or "anonymous"
            name = f"{module}.{getattr(fn, '__qualname__', 'some_fn')}"
        _fn_with_checker.PYANTZ_NAME = name  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]

        PYANTZ_REGISTERED_FUNCTION[_fn_with_checker.PYANTZ_NAME] = _fn_with_checker  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]

        return _fn_with_checker

    return _decorate_fn_with_params


def get_parameters(fn: Any) -> type[BaseModel] | None:  # noqa: ANN401
    """Get the add parameters if PYANTZ_VALIDATION_MODEL set.

    Args:
        fn: a job function.

    Returns:
        type[BaseModel] | None: the parameters model ``fn`` was registered with by
        :func:`add_parameters`, or None if it wasn't.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.parameters.decorators import (
                get_parameters,
            )
            from pyantz.jobs.files.simple import mkdir
            from pyantz.jobs.testing.nop import do_nothing

            print(get_parameters(mkdir).__name__, get_parameters(do_nothing))

        .. testoutput::

            Mkdirparams None

    """
    return (
        fn.PYANTZ_VALIDATION_MODEL if hasattr(fn, "PYANTZ_VALIDATION_MODEL") else None
    )


def update_deps[T: BaseModel](
    fn: Callable[[T, list[JobConfig]], list[JobConfig]],
) -> Callable[[T, list[JobConfig]], list[JobConfig]]:
    """Wrap a compilation function in a wrapper.

    This will "scramble" the ids of all the jobs to reduce conflicts of
    multiple ids as they're wrapped into virtual jobs. While other jobs
    **should** handle this, this will make life easier.

    Args:
        fn: the ``compile_virtual`` method of a virtual job's parameters model.

    Returns:
        Callable[[T, list[JobConfig]], list[JobConfig]]: the method, given the
        dependent jobs with new ids.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import JobConfig, update_deps

            @update_deps
            def compile_virtual(params, deps):
                return deps

            nop = "pyantz.jobs.testing.nop.do_nothing"
            first = JobConfig(job_id="first", function=nop, parameters={})
            second = JobConfig(depends_on={"first"}, function=nop, parameters={})
            new_first, new_second = compile_virtual(None, [first, second])
            print(new_first.job_id != "first")
            print(new_second.depends_on == {new_first.job_id})

        .. testoutput::

            True
            True

    """

    @wraps(fn)
    def scramble_deps(job_params: T, deps: list[JobConfig]) -> list[JobConfig]:
        """Re-map all job ids to fresh UUIDs while preserving the dependency graph.

        Args:
            job_params: the virtual job's parameters.
            deps: the jobs depending on the virtual job.

        Returns:
            list[JobConfig]: the result of ``fn``.

        Raises:
            Exception: anything raised by ``fn``.

        """
        old_ids_to_new_ids = {job.job_id: str(uuid.uuid4()) for job in deps}

        deps = [
            job.model_copy(
                update={
                    "job_id": old_ids_to_new_ids[job.job_id],
                    # ids outside of this list (external jobs) are left unchanged
                    "depends_on": {
                        old_ids_to_new_ids.get(dep, dep)
                        for dep in (job.depends_on or set())
                    }
                    if job.depends_on
                    else job.depends_on,
                }
            )
            for job in deps
        ]

        return fn(job_params, deps)

    return scramble_deps


def mark_virtual[T](fn: T) -> T:
    """Add a parameter marking the function as a virtual job.

    Used as a decorator on the parameters model of a virtual job, which must have
    a ``compile_virtual`` method (see
    :class:`~pyantz.infrastructure.config.VirtualParamModel`).

    Args:
        fn: the parameters model (or function) to mark.

    Returns:
        T: ``fn`` itself, marked.

    Raises:
        AttributeError: if ``fn`` doesn't accept new attributes.

    Example:
        .. testcode::

            from pydantic import BaseModel

            from pyantz.infrastructure.config import is_virtual, mark_virtual

            @mark_virtual
            class Nothing(BaseModel):
                def compile_virtual(self, deps):
                    return deps

            print(is_virtual(Nothing))

        .. testoutput::

            True

    """
    setattr(fn, VIRTUAL_MARKER, True)  # type: ignore[attr-defined] # pyright: ignore[reportFunctionMemberAccess]

    return fn


def is_virtual(fn: Any) -> bool:  # noqa: ANN401
    """Return true if the function is marked as virtual.

    Args:
        fn: the item to check.

    Returns:
        bool: True if ``fn`` was marked by :func:`mark_virtual`.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.config import is_virtual
            from pyantz.virtual.add_variables import AddVariables
            from pyantz.jobs.testing.nop import do_nothing

            print(is_virtual(AddVariables), is_virtual(do_nothing))

        .. testoutput::

            True False

    """
    return hasattr(fn, VIRTUAL_MARKER) and getattr(fn, VIRTUAL_MARKER)
