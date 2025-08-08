"""The base entry level of the module.

This file takes the initial config and sets up everything
"""

import argparse
import json
import pathlib
import warnings
from collections.abc import Mapping
from typing import Any

from pyantz.infrastructure.config.base import InitialConfig
from pyantz.infrastructure.submitters.local import run_local_submitter
from pyantz.infrastructure.submitters.slurm.basic_slurm import run_slurm_local


def run(config: Mapping[str, Any] | InitialConfig) -> None:
    """Run the provided configuration.

    Calls the correct initial submitter and submits the first configuration
    """
    validated_config = InitialConfig.model_validate(config)

    if validated_config.submitter_config.type == "local":
        thread_handle = run_local_submitter(validated_config)
        thread_handle.join()  # wait for child threads to finish
    elif validated_config.submitter_config.type == "slurm_basic":
        run_slurm_local(validated_config)
    else:
        msg = f"Unknown submitter type: {validated_config.submitter_config.type}"
        raise RuntimeError(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="antz")
    parser.add_argument(
        "--config",
        "-c",
        help="Path to the configuration of the entire analysis pipeline",
        required=True,
    )

    args = parser.parse_args()

    try:
        with pathlib.Path(args.config).open(mode="r", encoding="utf-8") as fh:
            _loaded_config = json.load(fh)
    except FileNotFoundError:
        warnings.warn("No such file for configuration", stacklevel=2)
    except OSError:
        warnings.warn("Unable to open file for unknown IO error", stacklevel=2)
    except ValueError:
        warnings.warn("JSON invalid, unable to decode. See error for details", stacklevel=2)
        raise
    else:
        run(_loaded_config)
