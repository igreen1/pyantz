Writing jobs
============

A job is a Python function which takes its parameters and a *submit function*,
and returns ``True`` on success. Configurations refer to it by its import path.

A job with typed parameters
---------------------------

Describe the parameters with a pydantic model and register the function with
:func:`~pyantz.infrastructure.config.add_parameters`. The parameters are validated
(after variables are filled in) each time the job runs, and the web UI uses the
model's JSON schema to build its forms. A job which never submits other jobs can
take only its parameters by adding :func:`~pyantz.infrastructure.config.no_submit_fn`
below.

.. testcode:: writing-jobs-typed

    from pydantic import BaseModel

    from pyantz.infrastructure.config import add_parameters, no_submit_fn


    class GreetParams(BaseModel):
        """Parameters of greet."""

        name: str
        """Who to greet."""

        times: int = 1
        """How many times to greet them."""


    @add_parameters(GreetParams)
    @no_submit_fn
    def greet(params: GreetParams) -> bool:
        """Greet someone.

        Args:
            params: the job's parameters, validated as GreetParams.

        Parameters:
            name (str): who to greet.
            times (int): how many times to greet them. Defaults to 1.

        Returns:
            bool: always True.

        Raises:
            None.

        """
        for _ in range(params.times):
            print(f"hello {params.name}")
        return True


    # registered jobs are called with their parameters and a submit function
    greet({"name": "ant", "times": 2}, lambda job: None)

.. testoutput:: writing-jobs-typed

    hello ant
    hello ant

A job reports failure by returning ``False`` or raising an exception. Returning
``None`` counts as success, with a warning.

Submitting jobs from a job
--------------------------

The submit function adds jobs to the running pipeline. The submitted jobs inherit
the variables of the job which submitted them, and the jobs waiting for that job
wait for them too. :func:`~pyantz.jobs.branching.if_else.if_else` and
:func:`~pyantz.jobs.branching.case_matrix.pipeline_expansion` work this way.

.. testcode:: writing-jobs-submit

    from pydantic import BaseModel

    from pyantz.infrastructure.config import JobConfig, add_parameters


    class FanOutParams(BaseModel):
        """Parameters of fan_out."""

        count: int
        """How many jobs to submit."""


    @add_parameters(FanOutParams)
    def fan_out(params: FanOutParams, submit_fn) -> bool:
        """Submit one job per index."""
        for index in range(params.count):
            submit_fn(
                JobConfig(
                    name=f"job_{index}",
                    function="pyantz.jobs.testing.nop.do_nothing",
                    parameters={},
                )
            )
        return True


    submitted = []
    fan_out({"count": 3}, submitted.append)
    print([job.name for job in submitted])

.. testoutput:: writing-jobs-submit

    ['job_0', 'job_1', 'job_2']

Documenting a job
-----------------

Docstrings follow the Google style, checked by ruff and rendered by Sphinx's
napoleon extension. Every function has ``Args``, ``Returns`` and ``Raises``
sections. A job also lists the fields of its parameters model in a ``Parameters``
section (shown as "Job parameters" in these docs), and has an ``Example`` with a
runnable ``testcode`` block, which ``make test`` runs as a doctest.

The first paragraph of a job's docstring is its description in the web UI.

Built-in jobs
-------------

A job in the :mod:`pyantz.jobs` package must be imported by
``pyantz/jobs/__init__.py`` (through its sub-package), since the registry of jobs
only knows the modules which have been imported; a test checks this.

Virtual jobs
------------

A virtual job exists only while a configuration is compiled: its parameters model,
marked with :func:`~pyantz.infrastructure.config.mark_virtual`, has a
``compile_virtual`` method which turns the jobs depending on it into concrete jobs.
See :class:`~pyantz.virtual.add_variables.AddVariables` and
:mod:`pyantz.infrastructure.virtual`.
