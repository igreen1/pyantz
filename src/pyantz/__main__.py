"""Primary way to run a configuration.

Pass a path to the configuration file (JSON or YAML)::

    pyantz config.json
    pyantz config.yaml --validate
    pyantz config.json --log-level DEBUG --log-file run.log

The exit status is 1 if the configuration is invalid or a job failed.
"""

from __future__ import annotations

import argparse as _argparse
import json as _json
import logging as _logging
import sys as _sys
from pathlib import Path as _Path
from typing import Any

from pydantic import ValidationError as _ValidationError
from ruamel.yaml import YAML as _YAML
from ruamel.yaml.error import YAMLError as _YAMLError

from pyantz import start as _start
from pyantz.infrastructure.config import InitialConfig as _InitialConfig

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
"""Choices of ``--log-level``."""

YAML_SUFFIXES = (".yaml", ".yml")
"""Endings of configuration files read as YAML; others are read as JSON."""


def _build_parser() -> _argparse.ArgumentParser:
    """Create the command line parser.

    Args:
        None.

    Returns:
        argparse.ArgumentParser: the parser of ``pyantz``'s arguments.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.__main__ import _build_parser

            args = _build_parser().parse_args(["config.yaml", "--log-level", "debug"])
            print(args.config_location, args.log_level, args.validate)

        .. testoutput::

            config.yaml DEBUG False

    """
    parser = _argparse.ArgumentParser("PyAntz", description="Run a DAG of data jobs.")
    parser.add_argument(
        "config_location",
        help="JSON or YAML (.yaml / .yml) file with the configuration to run",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="check the configuration and print the jobs and their dependencies "
        "without running anything (exit status 1 if it is invalid)",
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        type=str.upper,
        default="INFO",
        help="how much to log (default: %(default)s)",
    )
    parser.add_argument("--log-file", help="also write the log to this file")
    return parser


def _load_config_data(path: _Path) -> Any:  # noqa: ANN401
    r"""Read a JSON or YAML file into plain python values.

    Args:
        path: the file; read as YAML if it ends with ``.yaml`` or ``.yml``.

    Returns:
        Any: the file's contents.

    Raises:
        OSError: if the file can't be read.
        ValueError: if a JSON file is invalid.
        ruamel.yaml.error.YAMLError: if a YAML file is invalid.

    Example:
        .. testsetup:: main-load-config

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: main-load-config

            from pathlib import Path

            from pyantz.__main__ import _load_config_data

            Path("config.yaml").write_text("jobs: []\nvariables: {name: test}\n")
            print(_load_config_data(Path("config.yaml")))

        .. testoutput:: main-load-config

            {'jobs': [], 'variables': {'name': 'test'}}

        .. testcleanup:: main-load-config

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in YAML_SUFFIXES:
        return _YAML(typ="safe").load(text)
    return _json.loads(text)


def _setup_logging(level: str, log_file: str | None) -> None:
    """Show the logs of pyantz at the requested level.

    Replaces any logging setup already made.

    Args:
        level: the lowest level shown, e.g., ``"INFO"``.
        log_file: if set, also write the log to this file.

    Returns:
        None.

    Raises:
        OSError: if the log file can't be opened.

    """
    handlers: list[_logging.Handler] = [_logging.StreamHandler()]
    if log_file:
        handlers.append(_logging.FileHandler(log_file, encoding="utf-8"))
    _logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,  # the command line owns the logging setup
    )


def _describe(config: _InitialConfig) -> str:
    """List the jobs of the configuration and what they depend on.

    Args:
        config: the validated configuration.

    Returns:
        str: one line per job: its id, name and the ids it depends on.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.__main__ import _describe
            from pyantz.infrastructure.config import InitialConfig

            nop = "pyantz.jobs.testing.nop.do_nothing"
            config = InitialConfig.model_validate(
                {
                    "submitter": {"type_": "local_proc", "working_directory": "."},
                    "jobs": [
                        {"job_id": "a", "name": "first", "function": nop,
                         "parameters": {}},
                        {"job_id": "b", "function": nop, "parameters": {},
                         "depends_on": ["a"]},
                    ],
                }
            )
            print(_describe(config))

        .. testoutput::

            2 job(s):
              a (first)
              b <- a

    """
    lines = [f"{len(config.jobs)} job(s):"]
    for job in config.jobs:
        name = f" ({job.name})" if job.name else ""
        dependencies = sorted(job.depends_on or set())
        after = f" <- {', '.join(dependencies)}" if dependencies else ""
        lines.append(f"  {job.job_id}{name}{after}")
    return "\n".join(lines)


def main() -> None:
    """Entry point for running pyantz.

    Reads the command line (see :func:`_build_parser`), checks the configuration
    and runs it, or only describes it with ``--validate``.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: with status 1 if the configuration is invalid or a job
            failed, 2 if the arguments are invalid or the file doesn't exist.

    """
    parser = _build_parser()
    args = parser.parse_args()
    config_location = _Path(args.config_location)

    if not config_location.is_file():
        parser.error(f"No such file {config_location}")

    _setup_logging(args.log_level, args.log_file)

    # load and check the config
    try:
        config: _InitialConfig = _InitialConfig.model_validate(
            _load_config_data(config_location),
        )
    except (
        _ValidationError,
        ValueError,
        TypeError,
        ImportError,
        AttributeError,
        _YAMLError,
    ) as exc:
        print(f"Invalid configuration {config_location}:\n{exc}", file=_sys.stderr)  # noqa: T201
        _sys.exit(1)

    if args.validate:
        print(_describe(config))  # noqa: T201
        return

    report = _start(config)
    if report is not None and not report.all_succeeded:
        _sys.exit(1)


if __name__ == "__main__":
    main()
