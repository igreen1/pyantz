Job library
===========

The built-in jobs, by area. Each job's page lists its parameters and has an example.

Files
-----

.. autosummary::

    pyantz.jobs.files.simple.copy
    pyantz.jobs.files.simple.move
    pyantz.jobs.files.simple.delete
    pyantz.jobs.files.simple.create
    pyantz.jobs.files.simple.mkdir
    pyantz.jobs.files.moving.copy
    pyantz.jobs.files.moving.move
    pyantz.jobs.files.moving.rsync
    pyantz.jobs.files.check.file_exists
    pyantz.jobs.files.check.file_contains
    pyantz.jobs.files.edit.edit_json
    pyantz.jobs.files.edit.edit_yaml
    pyantz.jobs.files.edit.edit_external_method
    pyantz.jobs.files.reformat.csv_to_parquet
    pyantz.jobs.files.reformat.excel_to_csv

Analysis
--------

.. autosummary::

    pyantz.jobs.analysis.simple.columnar_operation
    pyantz.jobs.analysis.simple.join_parquets
    pyantz.jobs.analysis.external.save_from_external_extraction
    pyantz.jobs.analysis.external.external_simple
    pyantz.jobs.analysis.external.external_analysis

Subprocesses
------------

.. autosummary::

    pyantz.jobs.subproc.dispatch.dispatch

Branching
---------

.. autosummary::

    pyantz.jobs.branching.if_else.if_else
    pyantz.jobs.branching.if_else.conditionally_execute
    pyantz.jobs.branching.case_matrix.create_case_matrix
    pyantz.jobs.branching.case_matrix.pipeline_expansion
    pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir

Wrappers
--------

.. autosummary::

    pyantz.jobs.wrappers.local.run_pipeline
    pyantz.jobs.wrappers.loops.local_for_loop
    pyantz.jobs.wrappers.submit.submit
    pyantz.jobs.wrappers.submit.new_host
    pyantz.jobs.wrappers.variables.set_variables
    pyantz.jobs.wrappers.variables.run_jobs_in_context
    pyantz.jobs.wrappers.variables.run_jobs_with_temp_dir

Virtual jobs
------------

.. autosummary::

    pyantz.virtual.add_variables.AddVariables

Testing
-------

.. autosummary::

    pyantz.jobs.testing.nop.do_nothing
    pyantz.jobs.testing.touch_file.touch_file
