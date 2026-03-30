"""Primary way to run a configuration.

Pass a path to the configuration file.
"""

import argparse as _argparse
from pathlib import Path as _Path
from typing import Any

from pyantz import start as _start
from pyantz.infrastructure.config import InitialConfig as _InitialConfig

if __name__ == "__main__":
    parser = _argparse.ArgumentParser("PyAntz", description="Run a DAG of data jobs.")
    parser.add_argument(
        "config_location", help="JSON file with the configuration to run"
    )

    args = parser.parse_args()
    config_location = _Path(args.config_location)

    if not config_location.exists():
        no_such_file: str = f"No such file {config_location}"
        raise RuntimeError(no_such_file)

    # load config
    config_text = config_location.read_text(encoding="utf-8")
    config: _InitialConfig[Any] = _InitialConfig.model_validate_json(config_text)  # pyright: ignore[reportUnknownVariableType]
    _start(config)
