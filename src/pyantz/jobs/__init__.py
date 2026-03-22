"""PyAntz includes many useful jobs to help run pipelines and call external functions.

A user should first create a large configuration file and then pass this to the
PyAntz entry point runner. Below is an example using a "nop", which is a job
that literally does nothing.

:Example:

    .. testsetup::

        import os
        os.mkdir("./working_dir")

    .. testcode::

        from pyantz import start

        config = {
            "jobs": [
                {
                    "function": "pyantz.jobs.testing.nop.do_nothing",
                    "parameters": {
                        "hello": "there", # fake parameters
                        "general": "kenobi", # these are deleted in "nop"
                    },
                }
            ],
            "submitter": {
                "type_": "local_proc",
                "working_directory": "./working_dir", # set to some temp dir
            },
        }
        start(config)

    Output:

        `did nothing :)`

    .. testcleanup::

        import shutil
        import os
        if os.path.exists("./working_dir"):
            shutil.rmtree("./working_dir")


"""

from . import analysis, branching, files, subproc, testing, wrappers

__all__ = [
    "analysis",
    "branching",
    "files",
    "subproc",
    "testing",
    "wrappers",
]
