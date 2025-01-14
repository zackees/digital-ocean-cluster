import json
import subprocess
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TIME_DELETE_BEFORE_GONE = 10
SLEEP_TIME_BEFORE_SSH = 10


@dataclass
class Authentication:
    droplet_limit: int
    floating_ip_limit: int
    reserved_ip_limit: int
    volume_limit: int
    email: str
    name: str
    uuid: str
    email_verified: bool
    status: str
    team: dict[str, str]


@dataclass
class SSHKey:
    id: int
    name: str
    fingerprint: str
    public_key: str

    def __str__(self) -> str:
        return f"SSHKey: name={self.name},id={self.id},fingerprint={self.fingerprint}"


MACHINE_SIZES = [
    "s-1vcpu-512mb-10gb",
    "s-1vcpu-1gb",
    "s-1vcpu-1gb-amd",
    "s-1vcpu-1gb-intel",
    "s-1vcpu-1gb-35gb-intel",
    "s-1vcpu-2gb",
    "s-1vcpu-2gb-amd",
    "s-1vcpu-2gb-intel",
    "s-1vcpu-2gb-70gb-intel",
    "s-2vcpu-2gb",
    "s-2vcpu-2gb-amd",
    "s-2vcpu-2gb-intel",
    "s-2vcpu-2gb-90gb-intel",
    "s-2vcpu-4gb",
    "s-2vcpu-4gb-amd",
    "s-2vcpu-4gb-intel",
    "s-2vcpu-4gb-120gb-intel",
    "s-2vcpu-8gb-amd",
    "c-2",
    "c2-2vcpu-4gb",
    "s-2vcpu-8gb-160gb-intel",
    "s-4vcpu-8gb",
    "s-4vcpu-8gb-amd",
    "s-4vcpu-8gb-intel",
    "g-2vcpu-8gb",
    "s-4vcpu-8gb-240gb-intel",
    "gd-2vcpu-8gb",
    "g-2vcpu-8gb-intel",
    "gd-2vcpu-8gb-intel",
    "s-4vcpu-16gb-amd",
    "m-2vcpu-16gb",
    "c-4",
    "c2-4vcpu-8gb",
    "s-4vcpu-16gb-320gb-intel",
    "s-8vcpu-16gb",
    "m-2vcpu-16gb-intel",
    "m3-2vcpu-16gb",
    "c-4-intel",
    "m3-2vcpu-16gb-intel",
    "s-8vcpu-16gb-amd",
    "s-8vcpu-16gb-intel",
    "c2-4vcpu-8gb-intel",
    "g-4vcpu-16gb",
    "s-8vcpu-16gb-480gb-intel",
    "so-2vcpu-16gb-intel",
    "so-2vcpu-16gb",
    "m6-2vcpu-16gb",
    "gd-4vcpu-16gb",
    "so1_5-2vcpu-16gb-intel",
    "g-4vcpu-16gb-intel",
    "gd-4vcpu-16gb-intel",
    "so1_5-2vcpu-16gb",
    "s-8vcpu-32gb-amd",
    "m-4vcpu-32gb",
    "c-8",
    "c2-8vcpu-16gb",
    "s-8vcpu-32gb-640gb-intel",
    "m-4vcpu-32gb-intel",
    "m3-4vcpu-32gb",
]


WINDOWS_OPENSSH = "C:\\Windows\\System32\\OpenSSH\\ssh.exe"


def get_private_key() -> str:
    """Get public key."""
    home = Path.home()
    return str(home / ".ssh/id_rsa")


