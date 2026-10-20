#!/bin/bash
#SBATCH --export=ALL

# Run the command given as arguments, exactly as given (quoting preserved).
# pyantz passes the python interpreter it was started with, so the compute node
# uses the same environment instead of whatever `python` is on its PATH.
exec "$@"
