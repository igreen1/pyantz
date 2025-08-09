"""Start the server."""

import argparse
import os
from typing import TYPE_CHECKING

import uvicorn

from .server import app

if TYPE_CHECKING:
    from fastapi import FastAPI

HOSTNAME: str = os.environ.get("PYANTZ_HOST", "localhost")
PORT: int = int(os.environ.get("PYANTZ_PORT", "8000"))

parser = argparse.ArgumentParser(prog="antz-api")
parser.add_argument(
    "--reload",
    dest="reload",
    help="Used for development. If true, uvicorn will hot reload the server",
    required=False,
    default=False,
    choices=["true", "false"]
)
_truthy_dict: dict[str, bool] = {
    "true": True,
    "1": True,
    "false": False,
    "0": False,
}


def run_api() -> None:
    """Start up the application on uvicorn."""
    args = parser.parse_args()
    reload_input: str = args.reload
    reload: bool = False
    if reload_input:
        reload = _truthy_dict.get(reload_input.lower(), False)

    uvicorn_app: str | FastAPI = "pyantz.api.server:app" if reload else app
    uvicorn.run(uvicorn_app, host=HOSTNAME, port=PORT, reload=reload)


if __name__ == "__main__":
    run_api()
