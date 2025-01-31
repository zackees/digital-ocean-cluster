import subprocess
import time
import warnings
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from digital_ocean_cluster.droplet_manager import Droplet, DropletManager
from digital_ocean_cluster.ensure_doctl import ensure_doctl
from digital_ocean_cluster.machines import ImageType, MachineSize, Region
from digital_ocean_cluster.types import THREAD_POOL, DropletException, SSHKey


@dataclass
class DropletCreationArgs:
    name: str
    tags: list[str]
    ssh_key: SSHKey | None = None
    size: MachineSize = MachineSize.S_2VCPU_2GB
    image: ImageType = ImageType.UBUNTU_24_10_X64
    region: Region = Region.NYC_1
    # Use a function that throws if there is a failure to execute.
    install: Callable[[Droplet], Any] | None = None

    def __post_init__(self) -> None:
        if "_" in self.name:
            warnings.warn(
                f"Droplet name contains underscore: {self.name}, replacing with dash."
            )
            self.name = self.name.replace("_", "-")

    def to_args(self) -> list[str]:
        args = [
            self.name,
            "--image",
            self.image.value,
            "--size",
            self.size.value,
            "--region",
            self.region.value,
            "--wait",
        ]
        if self.tags is not None:
            args += ["--tag-names", ",".join(self.tags)]
        if self.ssh_key is not None:
            args += ["--ssh-keys", str(self.ssh_key)]
        return args


@dataclass
class DropletCmdArgs:
    droplet: Droplet
    cmd: str


@dataclass
class DropletCopyArgs:
    droplet: Droplet
    local_path: Path
    remote_path: Path


@dataclass
class DropletCluster:
    droplets: list[Droplet]
    failed_droplets: dict[str, DropletException]

    # allow in if statements, return True if droplets are present
    def __bool__(self) -> bool:
        return len(self.droplets) > 0

    # length
    def __len__(self) -> int:
        return len(self.droplets)

    def run_cmd(self, cmd: str) -> dict[Droplet, subprocess.CompletedProcess]:
        return DigitalOceanCluster.run_cluster_cmd(self.droplets, cmd)

    def run_function(self, function: Callable[[Droplet], Any]) -> dict[Droplet, Any]:
        return DigitalOceanCluster.run_cluster_function(self.droplets, function)

    def copy_to(
        self, local_path: Path, remote_path: Path, chmod: str | None = None
    ) -> dict[Droplet, subprocess.CompletedProcess]:
        return DigitalOceanCluster.run_cluster_copy_to(
            self.droplets, local_path, remote_path, chmod=chmod
        )

    def copy_from(
        self, local_path: Path, remote_path: Path
    ) -> dict[Droplet, subprocess.CompletedProcess]:
        ensure_doctl()
        args = [
            DropletCopyArgs(
                droplet=droplet, local_path=local_path, remote_path=remote_path
            )
            for droplet in self.droplets
        ]
        return DigitalOceanCluster.run_cluster_copy_from(args)

    def copy_text_to(
        self, text: str, remote_path: Path
    ) -> dict[Droplet, subprocess.CompletedProcess]:
        ensure_doctl()
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir) / "tmp.txt"
            with open(tmp, "w", newline="\n") as f:
                f.write(text)
            out = self.copy_to(tmp, remote_path)
            # time.sleep(1)  # Give time for the file handle to expire.
            return out

    def copy_text_from(
        self, remote_path: Path
    ) -> dict[Droplet, str | DropletException]:
        ensure_doctl()
        cmd = "cat " + remote_path.as_posix()
        results = self.run_cmd(cmd)
        out: dict[Droplet, str | DropletException] = {}
        for droplet, cp in results.items():
            if cp.returncode == 0:
                out[droplet] = cp.stdout
            else:
                out[droplet] = DropletException(cp.stderr)
        return out

    def delete(self) -> list[Droplet]:
        return DigitalOceanCluster.delete_cluster(self)

    def __str__(self) -> str:
        droplet_names: list[str] = [d.name for d in self.droplets]
        failed_droplets: dict[str, DropletException] = self.failed_droplets
        if not failed_droplets:
            return f"DropletCluster(droplets={droplet_names})"
        return f"DropletCluster(droplets={droplet_names}, failed_droplets={self.failed_droplets})"


