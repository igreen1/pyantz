"""Test the simple get/set operations of the queue."""

from pathlib import Path

import pytest

from pyantz.infrastructure.config.job import JobWithContext
from pyantz.infrastructure.distributed_queue.common.return_types import JobStatus
from pyantz.infrastructure.distributed_queue.sql.sql_queue import CHUNKSIZE, SqliteQueue


@pytest.fixture
def sqlite_queue(tmp_path: Path) -> SqliteQueue:
    """Create a sqlite queue for testing."""
    return SqliteQueue(
        database_file=tmp_path / "queue.db",
    )


def test_put_get_single_item(sqlite_queue: SqliteQueue) -> None:
    """Test putting and getting a single item from a queue."""
    config = JobWithContext(
        job_id="my_job",
        function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
        parameters={},
    )

    sqlite_queue.add_job(
        config,
        None,
    )

    returned_config = sqlite_queue.get_job()

    assert returned_config.payload.type_ == "job"
    assert returned_config.payload.job == config

    assert sqlite_queue.get_job().payload.type_ == "pending"
    sqlite_queue.update_job_status("my_job", JobStatus.SUCCESS)
    assert sqlite_queue.get_job().payload.type_ == "complete"


def test_put_get_large_item(sqlite_queue: SqliteQueue) -> None:
    """Test putting and getting an item greater than one chunk."""
    very_large_config = JobWithContext(
        job_id="my_job",
        function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
        parameters={"my_ver_large_paramter": "char" * (CHUNKSIZE * 3)},
    )
    # sanity check our own test
    assert len(very_large_config.model_dump_json()) > CHUNKSIZE
    sqlite_queue.add_job(
        very_large_config,
        None,
    )

    returned_config = sqlite_queue.get_job()

    assert returned_config.payload.type_ == "job"
    assert returned_config.payload.job == very_large_config
    assert sqlite_queue.get_job().payload.type_ == "pending"
    sqlite_queue.update_job_status("my_job", JobStatus.SUCCESS)
    assert sqlite_queue.get_job().payload.type_ == "complete"


def test_put_get_multiple_items(sqlite_queue: SqliteQueue) -> None:
    """Test putting and getting multiple items with no dependencies."""
    configs: list[JobWithContext] = [
        JobWithContext(
            job_id="job1",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={"my_ver_large_paramter": "char" * (CHUNKSIZE * 3)},
        ),
        JobWithContext(
            job_id="job2",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={},
        ),
        JobWithContext(
            job_id="job3",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={},
        ),
        JobWithContext(
            job_id="job4",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={},
        ),
    ]

    for c in configs:
        sqlite_queue.add_job(c, None)

    for expected_config in configs:
        returned_config = sqlite_queue.get_job()
        assert returned_config.payload.type_ == "job"
        assert returned_config.payload.job == expected_config

    assert sqlite_queue.get_job().payload.type_ == "pending"
    for c in configs:
        sqlite_queue.update_job_status(c.job_id, JobStatus.SUCCESS)
    assert sqlite_queue.get_job().payload.type_ == "complete"


def test_dependency_ordering(sqlite_queue: SqliteQueue) -> None:
    """Test using the queue with a dependency graph.."""
    configs: list[JobWithContext] = [
        JobWithContext(
            job_id="job1",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={"my_ver_large_paramter": "char" * (CHUNKSIZE * 3)},
        ),
        JobWithContext(
            job_id="job2",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={},
            depends_on={"job1"},
        ),
        JobWithContext(
            job_id="job3",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={},
            depends_on={"job2"},
        ),
        JobWithContext(
            job_id="job4",
            function="pyantz.jobs.testing.nop.do_nothing",  # type: ignore[arg-type]
            parameters={},
        ),
    ]

    for c in configs:
        sqlite_queue.add_job(c, None)

    # get the ones with no deps
    for expected_config in [configs[0], configs[3]]:
        returned_config = sqlite_queue.get_job()
        assert returned_config.payload.type_ == "job"
        assert returned_config.payload.job == expected_config
    assert sqlite_queue.get_job().payload.type_ == "pending"

    # now our deps run successfully
    for c in [configs[0], configs[3]]:
        sqlite_queue.update_job_status(c.job_id, JobStatus.SUCCESS)

    # now that job1 is done, job 2 is ready to run
    returned_config = sqlite_queue.get_job()
    assert returned_config.payload.type_ == "job"
    assert returned_config.payload.job == configs[1]
    assert sqlite_queue.get_job().payload.type_ == "pending"

    # now if 2 fails, 3 cannot be run ever so we're complete.
    sqlite_queue.update_job_status("job2", JobStatus.ERROR)
    assert sqlite_queue.get_job().payload.type_ == "complete"
