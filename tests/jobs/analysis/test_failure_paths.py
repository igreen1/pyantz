"""Test the failure paths and options of the analysis jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import polars as pl
import pytest

from pyantz.jobs.analysis.external import (
    ExternalAnalysisParams,
    ExternalExtractParams,
    ExternalSimpleParams,
    external_analysis,
    external_simple,
    save_from_external_extraction,
)
from pyantz.jobs.analysis.simple import (
    ColumnarOperationParameters,
    JoinParquetParams,
    columnar_operation,
    join_parquets,
)

if TYPE_CHECKING:
    from pathlib import Path


def _loaders(
    **loaders: Literal["lazy", "eager"],
) -> dict[str, Literal["lazy", "eager"]]:
    """Choose lazy or eager loading per variable, typed as the parameters expect."""
    return loaders


def returns_true() -> bool:
    """Succeed."""
    return True


def returns_false() -> bool:
    """Fail."""
    return False


def returns_none() -> None:
    """Return nothing, which counts as success."""
    return


def raises() -> None:
    """Fail by raising."""
    msg = "boom"
    raise RuntimeError(msg)


def returns_lazy_frame() -> pl.LazyFrame:
    """Give a lazy frame."""
    return pl.LazyFrame({"a": [1, 2]})


def returns_eager_frame() -> pl.DataFrame:
    """Give a frame."""
    return pl.DataFrame({"a": [1, 2]})


def returns_text() -> str:
    """Give something which is not a frame."""
    return "text"


def total(data: pl.DataFrame, extra: int = 0) -> None:
    """Fail unless the data was given as an eager frame."""
    assert isinstance(data, pl.DataFrame)
    assert data["a"].sum() + extra == 6  # noqa: PLR2004


def run(job: Any, params: Any) -> bool:  # noqa: ANN401
    """Run a job function with its parameters."""
    return job(params.model_dump(), lambda *_: None)


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        (returns_true, True),
        (returns_false, False),
        (returns_none, True),
        (raises, False),
    ],
)
def test_external_simple(function: Any, expected: bool) -> None:  # noqa: ANN401, FBT001
    """A bool result is passed on, no result is success, an exception fails."""
    params = ExternalSimpleParams(external_function=function)

    assert run(external_simple, params) is expected


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        (returns_lazy_frame, True),
        (returns_eager_frame, True),
        (returns_text, False),
        (raises, False),
    ],
)
def test_extraction_result_types(
    tmp_path: Path,
    function: Any,  # noqa: ANN401
    expected: bool,  # noqa: FBT001
) -> None:
    """Frames are saved; anything else, or an exception, fails the job."""
    out = tmp_path / "out.parquet"
    params = ExternalExtractParams(
        external_function=function, result_parquet_location=str(out)
    )

    assert run(save_from_external_extraction, params) is expected
    assert out.exists() is expected


def test_analysis_loads_each_variable_as_asked(tmp_path: Path) -> None:
    """Per-variable lazy/eager choices and the extra kwargs reach the function."""
    data = tmp_path / "data.parquet"
    pl.DataFrame({"a": [1, 2, 3]}).write_parquet(data)

    params = ExternalAnalysisParams(
        variable_names_to_parquets={"data": data},
        lazy_or_eager=_loaders(data="eager"),
        function_kwargs={"extra": 0},
        external_function=total,
    )

    assert run(external_analysis, params) is True


def test_analysis_needs_a_loader_for_every_variable(tmp_path: Path) -> None:
    """A mapping which leaves a variable out fails the job."""
    data = tmp_path / "data.parquet"
    pl.DataFrame({"a": [1, 2, 3]}).write_parquet(data)
    params = ExternalAnalysisParams(
        variable_names_to_parquets={"data": data},
        lazy_or_eager=_loaders(other="eager"),
        external_function=total,
    )

    assert run(external_analysis, params) is False


def test_analysis_function_errors_fail_the_job(tmp_path: Path) -> None:
    """An exception (here an assertion) in the function fails the job."""
    data = tmp_path / "data.parquet"
    pl.DataFrame({"a": [1]}).write_parquet(data)
    params = ExternalAnalysisParams(
        variable_names_to_parquets={"data": data},
        lazy_or_eager="eager",
        external_function=total,
    )

    assert run(external_analysis, params) is False


def _columnar(tmp_path: Path, **changes: Any) -> ColumnarOperationParameters:  # noqa: ANN401
    source = tmp_path / "source.parquet"
    if not source.exists():
        pl.DataFrame({"a": [1, 2], "b": [3, 4]}).write_parquet(source)
    values = {
        "source_parquet_file": source,
        "result_parquet_file": str(tmp_path / "result.parquet"),
        "left_col": "a",
        "right_col": "b",
        "result_col": "c",
        "operation": "+",
    }
    return ColumnarOperationParameters.model_validate({**values, **changes})


def test_columnar_operation_adds_the_column(tmp_path: Path) -> None:
    """The result column holds the operation applied to the two columns."""
    params = _columnar(tmp_path)

    assert run(columnar_operation, params) is True

    assert pl.read_parquet(params.result_parquet_file)["c"].to_list() == [4, 6]


def test_columnar_operation_missing_source(tmp_path: Path) -> None:
    """A source which doesn't exist fails the job."""
    params = _columnar(tmp_path, source_parquet_file=tmp_path / "missing.parquet")

    assert run(columnar_operation, params) is False


def test_columnar_operation_unknown_column(tmp_path: Path) -> None:
    """A column which isn't in the file fails the job."""
    params = _columnar(tmp_path, left_col="nope")

    assert run(columnar_operation, params) is False


def test_columnar_operation_unwritable_result(tmp_path: Path) -> None:
    """A result file which can't be written fails the job."""
    params = _columnar(tmp_path, result_parquet_file=str(tmp_path / "no" / "r.parquet"))

    assert run(columnar_operation, params) is False


def test_join_parquets(tmp_path: Path) -> None:
    """Two files are joined on the column."""
    left, right = tmp_path / "left.parquet", tmp_path / "right.parquet"
    pl.DataFrame({"k": [1, 2], "x": [10, 20]}).write_parquet(left)
    pl.DataFrame({"k": [2, 3], "y": [200, 300]}).write_parquet(right)
    params = JoinParquetParams(
        left_parquet=left,
        right_parquet=right,
        output_parquet=tmp_path / "out.parquet",
        on_="k",
    )

    assert run(join_parquets, params) is True

    assert pl.read_parquet(params.output_parquet).to_dicts() == [
        {"k": 2, "x": 20, "y": 200}
    ]


def test_join_parquets_failure(tmp_path: Path) -> None:
    """Files which can't be read fail the job."""
    params = JoinParquetParams(
        left_parquet=tmp_path / "missing.parquet",
        right_parquet=tmp_path / "missing2.parquet",
        output_parquet=tmp_path / "out.parquet",
        on_="k",
    )

    assert run(join_parquets, params) is False


def test_join_output_cannot_overwrite_an_input(tmp_path: Path) -> None:
    """The output may not be one of the inputs."""
    same = tmp_path / "same.parquet"

    with pytest.raises(ValueError, match="cannot be the same"):
        JoinParquetParams(
            left_parquet=same,
            right_parquet=tmp_path / "other.parquet",
            output_parquet=same,
            on_="k",
        )
