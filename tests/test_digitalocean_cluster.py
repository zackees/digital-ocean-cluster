"""
Unit test file.
"""

import os
import unittest
from pathlib import Path

from digital_ocean_cluster import (
    DigitalOceanCluster,
    Droplet,
    DropletCluster,
    DropletCreationArgs,
)
from digital_ocean_cluster.types import CompletedProcess, DropletException

# os.environ["home"] = "/home/niteris"

IS_GITHUB = os.environ.get("GITHUB_ACTIONS", False)

TAGS = ["test", "cluster"]

CLUSTER_SIZE = 1


def install(droplet: Droplet) -> None:
    """Install a package."""
    # droplet.run_cmd("apt-get update")
    # droplet.run_cmd("apt-get install -y vim")
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
            DropletCreationArgs(
                name=f"test-droplet-creation-{i}", tags=TAGS, install=install
            )
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
        results: dict[Droplet, str | DropletException] = cluster.copy_text_from(
            remote_path
        )
        for droplet, text in results.items():
            if isinstance(text, DropletException):
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
