"""Check the structure of a set of jobs: ids, dependencies and cycles.

:func:`find_graph_problems` reports every problem at once, so that a user can fix a
configuration in one go instead of one error at a time.
"""

from __future__ import annotations

import graphlib
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .abstract_job import AbstractJobConfig


def find_graph_problems(jobs: Iterable[AbstractJobConfig]) -> list[str]:
    """List everything wrong with the ids and dependencies of the jobs.

    Args:
        jobs: the jobs of one pipeline (virtual jobs included)

    Returns:
        list[str]: a message for each problem; empty if the jobs are fine

    """
    job_list = list(jobs)
    problems: list[str] = []

    counts = Counter(job.job_id for job in job_list)
    problems.extend(
        f"Duplicate job_id {job_id!r} (used by {count} jobs)"
        for job_id, count in counts.items()
        if count > 1
    )

    known = set(counts)
    for job in job_list:
        missing = sorted((job.depends_on or set()) - known)
        problems.extend(
            f"Job {job.job_id!r} depends on unknown job {dependency!r}"
            for dependency in missing
        )

    graph = {job.job_id: (job.depends_on or set()) & known for job in job_list}
    try:
        graphlib.TopologicalSorter(graph).prepare()
    except graphlib.CycleError as exc:
        problems.append(f"Dependency cycle: {' -> '.join(exc.args[1])}")

    return problems