class DigitalOceanCluster:

    @staticmethod
    def find_cluster(tags: list[str]) -> DropletCluster:
        ensure_doctl()
        droplets = DropletManager.find_droplets(tags=tags)
        return DropletCluster(droplets=droplets, failed_droplets={})

    @staticmethod
    def delete_cluster(tags: list[str] | DropletCluster) -> list[Droplet]:
        ensure_doctl()
        if isinstance(tags, list):
            droplets = DropletManager.find_droplets(tags=tags)
        else:
            droplets = tags.droplets

        def _delete(droplet: Droplet) -> None:
            droplet.delete()

        THREAD_POOL.map(_delete, droplets)
        droplets = [d for d in droplets]
        timeout = time.time() + 60
        while time.time() < timeout:
            found_droplets = DropletManager.find_droplets()
            # if any of the droplets are still present, wait
            any_found = False
            for d in droplets:
                for d2 in found_droplets:
                    if d2.id == d.id:
                        any_found = True
                        break
            if not any_found:
                break
            time.sleep(1)
        else:
            raise TimeoutError("Timeout waiting for droplets to delete.")
        return droplets

    @staticmethod
    def async_create_droplets(
        args: list[DropletCreationArgs],
    ) -> dict[str, Future[Droplet | Exception]]:
        ensure_doctl()
        # check that the names are unique
        names = [arg.name for arg in args]
        if len(names) != len(set(names)):
            raise ValueError("Names must be unique.")
        tmp: dict[str, Callable[[], Droplet | Exception]] = {}
        for arg in args:
            name = arg.name
            ssh_key = arg.ssh_key
            tags = arg.tags
            size = arg.size
            image = arg.image
            region = arg.region
            install = arg.install

            def task(
                name=name,
                ssh_key=ssh_key,
                tags=tags,
                size=size,
                image=image,
                region=region,
                install=install,
            ) -> Droplet | Exception:
                droplet: Droplet | Exception = DropletManager.create_droplet(
                    name=name,
                    ssh_key=ssh_key,
                    tags=tags,
                    size=size,
                    image=image,
                    region=region,
                    check=False,
                )
                if isinstance(droplet, Exception):
                    return droplet
                if install is not None:
                    try:
                        install(droplet)
                    except Exception as e:
                        return e
                return droplet

            tmp.update({name: task})
        out: dict[str, Future[Droplet | Exception]] = {}
        for name, tsk in tmp.items():
            future = THREAD_POOL.submit(tsk)
            out[name] = future
        return out

    @staticmethod
    def create_droplets(
        args: list[DropletCreationArgs],
    ) -> DropletCluster:
        ensure_doctl()
        futures: dict[str, Future[Droplet | Exception]] = (
            DigitalOceanCluster.async_create_droplets(args)
        )
        droplets: list[Droplet] = []
        failed: dict[str, DropletException] = {}
        for name, future in futures.items():
            result = future.result()
            if isinstance(result, Exception):
                failed[name] = DropletException(str(result))
            else:
                droplet = result
                assert isinstance(droplet, Droplet)
                droplets.append(droplet)
        cluster = DropletCluster(droplets=droplets, failed_droplets=failed)
        return cluster

    @staticmethod
    def async_run_cluster_cmd(
        droplets: list[Droplet], cmd: str
    ) -> dict[Droplet, Future[subprocess.CompletedProcess]]:
        ensure_doctl()
        # futures: list[Future[subprocess.CompletedProcess]] = []
        droplet: Droplet
        out: dict[Droplet, Future[subprocess.CompletedProcess]] = {}
        for droplet in droplets:

            def task(
                droplet: Droplet = droplet, cmd: str = cmd
            ) -> subprocess.CompletedProcess:
                return droplet.ssh_exec(cmd)

            future = THREAD_POOL.submit(task)
            out[droplet] = future
        return out

    @staticmethod
    def run_cluster_cmd(
        droplets: list[Droplet], cmd: str
    ) -> dict[Droplet, subprocess.CompletedProcess]:
        ensure_doctl()
        futures: dict[Droplet, Future[subprocess.CompletedProcess]] = (
            DigitalOceanCluster.async_run_cluster_cmd(droplets, cmd)
        )
        out: dict[Droplet, subprocess.CompletedProcess] = {}
        for droplet, future in futures.items():
            out[droplet] = future.result()
        return out

    @staticmethod
    def async_run_cluster_function(
        droplets: list[Droplet], function: Callable[[Droplet], Any]
    ) -> dict[Droplet, Any]:
        ensure_doctl()
        futures: dict[Droplet, Future[Any]] = {}
        droplet: Droplet
        for droplet in droplets:

            def task(
                droplet: Droplet = droplet,
                function: Callable[[Droplet], Any] = function,
            ) -> Any:
                return function(droplet)

            future = THREAD_POOL.submit(task)
            futures[droplet] = future
        return futures

    @staticmethod
    def run_cluster_function(
        droplets: list[Droplet], function: Callable[[Droplet], Any]
    ) -> dict[Droplet, Any | DropletException]:
        ensure_doctl()
        futures: dict[Droplet, Future[Any]] = (
            DigitalOceanCluster.async_run_cluster_function(droplets, function)
        )
        out: dict[Droplet, Any | Exception] = {}
        for droplet, future in futures.items():
            try:
                result = future.result()
                out[droplet] = result
            except Exception as e:
                out[droplet] = DropletException(str(e))
        return out

    @staticmethod
    def async_run_cluster_copy_to(
        droplets: list[Droplet],
        local_path: Path,
        remote_path: Path,
        chmod: str | None = None,
    ) -> dict[Droplet, Future[subprocess.CompletedProcess]]:
        ensure_doctl()
        futures: dict[Droplet, Future[subprocess.CompletedProcess]] = {}
        droplet: Droplet
        for droplet in droplets:

            def task(
                droplet: Droplet = droplet,
                local_path: Path = local_path,
                remote_path: Path = remote_path,
                chmod: str | None = chmod,
            ) -> subprocess.CompletedProcess:
                return droplet.copy_to(local_path, remote_path, chmod)

            future = THREAD_POOL.submit(task)
            futures[droplet] = future
        return futures

    @staticmethod
    def run_cluster_copy_to(
        droplets: list[Droplet],
        local_path: Path,
        remote_path: Path,
        chmod: str | None = None,
    ) -> dict[Droplet, subprocess.CompletedProcess]:
        ensure_doctl()
        futures: dict[Droplet, Future[subprocess.CompletedProcess]] = (
            DigitalOceanCluster.async_run_cluster_copy_to(
                droplets, local_path, remote_path, chmod=chmod
            )
        )
        out: dict[Droplet, subprocess.CompletedProcess] = {}
        for droplet, future in futures.items():
            out[droplet] = future.result()
        return out

    @staticmethod
    def async_run_cluster_copy_from(
        args: list[DropletCopyArgs],
    ) -> dict[Droplet, Future[subprocess.CompletedProcess]]:
        ensure_doctl()
        out: dict[Droplet, Future[subprocess.CompletedProcess]] = {}
        arg: DropletCopyArgs
        for arg in args:

            def task(
                droplet: Droplet = arg.droplet,
                local_path: Path = arg.local_path,
                remote_path: Path = arg.remote_path,
            ) -> subprocess.CompletedProcess:
                return droplet.copy_from(local_path, remote_path)

            out[arg.droplet] = THREAD_POOL.submit(task)
        return out

    @staticmethod
    def run_cluster_copy_from(
        args: list[DropletCopyArgs],
    ) -> dict[Droplet, subprocess.CompletedProcess]:
        ensure_doctl()
        futures: dict[Droplet, Future[subprocess.CompletedProcess]] = (
            DigitalOceanCluster.async_run_cluster_copy_from(args)
        )
        out: dict[Droplet, subprocess.CompletedProcess] = {}
        for droplet, future in futures.items():
            out[droplet] = future.result()
        return out
