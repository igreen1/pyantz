"""Dump the description and parameter schema of every job as json.

The frontend tests use the dump as a fixture, so they see the schemas as the
api serves them. Run ``python -m pyantz.api.dump_schemas [FILE]`` (standard output
without a file) to regenerate it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# import jobs so that they are all imported/registered
import pyantz.jobs  # pyright: ignore[reportUnusedImport] # noqa: F401
from pyantz.api.endpoints.get_jobs.endpoint import describe_job
from pyantz.api.endpoints.get_parameters.endpoints import get_job_schema
from pyantz.infrastructure.config.fn_utils import serialize_function
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions


def dump_schemas() -> dict[str, dict[str, object]]:
    """Get the description and schema of each job, by job name and sorted by it.

    Args:
        None.

    Returns:
        dict[str, dict[str, object]]: for each registered job, its
        ``description`` and the ``json_schema`` of its parameters.

    Raises:
        fastapi.HTTPException: if a registered job has no parameters model.

    Example:
        .. testcode::

            from pyantz.api.dump_schemas import dump_schemas

            copy = dump_schemas()["pyantz.jobs.files.simple.copy"]
            print(copy["description"], sorted(copy["json_schema"]["properties"]))

        .. testoutput::

            Copy from src to destination. ['dst', 'src']

    """
    jobs: dict[str, dict[str, object]] = {}
    for fn in get_registered_functions():
        name = serialize_function(fn)
        jobs[name] = {
            "description": describe_job(fn),
            "json_schema": get_job_schema(name).json_schema,
        }
    return dict(sorted(jobs.items()))


def main() -> None:
    """Write the dump to the file given as argument, or to standard output.

    Args:
        None.

    Returns:
        None.

    Raises:
        OSError: if the file can't be written.

    """
    text = json.dumps(dump_schemas(), indent=2, sort_keys=True) + "\n"
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
