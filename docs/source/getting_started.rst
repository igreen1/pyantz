Getting started
===============

PyAntz runs pipelines described by a configuration: a list of jobs, each naming a
Python function by its import path, and a *submitter* which says how the jobs run.

Installation
------------

.. code-block:: bash

    pip install pyantz
    # or with uv (recommended):
    uv add pyantz

PyAntz requires Python 3.13 or newer.

A first pipeline
----------------

A configuration is a JSON (or YAML) file, or the equivalent Python mapping. The
``local_proc`` submitter runs the jobs in worker processes on this machine, keeping
its queue in ``working_directory``. A job runs once every job in its
``depends_on`` has succeeded.

.. testsetup:: getting-started-first

    import os, shutil, tempfile
    start_dir = os.getcwd()
    os.chdir(tempfile.mkdtemp())

.. testcode:: getting-started-first

    from pyantz import start

    report = start(
        {
            "submitter": {"type_": "local_proc", "working_directory": "work"},
            "jobs": [
                {
                    "job_id": "write",
                    "function": "pyantz.jobs.files.simple.create",
                    "parameters": {"path": "hello.txt", "contents": "hello"},
                },
                {
                    "function": "pyantz.jobs.files.simple.copy",
                    "parameters": {"src": "hello.txt", "dst": "copy.txt"},
                    "depends_on": ["write"],
                },
            ],
        }
    )
    print(report.success, "of", report.total, "jobs succeeded")
    print(open("copy.txt").read())

.. testoutput:: getting-started-first

    2 of 2 jobs succeeded
    hello

.. testcleanup:: getting-started-first

    tmp = os.getcwd()
    os.chdir(start_dir)
    shutil.rmtree(tmp)

:func:`pyantz.start` blocks until the local run is over and returns a
:class:`~pyantz.infrastructure.distributed_queue.common.JobsReport`.

Variables
---------

Strings in a job's parameters can refer to variables as ``%{name}``. Variables come
from the configuration's ``variables``, from jobs such as
:func:`~pyantz.jobs.wrappers.loops.local_for_loop` or
:func:`~pyantz.jobs.branching.case_matrix.pipeline_expansion`, and from the virtual
job :class:`~pyantz.virtual.add_variables.AddVariables`. A string which is exactly
one reference keeps the variable's type.

.. testsetup:: getting-started-variables

    import os, shutil, tempfile
    start_dir = os.getcwd()
    os.chdir(tempfile.mkdtemp())

.. testcode:: getting-started-variables

    import os

    from pyantz import start

    start(
        {
            "submitter": {"type_": "local_proc", "working_directory": "work"},
            "variables": {"name": "experiment"},
            "jobs": [
                {
                    "function": "pyantz.jobs.wrappers.loops.local_for_loop",
                    "parameters": {
                        "num_iterations": 2,
                        "jobs": [
                            {
                                "function": "pyantz.jobs.files.simple.mkdir",
                                "parameters": {
                                    "dir_path": "%{name}/run_%{loop_index}",
                                },
                            },
                        ],
                    },
                },
            ],
        }
    )
    print(sorted(os.listdir("experiment")))

.. testoutput:: getting-started-variables

    ['run_0', 'run_1']

.. testcleanup:: getting-started-variables

    tmp = os.getcwd()
    os.chdir(start_dir)
    shutil.rmtree(tmp)

The command line
----------------

.. code-block:: bash

    pyantz config.json                  # run a pipeline (JSON or YAML)
    pyantz config.json --validate       # only check it and list its jobs
    pyantz config.json --log-level DEBUG --log-file run.log
    pyantz-status work                  # progress of the run in "work"

``pyantz`` exits with status 1 if the configuration is invalid or a job failed. See
:mod:`pyantz.__main__` and :mod:`pyantz.status`.

Where the jobs run
------------------

The ``submitter`` decides how jobs run:

* ``local_proc`` (:class:`~pyantz.infrastructure.config.LocalRunnerConfig`):
  worker processes on this machine.
* ``slurm_sbatch``
  (:class:`~pyantz.infrastructure.config.runners.SlurmRunnerConfig`): one
  ``sbatch`` job per job on a SLURM cluster.

The optional ``host`` decides where the submitter starts: ``local`` (the default),
``ssh`` (:class:`~pyantz.infrastructure.config.SshConfig`) or ``container``
(:class:`~pyantz.infrastructure.config.ContainerConfig`).

.. warning::

    A configuration is code: it can import and run any function. Only run
    configurations you trust, or limit the modules they may use with the
    ``PYANTZ_ALLOWED_MODULES`` environment variable (see
    :func:`~pyantz.infrastructure.config.fn_utils._check_import_allowed`).

Next steps
----------

* :doc:`job_library` lists the built-in jobs.
* :doc:`writing_jobs` shows how to write your own.
* The :doc:`API reference <pyantz>` documents every module.
