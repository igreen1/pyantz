"""Execute a pyantz pipeline on a remote host via SSH.

:func:`run_ssh` connects to the remote machine with Paramiko, copies the
setup tarball via SFTP, extracts it, and runs ``uvx pyantz config.json``
— either synchronously or as a background process (``nohup … &``).
"""

import getpass
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import paramiko

from ._transfers import get_cmd, get_environment, get_project_dir, get_setup_tar

if TYPE_CHECKING:
    from pyantz.infrastructure.config import InitialConfig, SshConfig

# where the output of a background run is written, in the remote working directory
REMOTE_LOG_FILE = "pyantz.log"


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


def _make_remote_dir(ssh: paramiko.SSHClient, path: str) -> None:
    """Create the directory (and any missing parents) on the remote.

    Unlike ``sftp.mkdir`` this doesn't fail when the directory already exists
    (for example when re-running) or when parent directories are missing.
    """
    _, stdout, stderr = ssh.exec_command(f"mkdir -p {shlex.quote(path)}")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        msg = (
            f"Could not create directory {path!r} on the remote "
            f"(exit code {exit_code}): {stderr.read().decode().strip()}"
        )
        raise RuntimeError(msg)


def _build_remote_command(
    host_config: SshConfig,
    working_dir: str,
    addl_requirements: list[str],
) -> str:
    """Build the shell command which runs pyantz in the remote working directory."""
    cmd = get_cmd(host_config, working_dir, addl_requirements)
    environment = get_environment(host_config)
    if environment:
        cmd = [
            "env",
            *(f"{name}={value}" for name, value in environment.items()),
            *cmd,
        ]
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
        # the model validates this, the check is for the type checker
        msg = "output_dir must be set when sync_data_at_end is true"
        raise RuntimeError(msg)
    rsync = shutil.which("rsync")
    if rsync is None:
        msg = (
            "rsync was not found on this machine, which is needed to copy the "
            "results back (sync_data_at_end); install it or set "
            "sync_data_at_end to false"
        )
        raise RuntimeError(msg)
    # run rsync to output directory
    subprocess.run(  # noqa: S603
        [
            rsync,
            "-avz",
            "-e",
            f"ssh -p {host_config.remote_port}",
            f"{host_config.remote_user}@{host_config.remote_host}:{working_dir}",
            host_config.output_dir,
        ],
        check=True,
    )


def _prepare_working_dir(
    ssh: paramiko.SSHClient,
    host_config: SshConfig,
) -> str:
    """Create (or pick) the directory on the remote that the pipeline runs in."""
    logger = logging.getLogger(__name__)
    if host_config.working_dir is not None:
        _make_remote_dir(ssh, host_config.working_dir)
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
    except paramiko.AuthenticationException as exc:
        logger.debug("Failed to authenticate using keys, failing back to password.")
        if not sys.stdin.isatty():
            msg = (
                f"Could not authenticate to {host_config.remote_host} as "
                f"{host_config.remote_user} with ssh keys, and there is no terminal "
                "to ask for a password. Set up key based login (or an ssh agent)."
            )
            raise RuntimeError(msg) from exc
        ssh.connect(
            **connect_args,
            password=getpass.getpass(f"Password ({host_config.remote_user}): "),
        )
        logger.debug("Connected to %s with password", host_config.remote_host)


def run_ssh(config: InitialConfig[Any]) -> None:
    """Copy our files to a remote and run."""
    if config.host.type_ != "ssh":
        msg = f"run_ssh needs an 'ssh' host, got {config.host.type_!r}"
        raise RuntimeError(msg)

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
        working_dir = _prepare_working_dir(ssh, host_config)

        setup_tar_filename = "setup.tar.gz"
        project_dir_filename = "pyantz.tar.gz"

        with tempfile.TemporaryDirectory() as tmp_dir:
            local_setup_tar = Path(tmp_dir) / "setup.tar.gz"
            remote_setup_tar_path = working_dir + "/" + setup_tar_filename
            with local_setup_tar.open(mode="wb") as fh:
                fh.write(
                    get_setup_tar(
                        config,
                        host_config,
                    ).getvalue()
                )
            sftp.put(os.fspath(local_setup_tar), remote_setup_tar_path)
            logger.debug(
                "Copied setup files to %s",
                remote_setup_tar_path,
            )

            if host_config.copy_project_dir:
                local_pyantz_file = Path(tmp_dir) / "project.tar.gz"
                remote_pyantz_file = working_dir + "/" + project_dir_filename
                with local_pyantz_file.open("wb") as fh:
                    fh.write(get_project_dir().getvalue())
                sftp.put(os.fspath(local_pyantz_file), remote_pyantz_file)
                logger.debug(
                    "Copied project dir to %s",
                    remote_pyantz_file,
                )
    finally:
        sftp.close()

    # perform our setup by untaring
    _run_checked(
        ssh,
        f"tar -xvzf {shlex.quote(remote_setup_tar_path)} -C {shlex.quote(working_dir)}",
        "Extracting the setup files",
    )
    if host_config.copy_project_dir:
        _run_checked(
            ssh,
            f"tar -xzvf {shlex.quote(remote_pyantz_file)} "
            f"-C {shlex.quote(working_dir)}",
            "Extracting the project files",
        )
    logger.debug("Starting remote command")
    # actually run our command to run pyantz!
    addl_requirements = []
    if host_config.copy_project_dir:
        addl_requirements = ["--with", f"{working_dir}/pyantz"]
    remote_cmd = _build_remote_command(host_config, working_dir, addl_requirements)
    # for a background run, this only checks that the command was launched
    _run_checked(ssh, remote_cmd, "Running pyantz")
    logger.debug("Finished submission, exiting submitter on local machine.")

    if host_config.sync_data_at_end:
        _sync_output(host_config, working_dir)
