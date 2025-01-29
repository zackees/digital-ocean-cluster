import json
import subprocess
import time
import warnings

from digital_ocean_cluster.droplet import Droplet
from digital_ocean_cluster.ensure_doctl import ensure_doctl
from digital_ocean_cluster.locked_print import locked_print
from digital_ocean_cluster.machines import ImageType, MachineSize, Region
from digital_ocean_cluster.settings import SLEEP_TIME_BEFORE_SSH
from digital_ocean_cluster.types import (
    Authentication,
    DropletException,
    SSHKey,
)


class DropletManager:

    @staticmethod
    def is_authenticated() -> Authentication | None:
        doctl = str(ensure_doctl())
        # cmd_str = "doctl account get --output=json --interactive=false"
        cmd_list: list[str] = [
            doctl,
            "account",
            "get",
            "--output=json",
            "--interactive=false",
        ]
        # cmd_str = subprocess.list2cmdline(cmd_list)
        cp = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
        if cp.returncode != 0:
            warnings.warn(f"Error checking authentication: {cp.stderr}")
            return None
        out = json.loads(cp.stdout)
        return Authentication(**out)

    @staticmethod
    def list_machines() -> list[str]:
        doctl = str(ensure_doctl())
        # cmd_str = (
        #     "doctl compute image list-distribution --output json --interactive=false"
        # )
        cmd_list: list[str] = [
            doctl,
            "compute",
            "image",
            "list-distribution",
            "--output=json",
            "--interactive=false",
        ]
        cp = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
        if cp.returncode != 0:
            raise DropletException(f"Error listing machines: {cp.stderr}")
        data = json.loads(cp.stdout)
        return [d["slug"] for d in data]

    @staticmethod
    def list_droplets() -> list[Droplet]:
        path = str(ensure_doctl())
        # cmd_str = "doctl compute droplet list --output json --interactive=false"
        cmd_list: list[str] = [
            path,
            "compute",
            "droplet",
            "list",
            "--output=json",
            "--interactive=false",
        ]
        cmd_str = subprocess.list2cmdline(cmd_list)
        locked_print(f"Running: {cmd_str}")
        cp_most = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
        if cp_most.returncode != 0:
            raise DropletException(f"Error listing droplets: {cp_most.stderr}")
        data_main = json.loads(cp_most.stdout)
        out = [Droplet(data) for data in data_main]
        return out

    @staticmethod
    def list_ssh_keys() -> list[SSHKey]:
        doctl = str(ensure_doctl())
        # cmd_str = "doctl compute ssh-key list --interactive=false --output json"
        cmd_list: list[str] = [
            doctl,
            "compute",
            "ssh-key",
            "list",
            "--interactive=false",
            "--output=json",
        ]
        # cp = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        cp = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
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
        doctl = str(ensure_doctl())
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
        cmd_list = [doctl, "compute", "droplet", "create"] + args
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
