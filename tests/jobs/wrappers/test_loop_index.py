"""Test the iteration index and failure handling of the local for loop."""

import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

LOOP = "pyantz.jobs.wrappers.loops.local_for_loop"
CREATE = "pyantz.jobs.files.simple.create"
DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch"


def _run(tmp_path: Path, parameters: dict[str, Any]) -> SqliteQueue:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    start(
        {
            "jobs": [{"function": LOOP, "parameters": parameters}],
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "working_directory": os.fspath(work),
            },
        },
    )
    return SqliteQueue(work / "queue.db")


def test_each_iteration_sees_its_index(tmp_path: Path) -> None:
    """Three iterations of a create job make three differently named files."""
    out = tmp_path / "out"
    out.mkdir()
    job = {
        "function": CREATE,
        "parameters": {"path": os.fspath(out / "out_%{loop_index}.txt")},
    }

    queue = _run(tmp_path, {"num_iterations": 3, "jobs": [job]})

    assert sorted(p.name for p in out.iterdir()) == [
        "out_0.txt",
        "out_1.txt",
        "out_2.txt",
    ]
    assert queue.get_jobs_report().success == 1


def test_index_variable_name_can_be_chosen(tmp_path: Path) -> None:
    """The name of the variable is configurable and shared by all jobs of a pass."""
    out = tmp_path / "out"
    out.mkdir()
    jobs = [
        {
            "function": CREATE,
            "parameters": {"path": os.fspath(out / f"{name}_%{{i}}")},
        }
        for name in ("a", "b")
    ]

    _run(tmp_path, {"num_iterations": 2, "jobs": jobs, "index_variable": "i"})

    assert sorted(p.name for p in out.iterdir()) == ["a_0", "a_1", "b_0", "b_1"]


def test_continue_after_failure_runs_everything_and_fails(tmp_path: Path) -> None:
    """With stop_on_failure=False every iteration runs, but the loop fails."""
    log = tmp_path / "log"
    jobs = [
        {"function": DISPATCH, "parameters": {"cmd": ["false"]}},
        {
            "function": DISPATCH,
            "parameters": {"cmd": ["sh", "-c", f'echo "%{{loop_index}}" >> "{log}"']},
        },
    ]

    queue = _run(
        tmp_path,
        {"num_iterations": 3, "jobs": jobs, "stop_on_failure": False},
    )

    assert log.read_text().split() == ["0", "1", "2"]
    assert queue.get_jobs_report().error == 1


def test_stops_at_first_failure_by_default(tmp_path: Path) -> None:
    """By default nothing runs after the first failure."""
    log = tmp_path / "log"
    jobs = [
        {"function": DISPATCH, "parameters": {"cmd": ["false"]}},
        {
            "function": DISPATCH,
            "parameters": {"cmd": ["sh", "-c", f'echo x >> "{log}"']},
        },
    ]

    queue = _run(tmp_path, {"num_iterations": 3, "jobs": jobs})

    assert not log.exists()
    assert queue.get_jobs_report().error == 1


def test_outer_variables_are_still_visible(tmp_path: Path) -> None:
    """The loop adds its index to the variables of the enclosing scope."""
    out = tmp_path / "out"
    out.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    start(
        {
            "variables": {"prefix": "run"},
            "jobs": [
                {
                    "function": LOOP,
                    "parameters": {
                        "num_iterations": 2,
                        "jobs": [
                            {
                                "function": CREATE,
                                "parameters": {
                                    "path": os.fspath(out / "%{prefix}_%{loop_index}"),
                                },
                            },
                        ],
                    },
                },
            ],
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "working_directory": os.fspath(work),
            },
        },
    )

    assert sorted(p.name for p in out.iterdir()) == ["run_0", "run_1"]
