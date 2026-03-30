"""Compile virtual jobs to 'real' jobs."""

from __future__ import annotations

import graphlib
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pyantz.infrastructure.config import (
        JobConfig as RealJobConfig,
    )
    from pyantz.infrastructure.config import (
        VirtualJobConfig,
    )

    type AnyJobConfig = RealJobConfig | VirtualJobConfig


def compile_virtual(jobs: list[AnyJobConfig]) -> list[RealJobConfig]:
    """Compile any virtual jobs to concrete jobs."""
    # uncompiled lookup tables
    virtual_job_lookup = {
        job.job_id: cast("VirtualJobConfig", job) for job in jobs if job.virtual
    }
    real_job_lookup = {
        job.job_id: cast("RealJobConfig", job) for job in jobs if not job.virtual
    }
    if not virtual_job_lookup:
        return [*real_job_lookup.values()]

    def get_uncompiled_job_config(job_id: str) -> AnyJobConfig:
        """Get the job definition from its id."""
        lookup_val = real_job_lookup.get(job_id, virtual_job_lookup.get(job_id))
        if lookup_val is None:
            raise ValueError
        return lookup_val

    graph = {job.job_id: job.depends_on or set[str]() for job in jobs}
    compilation_order = reversed(list(graphlib.TopologicalSorter(graph).static_order()))
    compiled_jobs: list[RealJobConfig] = []

    def get_and_consume_dependencies(job_id: str) -> list[RealJobConfig]:
        """Get jobs and `consume` them by removing them from our compiled scope."""
        nonlocal compiled_jobs
        direct_deps = [
            job for job in compiled_jobs if job_id in (job.depends_on or set())
        ]

        if not direct_deps:
            return []

        # remove direct deps from compiled job scope ("consume" them)
        compiled_jobs = [job for job in compiled_jobs if job not in direct_deps]

        # get indirect dependencies
        indirect_deps = [
            indirect_dep
            for direct_dep in direct_deps
            for indirect_dep in get_and_consume_dependencies(direct_dep.job_id)
        ]

        return [*direct_deps, *indirect_deps]

    for node_to_compile in compilation_order:
        node_def = get_uncompiled_job_config(node_to_compile)
        node_deps = get_and_consume_dependencies(node_to_compile)
        compile_results = _compile_singular(node_def, node_deps)
        compiled_jobs.extend(compile_results)

    return compiled_jobs


def _compile_singular(
    job: AnyJobConfig, dep_jobs: list[RealJobConfig]
) -> list[RealJobConfig]:
    """Compile the given job.

    Virtual jobs will "consume" this dependencies (they will likely wrap them).
    """
    if not job.virtual:
        return [cast("RealJobConfig", job), *dep_jobs]
    return cast("VirtualJobConfig", job).compile_virtual(dep_jobs)
