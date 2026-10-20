"""Primary way to run a configuration.

Pass a path to the configuration file (JSON or YAML).
"""

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
YAML_SUFFIXES = (".yaml", ".yml")


def _build_parser() -> _argparse.ArgumentParser:
    """Create the command line parser."""
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
    """Read a JSON or YAML file into plain python values."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in YAML_SUFFIXES:
        return _YAML(typ="safe").load(text)
    return _json.loads(text)


def _setup_logging(level: str, log_file: str | None) -> None:
    """Show the logs of pyantz at the requested level."""
    handlers: list[_logging.Handler] = [_logging.StreamHandler()]
    if log_file:
        handlers.append(_logging.FileHandler(log_file, encoding="utf-8"))
    _logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,  # the command line owns the logging setup
    )


def _describe(config: _InitialConfig[Any]) -> str:
    """List the jobs of the configuration and what they depend on."""
    lines = [f"{len(config.jobs)} job(s):"]
    for job in config.jobs:
        name = f" ({job.name})" if job.name else ""
        dependencies = sorted(job.depends_on or set())
        after = f" <- {', '.join(dependencies)}" if dependencies else ""
        lines.append(f"  {job.job_id}{name}{after}")
    return "\n".join(lines)


def main() -> None:
    """Entry point for running pyantz."""
    parser = _build_parser()
    args = parser.parse_args()
    config_location = _Path(args.config_location)

    if not config_location.is_file():
        parser.error(f"No such file {config_location}")

    _setup_logging(args.log_level, args.log_file)

    # load and check the config
    try:
        config: _InitialConfig[Any] = _InitialConfig.model_validate(  # pyright: ignore[reportUnknownVariableType]
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
