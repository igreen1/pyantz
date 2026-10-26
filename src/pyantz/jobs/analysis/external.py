"""Jobs that call user-defined Python functions for data extraction and analysis.

:func:`save_from_external_extraction` calls a user function and saves the
returned Polars DataFrame to a Parquet file.

:func:`external_simple` calls a function and returns its boolean result.

:func:`external_analysis` loads one or more Parquet files into Polars
frames, then passes them as keyword arguments to a user function.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Annotated, Any, Literal

import polars as pl
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    WithJsonSchema,
    field_serializer,
)

from pyantz.infrastructure.config import add_parameters, no_submit_fn
from pyantz.infrastructure.config.fn_utils import (
    import_function_by_name,
    serialize_function,
)


class ExternalExtractParams(BaseModel):
    """Parameters to call an external function returning a polars dataframe."""

    model_config = ConfigDict(frozen=True)

    function_args: list[Any] = Field(default_factory=list)
    """Positional arguments to pass directly to the function."""

    function_kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass directly to the function."""

    external_function: Annotated[
        Callable[..., pl.DataFrame | pl.LazyFrame],
        BeforeValidator(import_function_by_name),
        WithJsonSchema(
            {
                "type": "string",
                "format": "base64",
            }
        ),
    ]
    """Fully resolved name of the function, e.g. ``package.module.function``; it
    must return a polars DataFrame or LazyFrame."""

    result_parquet_location: str
    """Location to save the result from the function."""

    @field_serializer("external_function")
    def serialize_job_function(
        self,
        fn: Callable[..., pl.DataFrame | pl.LazyFrame],
    ) -> str:
        """Serialize the function.

        Args:
            fn: the function to serialize.

        Returns:
            str: the function's full import path.

        Raises:
            ValueError: if the function can't be imported by name, e.g., a lambda.

        """
        return serialize_function(fn)


@add_parameters(ExternalExtractParams)
@no_submit_fn
def save_from_external_extraction(params: ExternalExtractParams) -> bool:
    """Call a user defined function and save the results off.

    While the user could directly call their function, the utility of this
    function is saving it in the parquet file, allowing the user to ignore the file
    system fun. Missing parent directories of the parquet are created.

    Args:
        params: the job's parameters, validated as :class:`ExternalExtractParams`.

    Parameters:
        function_args (list[Any]): positional arguments for the function.
            Defaults to none.
        function_kwargs (dict[str, Any]): keyword arguments for the function.
            Defaults to none.
        external_function (str): import path of the function, which must return
            a polars DataFrame or LazyFrame.
        result_parquet_location (str): parquet file to save the result to.

    Returns:
        bool: True if the result was saved, False if the function raises, returns
        something other than a dataframe, or the parquet can't be written.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: analysis-extract

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: analysis-extract

            import polars as pl

            from pyantz.jobs.analysis.external import save_from_external_extraction

            save_from_external_extraction(
                {
                    "external_function": "polars.DataFrame",
                    "function_kwargs": {"data": {"a": [1, 2, 3]}},
                    "result_parquet_location": "out/extracted.parquet",
                },
                lambda job: None,
            )
            print(pl.read_parquet("out/extracted.parquet")["a"].to_list())

        .. testoutput:: analysis-extract

            [1, 2, 3]

        .. testcleanup:: analysis-extract

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)

    try:
        result = params.external_function(
            *params.function_args,
            **params.function_kwargs,
        )
    except Exception as exc:
        logger.exception("Unknown error in user defined function", exc_info=exc)
        return False

    try:
        Path(params.result_parquet_location).parent.mkdir(parents=True, exist_ok=True)
        if isinstance(result, pl.LazyFrame):
            result.sink_parquet(params.result_parquet_location)
        elif isinstance(result, pl.DataFrame):  # pyright: ignore[reportUnnecessaryIsInstance]
            result.write_parquet(params.result_parquet_location)
        else:
            logger.error("Function returned invalid type!")
            return False
    except Exception as exc:
        logger.exception("Error while saving results", exc_info=exc)
        return False
    else:
        return True


class ExternalSimpleParams(BaseModel):
    """Call an external function."""

    model_config = ConfigDict(frozen=True)

    function_args: list[Any] = Field(default_factory=list)
    """Positional arguments to pass directly to the function."""

    function_kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass directly to the function."""

    external_function: Annotated[
        Callable[..., Any],
        BeforeValidator(import_function_by_name),
        WithJsonSchema(
            {
                "type": "string",
                "format": "base64",
            }
        ),
    ]
    """Fully resolved name of the function, e.g. ``package.module.function``."""

    @field_serializer("external_function")
    def serialize_job_function(
        self,
        fn: Callable[..., Any],
    ) -> str:
        """Serialize the function.

        Args:
            fn: the function to serialize.

        Returns:
            str: the function's full import path.

        Raises:
            ValueError: if the function can't be imported by name, e.g., a lambda.

        """
        return serialize_function(fn)


