"""Run on a remote machine."""

import getpass
import tempfile
from typing import TYPE_CHECKING, Any

import paramiko

from ._transfers import get_cmd, get_project_dir, get_setup_tar

if TYPE_CHECKING:
    from pyantz.infrastructure.config import InitialConfig, SshConfig


def run_ssh(config: InitialConfig[Any]) -> None:
    """Copy our files to a remote and run."""
    if not config.host.type_ == "ssh":
        raise RuntimeError

    host_config: SshConfig = config.host

    ssh = paramiko.SSHClient()

    # login
    username: str = getpass.getuser()
    ssh.connect(
        hostname=host_config.remote_host,
        port=host_config.remote_port,
        username=username,
        password=getpass.getpass(f"Password ({username}): "),
    )

    sftp = ssh.open_sftp()

    # copy our configuration files over
    with tempfile.NamedTemporaryFile(mode="wb+") as fh:
        fh.write(get_setup_tar(host_config).getvalue())
        sftp.put(fh.name, host_config.working_dir + "/setup.tar")

    if host_config.copy_project_dir:
        with tempfile.NamedTemporaryFile(mode="wb+") as fh:
            fh.write(get_project_dir().getvalue())
            sftp.put(fh.name, host_config.working_dir + "/pyantz")

    # perform our setup by untaring
    ssh.exec_command(f"tar -xvf {host_config.working_dir}/setup.tar")

    # actually run our command to run pyantz!
    cmd = get_cmd(host_config)
    cmd.insert(0, "nohup")  # let our ssh client terminate
    cmd.append("&")
    ssh.exec_command(" ".join(cmd))