class Droplet:
    def __init__(self, data: Any) -> None:
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
            raise Exception("No public IP found.") from e
        raise Exception("No public IP found.")

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
        print(f"Executing: {cmd_str}")
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

    def copy_to_remote(
        self, src: Path, dest: Path, chmod: str | None = None
    ) -> subprocess.CompletedProcess:
        assert src.exists(), f"Source file does not exist: {src}"
        key_path = get_private_key()
        # rsync -avz -e "ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa" C:/Users/niteris/dev/mikeadams/mike-adams-tx/dist/mike_tx-1.0.5-py3-none-any.whl root@159.223.178.81:/root/dist/
        cmd_list = [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            key_path,
            str(src),
            f"root@{self.public_ip()}:{dest.as_posix()}",
        ]
        cmd_str = subprocess.list2cmdline(cmd_list)

        # make sure the destination directory exists
        self.ssh_exec(f"mkdir -p {dest.parent.as_posix()}")
        print(f"Executing: {cmd_str}")
        cp = subprocess.run(cmd_list, capture_output=True, text=True)
        # assert cp.returncode == 0, f"Error copying file: {cp.stderr}"
        if cp.returncode != 0:
            warnings.warn(f"Error copying file: {cp.stderr}")
        if chmod:
            self.ssh_exec(f"chmod {chmod} {dest.as_posix()}")
        return cp

    def copy_from_remote(
        self, remote_path: Path, local_path: Path
    ) -> subprocess.CompletedProcess:
        key_path = get_private_key()
        # rsync -avz -e "ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa" C:/Users/niteris/dev/mikeadams/mike-adams-tx/dist/mike_tx-1.0.5-py3-none-any.whl root@
        cmd_list = [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            key_path,
            f"root@{self.public_ip()}:{remote_path}",
            str(local_path),
        ]
        cmd_str = subprocess.list2cmdline(cmd_list)
        print(f"Executing: {cmd_str}")
        cp = subprocess.run(cmd_list, capture_output=True, text=True)
        # assert cp.returncode == 0, f"Error copying file: {cp.stderr}"
        if cp.returncode != 0:
            warnings.warn(f"Error copying file: {cp.stderr}")
        return cp

    def delete(self) -> Exception | None:
        try:
            print(f"Deleting droplet: {self.name}")
            # get_digital_ocean().compute.droplet.delete(str(self.id))
            cmd_str = f"doctl compute droplet delete {self.id} --force --output json --interactive=false"
            cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
            if cp.returncode != 0:
                warnings.warn(f"Error deleting droplet: {cp.stderr}")
                return None
        except Exception as e:
            warnings.warn(f"Error deleting droplet: {e}")
            return e
        time.sleep(_TIME_DELETE_BEFORE_GONE)
        if cp.returncode != 0:
            return Exception(f"Error deleting droplet {self.name}: {cp.stderr}")
        return None

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
        cmd_str = "doctl account get --output=json --interactive=false"
        cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp.returncode != 0:
            warnings.warn(f"Error checking authentication: {cp.stderr}")
            return None
        out = json.loads(cp.stdout)
        return Authentication(**out)

    @staticmethod
    def list_machines() -> list[str]:
        cmd_str = (
            "doctl compute image list-distribution --output json --interactive=false"
        )
        cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp.returncode != 0:
            raise Exception(f"Error listing machines: {cp.stderr}")
        data = json.loads(cp.stdout)
        return [d["slug"] for d in data]

    @staticmethod
    def list_droplets() -> list[Droplet]:
        cmd_str = "doctl compute droplet list --output json --interactive=false"
        cp_most = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp_most.returncode != 0:
            raise Exception(f"Error listing droplets: {cp_most.stderr}")
        data_main = json.loads(cp_most.stdout)
        out = [Droplet(data) for data in data_main]
        return out

    @staticmethod
    def list_ssh_keys() -> list[SSHKey]:
        cmd_str = "doctl compute ssh-key list --interactive=false --output json"
        cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        if cp.returncode != 0:
            raise Exception(f"Error listing SSH keys: {cp.stderr}")
        # return json.loads(cp.stdout)
        tmp_list = json.loads(cp.stdout)
        out = [SSHKey(**data) for data in tmp_list]
        return out

    @staticmethod
    def create_droplet(
        name: str,
        ssh_key: SSHKey | None = None,
        tags: list[str] | None = None,
        size: str | None = None,
        image="ubuntu-24-10-x64",
        region="nyc1",
        check=True,
    ) -> Droplet | Exception:
        size = size or "s-2vcpu-2gb"
        assert (
            size in MACHINE_SIZES
        ), f"Invalid size: {size}, choices are {MACHINE_SIZES}"
        if tags:
            for tag in tags:
                if " " in tag:
                    return Exception(f"Tag cannot contain spaces: {tag}")
        if check:
            if DropletManager.find_droplets(name):
                return Exception(f"Droplet already exists: {name}")
        if ssh_key is None:
            keys = DropletManager.list_ssh_keys()
            if not keys:
                return Exception("No SSH keys found.")
            ssh_key = keys[0]
        if not ssh_key:
            return Exception("No SSH key found.")
        args = [
            name,
            "--image",
            image,
            "--size",
            size,
            "--region",
            region,
            "--wait",
        ]
        if tags is not None:
            tag_names_joined = ",".join(tags)
            args += [f"--tag-names={tag_names_joined}"]
            # args += ["--tag-names", ",".join(tags)]
        args += ["--ssh-keys", ssh_key.fingerprint]
        cmd_list = ["doctl", "compute", "droplet", "create"] + args
        cmd_str = subprocess.list2cmdline(cmd_list)
        print(f"Running: {cmd_str}")
        cp = subprocess.run(
            cmd_str,
            capture_output=True,
            text=True,
            shell=True,
        )
        if cp.returncode != 0:
            return Exception(f"Error creating droplet: {cp.stderr}", cp)
        print("Created droplet:", name)
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
            print(f"Error creating droplet: {name}, available droplets: {all_droplets}")
            return Exception(
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
            return Exception(
                f"Cloud Init failed to complete: {stdout_cloudinit}, pwd: {stdout_pwd}"
            )

    @staticmethod
    def find_droplets(
        name: str | None = None, tags: list[str] | None = None
    ) -> list[Droplet]:
        if name is not None:
            name = name.replace("_", "-")
        droplets = DropletManager.list_droplets()
        if name is not None:
            droplets = [d for d in droplets if d.name == name]
        if tags:
            droplets = [d for d in droplets if all(tag in d.tags for tag in tags)]
        return droplets