@add_parameters(ExternalSimpleParams)
@no_submit_fn
def external_simple(params: ExternalSimpleParams) -> bool:
    """Call the external function.

    Args:
        params: the job's parameters, validated as :class:`ExternalSimpleParams`.

    Parameters:
        function_args (list[Any]): positional arguments for the function.
            Defaults to none.
        function_kwargs (dict[str, Any]): keyword arguments for the function.
            Defaults to none.
        external_function (str): import path of the function to call.

    Returns:
        bool: the function's result if it returns a bool, False if it raises, and
        True otherwise.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testcode::

            from pyantz.jobs.analysis.external import external_simple

            def submit(job):
                pass

            for args in ([1, 1], [1, 2]):
                params = {"external_function": "operator.eq", "function_args": args}
                print(external_simple(params, submit))

        .. testoutput::

            True
            False

    """
    logger = logging.getLogger(__name__)

    try:
        result = params.external_function(
            *params.function_args, **params.function_kwargs
        )
    except Exception as exc:
        logger.exception("Unknown error in user defined function", exc_info=exc)
        return False
    else:
        if isinstance(result, bool):
            return result
    return True


class ExternalAnalysisParams(BaseModel):
    """Params to pass to an external function which will perform analysis on data."""

    model_config = ConfigDict(frozen=True)

    variable_names_to_parquets: Mapping[str, Path]
    """Maps keyword argument names to parquet files; the parquet files are read
    into polars LazyFrames or DataFrames and passed as keyword arguments to the
    analysis function."""

    lazy_or_eager: Literal["lazy", "eager"] | Mapping[str, Literal["lazy", "eager"]]
    """If ``lazy``, all dataframes are scanned lazily (polars LazyFrames); if
    ``eager``, all dataframes are read into memory (polars DataFrames); if a
    mapping, maps each name of ``variable_names_to_parquets`` to one of those."""

    function_args: list[Any] = Field(default_factory=list)
    """Positional arguments to pass directly to the function."""

    function_kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass directly to the function."""

    external_function: Annotated[
        Callable[..., Any],
        BeforeValidator(import_function_by_name),
        WithJsonSchema(
            {
                "type": "string",
                "format": "base64",
            }
        ),
    ]
    """Fully resolved name of the function, e.g. ``package.module.function``."""

    @field_serializer("external_function")
    def serialize_job_function(
        self,
        fn: Callable[..., Any],
    ) -> str:
        """Serialize the function.

        Args:
            fn: the function to serialize.

        Returns:
            str: the function's full import path.

        Raises:
            ValueError: if the function can't be imported by name, e.g., a lambda.

        """
        return serialize_function(fn)


@add_parameters(ExternalAnalysisParams)
@no_submit_fn
def external_analysis(params: ExternalAnalysisParams) -> bool:
    """Call some external function with the data loaded into polars.

    Each parquet of ``variable_names_to_parquets`` is loaded and passed to the
    function as the keyword argument of its name, after ``function_args`` and
    along with ``function_kwargs``. The function's result is discarded.

    Args:
        params: the job's parameters, validated as :class:`ExternalAnalysisParams`.

    Parameters:
        variable_names_to_parquets (Mapping[str, Path]): keyword argument names
            mapped to the parquet files to load for them.
        lazy_or_eager (str | Mapping[str, str]): ``lazy`` (LazyFrames), ``eager``
            (DataFrames), or one of those for each keyword argument name.
        function_args (list[Any]): positional arguments for the function.
            Defaults to none.
        function_kwargs (dict[str, Any]): more keyword arguments for the
            function. Defaults to none.
        external_function (str): import path of the function to call.

    Returns:
        bool: True if the function ran, False if the data can't be loaded (or a
        name has no ``lazy_or_eager`` entry) or the function raises.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: analysis-external

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: analysis-external

            import polars as pl

            from pyantz.jobs.analysis.external import external_analysis

            pl.DataFrame({"a": [1, 2, 3]}).write_parquet("numbers.parquet")

            # in a configuration, the function is given by its import path
            def report_total(numbers, label):
                print(label, numbers["a"].sum())

            external_analysis(
                {
                    "variable_names_to_parquets": {"numbers": "numbers.parquet"},
                    "lazy_or_eager": "eager",
                    "function_kwargs": {"label": "total:"},
                    "external_function": report_total,
                },
                lambda job: None,
            )

        .. testoutput:: analysis-external

            total: 6

        .. testcleanup:: analysis-external

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)

    _mapping: dict[Literal["lazy", "eager"], Callable[..., Any]] = {
        "lazy": pl.scan_parquet,
        "eager": pl.read_parquet,
    }

    def get_loader_func(variable_name: str) -> Callable[..., Any]:
        """Get the function which loads the parquet of a keyword argument.

        Args:
            variable_name: the name of the keyword argument.

        Returns:
            Callable[..., Any]: :func:`polars.scan_parquet` (lazy) or
            :func:`polars.read_parquet` (eager).

        Raises:
            RuntimeError: if ``lazy_or_eager`` is a mapping without the name.

        """
        if isinstance(params.lazy_or_eager, Mapping):
            return_type = params.lazy_or_eager.get(variable_name)
            if not return_type:
                logger.error(
                    "User must register %s with a lazy or eager loader", variable_name
                )
                msg = f"No lazy or eager loader registered for {variable_name!r}"
                raise RuntimeError(msg)
        else:
            return_type = params.lazy_or_eager
        return _mapping[return_type]

    try:
        variables = {
            var_name: get_loader_func(var_name)(file_path)
            for var_name, file_path in params.variable_names_to_parquets.items()
        }
    except Exception as exc:
        logger.exception("Cannot load the data, not running the function", exc_info=exc)
        return False

    # output of the function is discarded
    try:
        params.external_function(
            *params.function_args, **variables, **params.function_kwargs
        )
    except Exception as exc:
        logger.exception("Unknown error in external function", exc_info=exc)
        return False
    else:
        return True
