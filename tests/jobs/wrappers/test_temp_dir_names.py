"""Test the names of the temporary directories made for remote runs."""

import re
from pathlib import Path
from typing import TYPE_CHECKING

from pyantz.jobs.wrappers.variables import (
    TemporaryDirectoryParams,
    _run_jobs_temp_dir_remote,
)

if TYPE_CHECKING:
    from pyantz.infrastructure.config import JobConfig


def _directories_created(shared: Path, count: int) -> list[str]:
    names: list[str] = []
    for _ in range(count):
        submitted: list[JobConfig] = []
        params = TemporaryDirectoryParams(
            jobs=[],
            variable_name="tmp",
            submit_type="remote",
            shared_working_dir=shared,
        )
        _run_jobs_temp_dir_remote(params, submitted.append)
        mkdir_job = submitted[0]
        names.append(Path(mkdir_job.parameters["dir_path"]).name)
    return names


def test_names_are_uuid_based(tmp_path: Path) -> None:
    """Each name is `tempdir_` followed by a 32 digit hex uuid."""
    (name,) = _directories_created(tmp_path, 1)

    assert re.fullmatch(r"tempdir_[0-9a-f]{32}", name)


def test_names_do_not_repeat_even_with_the_same_random_seed(tmp_path: Path) -> None:
    """Seeding python's random module doesn't make the names predictable."""
    import random  # noqa: PLC0415

    random.seed(1234)
    first = _directories_created(tmp_path, 20)
    random.seed(1234)
    second = _directories_created(tmp_path, 20)

    assert len(set(first)) == len(first)
    assert set(first).isdisjoint(second)
