# digital-ocean-cluster

A well tested library for managing a fleet of droplets.

[![Linting](../../actions/workflows/lint.yml/badge.svg)](../../actions/workflows/lint.yml)

[![MacOS_Tests](../../actions/workflows/push_macos.yml/badge.svg)](../../actions/workflows/push_macos.yml)
[![Ubuntu_Tests](../../actions/workflows/push_ubuntu.yml/badge.svg)](../../actions/workflows/push_ubuntu.yml)
[![Win_Tests](../../actions/workflows/push_win.yml/badge.svg)](../../actions/workflows/push_win.yml)


# About

This library concurrent creates and runs digital ocean droplets through the doctl command line interface.

To develop software, run `. ./activate`

# Windows

This environment requires you to use `git-bash`.

# Linting

Run `./lint.sh` to find linting errors using `pylint`, `flake8` and `mypy`.

# Pre-requesits

  * You will need to have an ssh key registered with digital ocean. This key must also be in your ~/.ssh folder.
  * You will need to have the doctl binary installed in your path.

TODO: Make a more minimal example

# Example

```python
from pathlib import Path
from threading import Lock

from digital_ocean_cluster import DigitalOceanCluster, Droplet, DropletCreationArgs

from mike_tx.build_whl import build_wheel
from mike_tx.paths import PROJECT_ROOT

TAGS = ["mike-adams", "audit", "progress"]

CLUSTER_SIZE = 1


INSTALL_CMDS = [
    "apt update -y",
    "apt install -y python3 python3-pip python3-venv rclone nodejs npm magic-wormhole",
    "npm install -g pm2 -y",
]


PRINT_LOCK = Lock()

_LOG_FILE = PROJECT_ROOT / "logs" / "do_ourprogress.log"
_LOG_FILE.parent.mkdir(exist_ok=True, parents=True)
# erase log file
if _LOG_FILE.exists():
    _LOG_FILE.write_text("", encoding="utf-8")


def locked_print(*args, **kwargs):
    # open log file
    with PRINT_LOCK:
        try:
            with open(str(_LOG_FILE), "a", encoding="utf-8") as f:
                print(*args, kwargs, file=f)
            print(*args, **kwargs)

        except UnicodeDecodeError as ue:
            print(f"Error in locked_print: {ue}")


def install(droplet: Droplet, ours: bool) -> None:
    for cmd in INSTALL_CMDS:
        stdout = droplet.ssh_exec(cmd).stdout
        locked_print("stdout:", stdout)
    locked_print("Completed installation.")

    locked_print("copying files")
    SRC = PROJECT_ROOT / "dist"
    whl = list(SRC.glob("*.whl"))[0]
    SRC = SRC / whl.name
    DST = Path("/root/dist/" + whl.name)
    droplet.copy_to_remote(SRC, DST)
    # now install the file
    stdout = droplet.ssh_exec(
        f"pip install {DST.as_posix()} --break-system-packages"
    ).stdout
    locked_print("stdout:", stdout)
    if ours:
        cmd_str = "pm2 start 'mike-tx size --ours' && pm2 save && pm2 startup"
    else:
        cmd_str = "pm2 start 'mike-tx size --theirs' && pm2 save && pm2 startup"
    cp = droplet.ssh_exec(cmd_str)
    if cp.returncode != 0:
        locked_print(f"Error running pm2: {cp.stderr}")


def main() -> None:
    build_wheel()  # build the wheel so that we get a fresh copy
    # if DigitalOceanCluster.find_cluster(TAGS):
    #     print("Cluster found, no need to create.")
    #     return
    droplets = DigitalOceanCluster.delete_cluster(TAGS)
    if droplets:
        print(f"Deleted: {[d.name for d in droplets]}")

    def install_ours(droplet: Droplet) -> None:
        install(droplet, True)

    def install_theirs(droplet: Droplet) -> None:
        install(droplet, False)

    args1 = DropletCreationArgs(
        name="progress-ours", tags=TAGS + ["ours"], install=install_ours
    )
    args2 = DropletCreationArgs(
        name="progress-theirs", tags=TAGS + ["theirs"], install=install_theirs
    )

    cluster = DigitalOceanCluster.create_droplets(
        [args1, args2],
    )

    assert len(cluster.failed_droplets) == 0, "Failed to create droplets"

    print(f"Created cluster: {cluster}")
    print("Completed installation.")


if __name__ == "__main__":
    main()
```
