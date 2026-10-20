"""Test that submitter and host configs are discriminated by their `type_`."""

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.runners import LocalRunnerConfig, SlurmRunnerConfig
from pyantz.jobs.wrappers.submit import HostParams, SubmitParams

JOB = {"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}


def test_submit_params_pick_the_runner_by_type() -> None:
    """The `type_` of the runner decides which config class is made."""
    slurm = SubmitParams.model_validate(
        {"runner_config": {"type_": "slurm_sbatch", "working_dir": "/"}, "jobs": [JOB]}
    )
    local = SubmitParams.model_validate(
        {
            "runner_config": {"type_": "local_proc", "working_directory": "."},
            "jobs": [JOB],
        }
    )

    assert isinstance(slurm.runner_config, SlurmRunnerConfig)
    assert isinstance(local.runner_config, LocalRunnerConfig)


def test_host_params_pick_host_and_runner_by_type() -> None:
    """The host is chosen by `type_`, like the runner."""
    params = HostParams.model_validate(
        {
            "host_config": {"type_": "local"},
            "submit_config": {"type_": "local_proc", "working_directory": "."},
            "jobs": [JOB],
        }
    )

    assert params.host_config.type_ == "local"
    assert isinstance(params.submit_config, LocalRunnerConfig)


def test_initial_config_picks_the_runner_by_type() -> None:
    """The initial configuration needs no generic parameter."""
    config = InitialConfig.model_validate(
        {"jobs": [JOB], "submitter": {"type_": "slurm_sbatch", "working_dir": "/"}}
    )

    assert isinstance(config.submitter, SlurmRunnerConfig)
