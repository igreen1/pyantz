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


def _host_key_policy(name: str) -> paramiko.MissingHostKeyPolicy:
    """Get the paramiko policy for hosts which are not in the known hosts."""
    policies: dict[str, type[paramiko.MissingHostKeyPolicy]] = {
        "reject": paramiko.RejectPolicy,
        "warn": paramiko.WarningPolicy,
        "auto_add": paramiko.AutoAddPolicy,
    }
    return policies[name]()


def _connect(ssh: paramiko.SSHClient, host_config: SshConfig) -> None:
    """Connect, trying keys first and falling back to a password."""
    logger = logging.getLogger(__name__)
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(_host_key_policy(host_config.known_hosts_policy))
    connect_args: dict[str, Any] = {
        "hostname": host_config.remote_host,
        "port": host_config.remote_port,
        "username": host_config.remote_user,
        "timeout": host_config.connect_timeout,
        "key_filename": host_config.key_filename,
    }
    try:
        logger.debug("Connecting to %s, attempting ssh keys", host_config.remote_host)
        ssh.connect(**connect_args)
        logger.debug("Connected to %s with ssh keys", host_config.remote_host)
    except paramiko.AuthenticationException:
        logger.debug("Failed to authenticate using keys, failing back to password.")
        ssh.connect(
            **connect_args,
            password=getpass.getpass(f"Password ({host_config.remote_user}): "),
        )
        logger.debug("Connected to %s with password", host_config.remote_host)


def run_ssh(config: InitialConfig[Any]) -> None:
    """Copy our files to a remote and run."""
    if not config.host.type_ == "ssh":
        raise RuntimeError

    host_config: SshConfig = cast("SshConfig", config.host)

    ssh = paramiko.SSHClient()
    try:
        _connect(ssh, host_config)
        _run_on_connection(ssh, config, host_config)
    finally:
        # also on failures, so sockets aren't leaked
        ssh.close()


def _run_on_connection(
    ssh: paramiko.SSHClient,
    config: InitialConfig[Any],
    host_config: SshConfig,
) -> None:
    """Copy our files to the connected remote and run."""
    logger = logging.getLogger(__name__)

    sftp = ssh.open_sftp()
    try:
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
                remote_pyantz_file = (
                    host_config.working_dir + "/" + project_dir_filename
                )
                with open(local_pyantz_file, "wb") as fh:
                    fh.write(get_project_dir().getvalue())
                sftp.put(local_pyantz_file, remote_pyantz_file)
                logger.debug(
                    "Copied project dir to %s",
                    remote_pyantz_file,
                )
    finally:
        sftp.close()

    # perform our setup by untaring
    _stdin, stdout, stderr = ssh.exec_command(
        f"tar -xvzf {remote_setup_tar_path} -C {host_config.working_dir}"
    )
    logger.debug(
        "Untar setup files,\n\tstdout=%s\n\tstderr=%s",
        stdout.read().decode(),
        stderr.read().decode(),
    )
    if host_config.copy_project_dir:
        _, stdout, stderr = ssh.exec_command(
            f"tar -xzvf {remote_pyantz_file} -C {host_config.working_dir}"
        )
        logger.debug(
            "Untar project files,\n\tstdout=%s\n\tstderr=%s",
            stdout.read().decode(),
            stderr.read().decode(),
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
    _, stdout, stderr = ssh.exec_command(" ".join(cmd))
    logger.debug(
        "Output from command:\n\tstdout=%s\n\tstderr=%s",
        stdout.read().decode(),
        stderr.read().decode(),
    )
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
