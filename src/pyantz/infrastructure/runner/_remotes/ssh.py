"""Execute a pyantz pipeline on a remote host via SSH.

:func:`run_ssh` connects to the remote machine with Paramiko, copies the
setup tarball via SFTP, extracts it, and runs ``uvx pyantz config.json``
— either synchronously or as a background process (``nohup … &``).
"""

import getpass
import logging
import os
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any, cast

import paramiko

from ._transfers import get_cmd, get_project_dir, get_setup_tar

if TYPE_CHECKING:
    from pyantz.infrastructure.config import InitialConfig, SshConfig


def _run_checked(ssh: paramiko.SSHClient, cmd: str, description: str) -> str:
    """Run a command on the remote and raise if it fails.

    Args:
        ssh: connected client
        cmd: shell command to run
        description: what the command does, used in the error message

    Returns:
        str: what the command wrote to stdout

    Raises:
        RuntimeError: if the exit status is not zero; the message has its stderr

    """
    logger = logging.getLogger(__name__)
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    exit_code = stdout.channel.recv_exit_status()
    logger.debug(
        "%s: exit code %s\n\tstdout=%s\n\tstderr=%s",
        description,
        exit_code,
        out,
        err,
    )
    if exit_code != 0:
        msg = (
            f"{description} failed on the remote (exit code {exit_code}): {err.strip()}"
        )
        raise RuntimeError(msg)
    return out


def run_ssh(config: InitialConfig[Any]) -> None:
    """Copy our files to a remote and run."""
    logger = logging.getLogger(__name__)
    if not config.host.type_ == "ssh":
        raise RuntimeError

    host_config: SshConfig = cast("SshConfig", config.host)

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()

    try:
        logger.debug("Connecting to %s, attempting ssh keys", host_config.remote_host)
        # login
        ssh.connect(
            hostname=host_config.remote_host,
            port=host_config.remote_port,
            username=host_config.remote_user,
        )
        logger.debug("Connected to %s with ssh keys", host_config.remote_host)
    except paramiko.AuthenticationException:
        logger.debug("Failed to authenticate using keys, failing back to password.")
        ssh.connect(
            hostname=host_config.remote_host,
            port=host_config.remote_port,
            username=host_config.remote_user,
            password=getpass.getpass(f"Password ({host_config.remote_user}): "),
        )
        logger.debug("Connected to %s with password", host_config.remote_host)

    sftp = ssh.open_sftp()
    sftp.mkdir(host_config.working_dir)
    logger.debug("Made working dir %s", host_config.working_dir)

    setup_tar_filename = "setup.tar.gz"
    project_dir_filename = "pyantz.tar.gz"

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_setup_tar = os.path.join(tmp_dir, "setup.tar.gz")
        remote_setup_tar_path = host_config.working_dir + "/" + setup_tar_filename
        with open(local_setup_tar, mode="wb") as fh:
            fh.write(
                get_setup_tar(
                    config,
                    host_config,
                ).getvalue()
            )
        sftp.put(local_setup_tar, remote_setup_tar_path)
        logger.debug(
            "Copied setup files to %s",
            remote_setup_tar_path,
        )

        if host_config.copy_project_dir:
            local_pyantz_file = os.path.join(tmp_dir, "project.tar.gz")
            remote_pyantz_file = host_config.working_dir + "/" + project_dir_filename
            with open(local_pyantz_file, "wb") as fh:
                fh.write(get_project_dir().getvalue())
            sftp.put(local_pyantz_file, remote_pyantz_file)
            logger.debug(
                "Copied project dir to %s",
                remote_pyantz_file,
            )
    # perform our setup by untaring
    _run_checked(
        ssh,
        f"tar -xvzf {remote_setup_tar_path} -C {host_config.working_dir}",
        "Extracting the setup files",
    )
    if host_config.copy_project_dir:
        _run_checked(
            ssh,
            f"tar -xzvf {remote_pyantz_file} -C {host_config.working_dir}",
            "Extracting the project files",
        )
    logger.debug("Starting remote command")
    # actually run our command to run pyantz!
    addl_requirements = []
    if host_config.copy_project_dir:
        addl_requirements = ["--with", f"{host_config.working_dir}/pyantz"]
    cmd = get_cmd(host_config, addl_requirements)
    if host_config.run_async:
        cmd.insert(0, "nohup")  # let our ssh client terminate
        cmd.append("&")
    cd_cmd = ["cd", host_config.working_dir]
    cmd = [*cd_cmd, "&&", *cmd]
    logger.debug("Will run the following on %s: cmd=%s", host_config.remote_host, cmd)
    # for a background run, this only checks that the command was launched
    _run_checked(ssh, " ".join(cmd), "Running pyantz")
    logger.debug("Finished submission, exiting submitter on local machine.")

    if host_config.sync_data_at_end:
        if host_config.output_dir is None:
            raise RuntimeError  # checked by validation of model, just for type checking
        # run rsync to output directory
        subprocess.run(  # noqa: S603
            [
                "/usr/bin/rsync",
                "-avz",
                f"{host_config.remote_user}@{host_config.remote_host}:{host_config.working_dir}",
                host_config.output_dir,
            ],
            check=True,
        )
