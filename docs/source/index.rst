PyAntz documentation
====================

Many small jobs work together to do big things!

PyAntz is a local-first DAG pipeline runner: pipelines are JSON/YAML
configurations whose jobs name Python functions by their import path, run with
local multiprocessing or on a SLURM cluster, optionally on a remote host.

.. toctree::
   :maxdepth: 2
   :caption: Guide:

   getting_started
   writing_jobs
   job_library

.. toctree::
   :maxdepth: 2
   :caption: API reference:

   pyantz
