"""Execute a pyantz pipeline on a remote host via SSH.

:func:`run_ssh` connects to the remote machine with Paramiko, copies the
setup tarball via SFTP, extracts it, and runs ``uvx pyantz config.json``
— either synchronously or as a background process (``nohup … &``).
"""

import getpass
import logging
import os
import shlex
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any, cast

import paramiko

from ._transfers import get_cmd, get_project_dir, get_setup_tar

if TYPE_CHECKING:
    from pyantz.infrastructure.config import InitialConfig, SshConfig

# where the output of a background run is written, in the remote working directory
REMOTE_LOG_FILE = "pyantz.log"


def _build_remote_command(
    host_config: SshConfig,
    working_dir: str,
    addl_requirements: list[str],
) -> str:
    """Build the shell command which runs pyantz in the remote working directory."""
    cmd = get_cmd(host_config, working_dir, addl_requirements)
    background: list[str] = []
    if host_config.run_async:
        cmd.insert(0, "nohup")  # let our ssh client terminate
        # without redirecting its output, the ssh channel stays open until the
        # background process exits, which makes reading the output block
        background = [">", REMOTE_LOG_FILE, "2>&1", "<", "/dev/null", "&"]
        logging.getLogger(__name__).info(
            "Running in the background; output goes to %s/%s on %s",
            working_dir,
            REMOTE_LOG_FILE,
            host_config.remote_host,
        )
    # every value is quoted, only the operators written here are shell syntax
    remote_cmd = " ".join(
        [
            "cd",
            shlex.quote(working_dir),
            "&&",
            *map(shlex.quote, cmd),
            *background,
        ],
    )
    logging.getLogger(__name__).debug(
        "Will run the following on %s: cmd=%s",
        host_config.remote_host,
        remote_cmd,
    )
    return remote_cmd


def _sync_output(host_config: SshConfig, working_dir: str) -> None:
    """Copy the remote working directory to the local output directory."""
    if host_config.output_dir is None:
        raise RuntimeError  # checked by validation of model, just for type checking
    # run rsync to output directory
    subprocess.run(  # noqa: S603
        [
            "/usr/bin/rsync",
            "-avz",
            f"{host_config.remote_user}@{host_config.remote_host}:{working_dir}",
            host_config.output_dir,
        ],
        check=True,
    )


def _prepare_working_dir(
    ssh: paramiko.SSHClient,
    sftp: paramiko.SFTPClient,
    host_config: SshConfig,
) -> str:
    """Create (or pick) the directory on the remote that the pipeline runs in."""
    logger = logging.getLogger(__name__)
    if host_config.working_dir is not None:
        sftp.mkdir(host_config.working_dir)
        logger.debug("Made working dir %s", host_config.working_dir)
        return host_config.working_dir

    # nothing was chosen, so ask the remote for a directory we can write to
    _, mktemp_out, _ = ssh.exec_command("mktemp -d")
    working_dir = mktemp_out.read().decode().strip()
    if not working_dir:
        msg = f"Could not create a temporary directory on {host_config.remote_host}"
        raise RuntimeError(msg)
    logger.debug("Created temporary working dir %s", working_dir)
    return working_dir


def _connect(host_config: SshConfig) -> paramiko.SSHClient:
    """Connect to the remote, trying keys and falling back to a password."""
    logger = logging.getLogger(__name__)
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
    return ssh


def run_ssh(config: InitialConfig[Any]) -> None:
    """Copy our files to a remote and run."""
    logger = logging.getLogger(__name__)
    if not config.host.type_ == "ssh":
        raise RuntimeError

    host_config: SshConfig = cast("SshConfig", config.host)

    ssh = _connect(host_config)

    sftp = ssh.open_sftp()
    working_dir = _prepare_working_dir(ssh, sftp, host_config)

    setup_tar_filename = "setup.tar.gz"
    project_dir_filename = "pyantz.tar.gz"

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_setup_tar = os.path.join(tmp_dir, "setup.tar.gz")
        remote_setup_tar_path = working_dir + "/" + setup_tar_filename
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
            remote_pyantz_file = working_dir + "/" + project_dir_filename
            with open(local_pyantz_file, "wb") as fh:
                fh.write(get_project_dir().getvalue())
            sftp.put(local_pyantz_file, remote_pyantz_file)
            logger.debug(
                "Copied project dir to %s",
                remote_pyantz_file,
            )
    # perform our setup by untaring
    _stdin, stdout, stderr = ssh.exec_command(
        f"tar -xvzf {shlex.quote(remote_setup_tar_path)} -C {shlex.quote(working_dir)}"
    )
    logger.debug(
        "Untar setup files,\n\tstdout=%s\n\tstderr=%s",
        stdout.read().decode(),
        stderr.read().decode(),
    )
    if host_config.copy_project_dir:
        _, stdout, stderr = ssh.exec_command(
            f"tar -xzvf {shlex.quote(remote_pyantz_file)} -C {shlex.quote(working_dir)}"
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
        addl_requirements = ["--with", f"{working_dir}/pyantz"]
    remote_cmd = _build_remote_command(host_config, working_dir, addl_requirements)
    _, stdout, stderr = ssh.exec_command(remote_cmd)
    logger.debug(
        "Output from command:\n\tstdout=%s\n\tstderr=%s",
        stdout.read().decode(),
        stderr.read().decode(),
    )
    logger.debug("Finished submission, exiting submitter on local machine.")

    if host_config.sync_data_at_end:
        _sync_output(host_config, working_dir)
