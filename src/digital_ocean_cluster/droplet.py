import os
import subprocess
import time
import warnings
from concurrent.futures import Future
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from digital_ocean_cluster.ensure_doctl import ensure_doctl
from digital_ocean_cluster.locked_print import locked_print
from digital_ocean_cluster.types import THREAD_POOL, CompletedProcess, DropletException

_TIME_DELETE_BEFORE_GONE = 10


WINDOWS_OPENSSH = "C:\\Windows\\System32\\OpenSSH\\ssh.exe"


def get_private_key() -> str:
    """Get public key."""
    home = Path.home()
    return str(home / ".ssh/id_rsa")


class Droplet:
    def __init__(self, data: Any) -> None:
        ensure_doctl()
        self.id = data["id"]
        self.name = data["name"]
        self.data = data
        assert self.tags is not None, f"No tags found for droplet: {self.name}"

    @property
    def tags(self) -> list[str]:
        if "tags" in self.data:
            return self.data["tags"]
        return []

    def public_ip(self) -> str:
        doctl = str(ensure_doctl())
        cmd_list = [
            doctl,
            "compute",
            "droplet",
            "get",
            str(self.id),
            "--format",
            "PublicIPv4",
            "--no-header",
        ]
        for _ in range(10):
            try:
                cp = subprocess.run(
                    cmd_list, capture_output=True, text=True, shell=False
                )
                if cp.returncode != 0:
                    raise DropletException(f"Error getting public IP: {cp.stderr}")
                ip = cp.stdout.strip()
                if not ip:
                    raise DropletException("No public IP found.")
                return ip
            except DropletException as e:
                locked_print(f"Error getting public IP: {e}, waiting")
                time.sleep(1)
        raise DropletException(f"Failed to get public IP for droplet: {self.name}")

    def ssh_exec(self, command: str) -> CompletedProcess:
        key_path = get_private_key()
        public_ip = self.public_ip()

        with TemporaryDirectory() as tmpdir:
            known_hosts = Path(tmpdir) / "known_hosts"
            known_hosts.touch()  # Create empty known_hosts file

            cmd_list = [
                WINDOWS_OPENSSH,
                "-n",  # prevents reading from stdin
                "-o",
                "BatchMode=yes",
                "-o",
                f"UserKnownHostsFile={known_hosts}",
                "-o",
                "StrictHostKeyChecking=no",
                "-i",
                key_path,
                f"root@{public_ip}",
                command,
            ]
            cmd_str = subprocess.list2cmdline(cmd_list)
            locked_print(f"Executing: {cmd_str}")
            proc: subprocess.Popen = subprocess.Popen(
                cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(input="\n")
            cp: subprocess.CompletedProcess = subprocess.CompletedProcess(
                cmd_list, proc.returncode, stdout.decode(), stderr.decode()
            )
            return CompletedProcess(cmd_list, cp)

    def copy_to(
        self, src: Path, dest: Path, chmod: str | None = None
    ) -> CompletedProcess:
        assert src.exists(), f"Source file does not exist: {src}"
        key_path = get_private_key()

        with TemporaryDirectory() as tmpdir:
            known_hosts = Path(tmpdir) / "known_hosts"
            known_hosts.touch()  # Create empty known_hosts file

            cmd_list = [
                "scp",
                "-o",
                f"UserKnownHostsFile={known_hosts}",
                "-o",
                "StrictHostKeyChecking=no",
                "-i",
                key_path,
            ]

            # Add recursive flag if source is a directory
            if src.is_dir():
                cmd_list.append("-r")

            cmd_list.extend(
                [
                    str(src),
                    f"root@{self.public_ip()}:{dest.as_posix()}",
                ]
            )
            cmd_str = subprocess.list2cmdline(cmd_list)

            # make sure the destination directory exists
            self.ssh_exec(f"mkdir -p {dest.parent.as_posix()}")
            locked_print(f"Executing: {cmd_str}")
            cp = subprocess.run(cmd_list, capture_output=True, text=True)
            if cp.returncode != 0:
                warnings.warn(f"Error copying file: {cp.stderr}")
            if chmod:
                chmod_path = dest.as_posix()
                if src.is_dir():
                    # Apply chmod recursively for directories
                    self.ssh_exec(f"chmod -R {chmod} {chmod_path}")
                else:
                    self.ssh_exec(f"chmod {chmod} {chmod_path}")
            out = CompletedProcess(cmd_list, cp)
            return out

    def copy_from(self, remote_path: Path, local_path: Path) -> CompletedProcess:
        key_path = get_private_key()

        with TemporaryDirectory() as tmpdir:
            known_hosts = Path(tmpdir) / "known_hosts"
            known_hosts.touch()  # Create empty known_hosts file

            cmd_list = [
                "scp",
                "-o",
                f"UserKnownHostsFile={known_hosts}",
                "-o",
                "StrictHostKeyChecking=no",
                "-i",
                key_path,
            ]

            # Check if remote path is a directory
            check_dir = self.ssh_exec(
                f"test -d {remote_path} && echo 'DIR' || echo 'FILE'"
            )
            is_dir = "DIR" in check_dir.stdout

            # Add recursive flag if source is a directory
            if is_dir:
                cmd_list.append("-r")

            # Make sure the local directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            cmd_list.extend(
                [
                    f"root@{self.public_ip()}:{remote_path}",
                    str(local_path),
                ]
            )

            cmd_str = subprocess.list2cmdline(cmd_list)
            locked_print(f"Executing: {cmd_str}")
            cp = subprocess.run(cmd_list, capture_output=True, text=True)
            if cp.returncode != 0:
                warnings.warn(f"Error copying file: {cp.stderr}")
            return CompletedProcess(cmd_list, cp)

    def copy_text_to(
        self, text: str, remote_path: Path, chmod: str | None = None
    ) -> CompletedProcess:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir) / "tmp.txt"
            with open(tmp, "w", newline="\n") as f:
                f.write(text)
            out = self.copy_to(tmp, remote_path, chmod)
            return out

    def copy_text_from(self, remote_path: Path) -> CompletedProcess:
        cmd = "cat " + remote_path.as_posix()
        results = self.ssh_exec(cmd)
        return results

    def delete(self) -> DropletException | None:
        try:
            locked_print(f"Deleting droplet: {self.name}")
            # get_digital_ocean().compute.droplet.delete(str(self.id))
            # cmd_str = f"doctl compute droplet delete {self.id} --force --output json --interactive=false"
            doctl = str(ensure_doctl())
            cmd_list = [
                doctl,
                "compute",
                "droplet",
                "delete",
                str(self.id),
                "--force",
                "--output",
                "json",
                "--interactive=false",
            ]
            cp = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
            if cp.returncode != 0:
                warnings.warn(f"Error deleting droplet: {cp.stderr}")
                # locked_print path to doctl
                env_paths = Path(os.environ["PATH"]).parts
                warnings.warn(f"PATH: {env_paths}")
                return None
        except DropletException as e:
            warnings.warn(f"Error deleting droplet: {e}")
            return e
        time.sleep(_TIME_DELETE_BEFORE_GONE)
        if cp.returncode != 0:
            return DropletException(f"Error deleting droplet {self.name}: {cp.stderr}")
        return None

    def async_delete(self) -> Future[DropletException | None]:

        return THREAD_POOL.submit(self.delete)

    def is_valid(self) -> bool:
        from digital_ocean_cluster.droplet_manager import DropletManager

        tmp_list: list[Droplet] = DropletManager.list_droplets()
        for droplet in tmp_list:
            if droplet.id == self.id:
                return True
        return False

    def __str__(self) -> str:
        return f"Droplet: {self.name} {self.id}"
