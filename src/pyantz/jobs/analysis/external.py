"""Call a separate python function to munge data and save the results."""

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

    #: Arguments to pass directly to the job
    function_args: list[Any] = Field(default_factory=list)

    #: Keyword arguments to pass directly to the job
    function_kwargs: dict[str, Any] = Field(default_factory=dict)

    #: Fully resolved name of the function, e.g. `package.module.function`
    #: Function must return a polars dataframe
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

    #: Location to save the result from the function
    result_parquet_location: str

    @field_serializer("external_function")
    def serialize_job_function(
        self,
        fn: Callable[..., pl.DataFrame | pl.LazyFrame],
    ) -> str:
        """Serialize the fucntion."""
        return serialize_function(fn)


@add_parameters(ExternalExtractParams)
@no_submit_fn
def save_from_external_extraction(params: ExternalExtractParams) -> bool:
    """Call a user defined function and save the results off.

    While the user could directly call their function, the utility of this
    function is saving it in the parquet file, allowing the user to ignore the file
    system fun.

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

    #: Arguments to pass directly to the job
    function_args: list[Any] = Field(default_factory=list)

    #: Keyword arguments to pass directly to the job
    function_kwargs: dict[str, Any] = Field(default_factory=dict)

    #: Fully resolved name of the function, e.g. `package.module.function`
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

    @field_serializer("external_function")
    def serialize_job_function(
        self,
        fn: Callable[..., pl.DataFrame | pl.LazyFrame],
    ) -> str:
        """Serialize the fucntion."""
        return serialize_function(fn)


@add_parameters(ExternalSimpleParams)
@no_submit_fn
def external_simple(params: ExternalSimpleParams) -> bool:
    """Call the external function."""
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

    #: map variable names to parquet files
    #: the parquet files will be read into polars lazy or dataframes
    #: and passed as kwargs to the analysis function
    variable_names_to_parquets: Mapping[str, Path]

    #: if lazy, all dataframes are scanned into memory
    #: if eager, all dataframes are scanned into memory
    #: if a mapping, maps each variable name from `variable_names_to_files` to one
    lazy_or_eager: Literal["lazy", "eager"] | Mapping[str, Literal["lazy", "eager"]]

    #: Arguments to pass directly to the job
    function_args: list[Any] = Field(default_factory=list)

    #: Keyword arguments to pass directly to the job
    function_kwargs: dict[str, Any] = Field(default_factory=dict)

    #: Fully resolved name of the function, e.g. `package.module.function`
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

    @field_serializer("external_function")
    def serialize_job_function(
        self,
        fn: Callable[..., Any],
    ) -> str:
        """Serialize the fucntion."""
        return serialize_function(fn)


@add_parameters(ExternalAnalysisParams)
@no_submit_fn
def external_analysis(params: ExternalAnalysisParams) -> bool:
    """Call some external function with the data loaded into polars."""
    logger = logging.getLogger(__name__)

    _mapping: dict[Literal["lazy", "eager"], Callable[..., Any]] = {
        "lazy": pl.scan_parquet,
        "eager": pl.read_parquet,
    }

    def get_loader_func(variable_name: str) -> Callable[..., Any]:
        if isinstance(params.lazy_or_eager, Mapping):
            return_type = params.lazy_or_eager.get(variable_name)
            if not return_type:
                logger.error(
                    "User must register %s with a lazy or eager loader", variable_name
                )
                raise RuntimeError
        else:
            return_type = params.lazy_or_eager
        return _mapping[return_type]

    try:
        variables = {
            var_name: get_loader_func(var_name)(file_path)
            for var_name, file_path in params.variable_names_to_parquets.items()
        }
    except RuntimeError:
        logger.debug("IO Error, cannot run external function")
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
