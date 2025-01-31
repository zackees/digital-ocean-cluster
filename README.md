# digital-ocean-cluster

A well tested library for managing a fleet of droplets.

[![Linting](../../actions/workflows/lint.yml/badge.svg)](../../actions/workflows/lint.yml)

[![MacOS_Tests](../../actions/workflows/push_macos.yml/badge.svg)](../../actions/workflows/push_macos.yml)
[![Ubuntu_Tests](../../actions/workflows/push_ubuntu.yml/badge.svg)](../../actions/workflows/push_ubuntu.yml)
[![Win_Tests](../../actions/workflows/push_win.yml/badge.svg)](../../actions/workflows/push_win.yml)


# About

This library concurrent creates and runs digital ocean droplets through the doctl command line interface. This api allows massive concurrency running each action on a seperate thread.

The amount of implemented features for doctl is very few, but just enough to bring up a Droplet cloud, install dependencies, and execute commands on the cluster.

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
"""
Unit test file.
"""

import os
import subprocess
import unittest
from pathlib import Path

from digital_ocean_cluster import (
    DigitalOceanCluster,
    Droplet,
    DropletCluster,
    DropletCreationArgs,
)

# os.environ["home"] = "/home/niteris"

IS_GITHUB = os.environ.get("GITHUB_ACTIONS", False)

TAGS = ["test", "cluster"]

CLUSTER_SIZE = 4


def install(droplet: Droplet) -> None:
    """Install a package."""
    # droplet.run_cmd("apt-get update")
    #droplet.run_cmd("apt-get install -y vim")
    droplet.copy_text_to("echo 'Install Done!'", Path("/root/test.sh"))

class DigitalOceanClusterTester(unittest.TestCase):
    """Main tester class."""

    @unittest.skipIf(IS_GITHUB, "Skipping test for GitHub Actions")
    def test_create_droplets(self) -> None:
        """Test command line interface (CLI)."""
        # first delete the previous cluster
        # create a cluster of 4 machines
        # Deleting the cluster
        deleted: list[Droplet] = DigitalOceanCluster.delete_cluster(TAGS)
        print(f"Deleted: {[d.name for d in deleted]}")

        creation_args: list[DropletCreationArgs] = [
            DropletCreationArgs(name=f"test-droplet-creation-{i}", tags=TAGS, install=install)
            for i in range(CLUSTER_SIZE)
        ]

        print(f"Creating droplets: {creation_args}")
        cluster: DropletCluster = DigitalOceanCluster.create_droplets(creation_args)
        self.assertEqual(len(cluster.droplets), CLUSTER_SIZE)
        self.assertEqual(len(cluster.failed_droplets), 0)

        # now run ls on all of them
        cmd = "pwd"
        result: dict[Droplet, CompletedProcess] = cluster.run_cmd(cmd)
        for _, cp in result.items():
            self.assertIn(
                "/root",
                cp.stdout,
                f"Error: {cp.returncode}\n\nstderr:\n{cp.stderr}\n\nstdout:\n{cp.stdout}",
            )

        content: str = "the quick brown fox jumps over the lazy dog"
        remote_path = Path("/root/test.txt")

        # now copy a file to all of them
        cluster.copy_text_to(content, remote_path)

        # now get the text back
        results: dict[Droplet, str | Exception] = cluster.copy_text_from(remote_path)
        for droplet, text in results.items():
            if isinstance(text, Exception):
                print(f"Error: {text}")
                self.fail(f"Droplet {droplet.name} failed\nError: {text}")
            else:
                print(f"Text: {text}")

        print("Deleting cluster")
        # now delete the cluster
        DigitalOceanCluster.delete_cluster(cluster)
        print("Deleted cluster")


if __name__ == "__main__":
    unittest.main()

```
