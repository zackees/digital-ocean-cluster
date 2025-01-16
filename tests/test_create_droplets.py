"""
Unit test file.
"""

import os
import unittest
from pathlib import Path

from digital_ocean_cluster import DigitalOceanCluster, DropletManager
from digital_ocean_cluster.types import DropletException

# os.environ["home"] = "/home/niteris"

IS_GITHUB = os.environ.get("GITHUB_ACTIONS", False)

TAGS = ["test", "cluster"]


def get_pub_key_path() -> str:
    """Get public key."""
    home = os.environ["HOME"]
    home_path = Path(home).as_posix()
    return f"{home_path}/.ssh/id_rsa.pub"


class DropletCreationCycleTester(unittest.TestCase):
    """Main tester class."""

    @unittest.skipIf(IS_GITHUB, "Skipping test for GitHub Actions")
    def test_create_droplets(self) -> None:
        """Test command line interface (CLI)."""
        DigitalOceanCluster.delete_cluster(TAGS)
        droplets = DropletManager.find_droplets("test-droplet-creation")
        self.assertEqual(len(droplets), 0)
        ssh_keys = DropletManager.list_ssh_keys()
        print(f"SSH Keys: {ssh_keys}")
        self.assertTrue(
            len(ssh_keys) > 0, "You MUST have at least one SSH key to run this test."
        )
        droplet = DropletManager.create_droplet(
            name="test-droplet-creation", ssh_key=ssh_keys[0], tags=TAGS
        )
        assert not isinstance(droplet, DropletException)
        print(f"Droplet: {droplet}")
        self.assertTrue(droplet.is_valid())
        self.assertIsNotNone(droplet)
        cp = droplet.ssh_exec("ls")
        print(f"Completed Process: {cp}")
        print("Output:", cp.stdout)
        droplet.delete()
        droplets = DropletManager.find_droplets("test-droplet-creation")  # type: ignore
        self.assertEqual(len(droplets), 0)


if __name__ == "__main__":
    unittest.main()
