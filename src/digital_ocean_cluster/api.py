import json
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
from digital_ocean_cluster.machines import ImageType, MachineSize, Region
from digital_ocean_cluster.types import (
    THREAD_POOL,
    Authentication,
    DropletException,
    SSHKey,
)

_TIME_DELETE_BEFORE_GONE = 10
SLEEP_TIME_BEFORE_SSH = 10


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
        try:
            addr_infos = self.data["networks"]["v4"]
            for addr_info in addr_infos:
                if addr_info["type"] == "public":
                    return addr_info["ip_address"]
        except KeyError as e:
            json_str = json.dumps(self.data, indent=2)
            warnings.warn(f"No public IP found for droplet: \n{json_str}")
            raise DropletException("No public IP found.") from e
        raise DropletException("No public IP found.")

    def ssh_exec(self, command: str) -> subprocess.CompletedProcess:
        key_path = get_private_key()
        public_ip = self.public_ip()
        cmd_list = [
            WINDOWS_OPENSSH,
            # "-t", # force pseudo-terminal allocation
            "-n",  # prevents reading from stdin
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            key_path,
            f"root@{public_ip}",
            command,
        ]
        cmd_str = subprocess.list2cmdline(cmd_list)
        locked_print(f"Executing: {cmd_str}")
        # cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        # DO NOT MOVE THESE TO USE TEXT - THE PROGRAM WILL CRASH IN WINDOWS
        proc: subprocess.Popen = subprocess.Popen(
            cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(input="\n")
        cp: subprocess.CompletedProcess = subprocess.CompletedProcess(
            cmd_list, proc.returncode, stdout.decode(), stderr.decode()
        )
        return cp

    def copy_to(
        self, src: Path, dest: Path, chmod: str | None = None
    ) -> subprocess.CompletedProcess:
        assert src.exists(), f"Source file does not exist: {src}"
        key_path = get_private_key()

        cmd_list = [
            "scp",
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
        return cp

    def copy_from(
        self, remote_path: Path, local_path: Path
    ) -> subprocess.CompletedProcess:
        key_path = get_private_key()

        cmd_list = [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            key_path,
        ]

        # Check if remote path is a directory
        check_dir = self.ssh_exec(f"test -d {remote_path} && echo 'DIR' || echo 'FILE'")
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
        return cp

    def copy_text_to(
        self, text: str, remote_path: Path, chmod: str | None = None
    ) -> subprocess.CompletedProcess:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir) / "tmp.txt"
            with open(tmp, "w", newline="\n") as f:
                f.write(text)
            out = self.copy_to(tmp, remote_path, chmod)
            return out

    def copy_text_from(self, remote_path: Path) -> subprocess.CompletedProcess:
        cmd = "cat " + remote_path.as_posix()
        results = self.ssh_exec(cmd)
        return results

    def delete(self) -> DropletException | None:
        try:
            locked_print(f"Deleting droplet: {self.name}")
            # get_digital_ocean().compute.droplet.delete(str(self.id))
            cmd_str = f"doctl compute droplet delete {self.id} --force --output json --interactive=false"
            cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
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
        tmp_list: list[Droplet] = DropletManager.list_droplets()
        for droplet in tmp_list:
            if droplet.id == self.id:
                return True
        return False

    def __str__(self) -> str:
        return f"Droplet: {self.name} {self.id}"


class DropletManager:

    @staticmethod
    def is_authenticated() -> Authentication | None:
        ensure_doctl()
        cmd_str = "doctl account get --output=json --interactive=false"
        cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp.returncode != 0:
            warnings.warn(f"Error checking authentication: {cp.stderr}")
            return None
        out = json.loads(cp.stdout)
        return Authentication(**out)

    @staticmethod
    def list_machines() -> list[str]:
        ensure_doctl()
        cmd_str = (
            "doctl compute image list-distribution --output json --interactive=false"
        )
        cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp.returncode != 0:
            raise DropletException(f"Error listing machines: {cp.stderr}")
        data = json.loads(cp.stdout)
        return [d["slug"] for d in data]

    @staticmethod
    def list_droplets() -> list[Droplet]:
        ensure_doctl()
        cmd_str = "doctl compute droplet list --output json --interactive=false"
        cp_most = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp_most.returncode != 0:
            raise DropletException(f"Error listing droplets: {cp_most.stderr}")
        data_main = json.loads(cp_most.stdout)
        out = [Droplet(data) for data in data_main]
        return out

    @staticmethod
    def list_ssh_keys() -> list[SSHKey]:
        ensure_doctl()
        cmd_str = "doctl compute ssh-key list --interactive=false --output json"
        cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp.returncode != 0:
            raise DropletException(f"Error listing SSH keys: {cp.stderr}")
        # return json.loads(cp.stdout)
        tmp_list = json.loads(cp.stdout)
        out = [SSHKey(**data) for data in tmp_list]
        return out

    @staticmethod
    def create_droplet(
        name: str,
        ssh_key: SSHKey | None = None,
        tags: list[str] | None = None,
        size: MachineSize = MachineSize.S_2VCPU_2GB,
        image: ImageType = ImageType.UBUNTU_24_10_X64,
        region=Region.NYC_1,
        check=True,
    ) -> Droplet | DropletException:
        ensure_doctl()
        if tags:
            for tag in tags:
                if " " in tag:
                    return DropletException(f"Tag cannot contain spaces: {tag}")
        if check:
            if DropletManager.find_droplets(name):
                return DropletException(f"Droplet already exists: {name}")
        if ssh_key is None:
            keys = DropletManager.list_ssh_keys()
            if not keys:
                return DropletException("No SSH keys found.")
            ssh_key = keys[0]
        if not ssh_key:
            return DropletException("No SSH key found.")
        args: list[str] = [
            name,
            "--image",
            image.value,
            "--size",
            size.value,
            "--region",
            region.value,
            "--wait",
        ]
        if tags is not None:
            tag_names_joined = ",".join(tags)
            args += [f"--tag-names={tag_names_joined}"]
            # args += ["--tag-names", ",".join(tags)]
        args += ["--ssh-keys", ssh_key.fingerprint]
        cmd_list = ["doctl", "compute", "droplet", "create"] + args
        cmd_str = subprocess.list2cmdline(cmd_list)
        locked_print(f"Running: {cmd_str}")
        cp = subprocess.run(
            cmd_str,
            capture_output=True,
            text=True,
            shell=True,
        )
        if cp.returncode != 0:
            msg = f"Error creating droplet:\nReturn Value: {cp.returncode}\n\nstderr:\n{cp.stderr}\n\nstdout:\n{cp.stdout}"
            return DropletException(msg)
        locked_print("Created droplet:", name)
        time.sleep(SLEEP_TIME_BEFORE_SSH)
        timeout = time.time() + 20
        droplet: Droplet
        while time.time() < timeout:
            droplets = DropletManager.find_droplets(name=name, tags=tags)
            if droplets:
                droplet = droplets[0]
                break
            time.sleep(1)
        else:
            all_droplets = DropletManager.list_droplets()
            locked_print(
                f"Error creating droplet: {name}, available droplets: {all_droplets}"
            )
            return DropletException(
                f"Error creating droplet: {name}, available droplets: {all_droplets}"
            )
        stdout_cloudinit = droplet.ssh_exec("sudo cloud-init status --wait")
        timeout = time.time() + 20
        stdout_pwd = ""
        while time.time() < timeout:
            stdout_pwd = droplet.ssh_exec("pwd").stdout
            if "/root" in stdout_pwd:
                return droplet
            time.sleep(1)
        else:
            return DropletException(
                f"Cloud Init failed to complete: {stdout_cloudinit}, pwd: {stdout_pwd}"
            )

    @staticmethod
    def find_droplets(
        name: str | None = None, tags: list[str] | None = None
    ) -> list[Droplet]:
        ensure_doctl()
        if name is not None:
            name = name.replace("_", "-")
        droplets = DropletManager.list_droplets()
        if name is not None:
            droplets = [d for d in droplets if d.name == name]
        if tags:
            droplets = [d for d in droplets if all(tag in d.tags for tag in tags)]
        return droplets
