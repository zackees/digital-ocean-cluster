"""
Unit test file.
"""

import os
import unittest
from pathlib import Path

from digital_ocean_cluster import Droplet, DropletManager
from digital_ocean_cluster.cluster import DigitalOceanCluster

# os.environ["home"] = "/home/niteris"

TAGS = ["test", "ssh_exec"]


def get_pub_key_path() -> str:
    """Get public key."""
    home = os.environ["HOME"]
    home_path = Path(home).as_posix()
    return f"{home_path}/.ssh/id_rsa.pub"


class DropletExecTester(unittest.TestCase):
    """Main tester class."""

    def test_ssh_exec_ls(self) -> None:
        """Test command line interface (CLI)."""
        DigitalOceanCluster.delete_cluster(TAGS)
        existing_droplets = DropletManager.find_droplets("test-droplet-ssh")
        for d in existing_droplets:
            print(f"Deleting droplet: {d.name}")
            d.delete()
        ssh_keys = DropletManager.list_ssh_keys()
        print(f"SSH Keys: {ssh_keys}")
        self.assertTrue(
            len(ssh_keys) > 0, "You MUST have at least one SSH key to run this test."
        )
        ssh_key = ssh_keys[0]
        print(f"Using SSH Key: {ssh_key}")
        # create
        droplet: Droplet | Exception = DropletManager.create_droplet(
            name="test-droplet-ssh", ssh_key=ssh_key, tags=TAGS
        )
        self.assertIsInstance(droplet, Droplet, f"Error: {droplet}")
        assert not isinstance(droplet, Exception)
        # Assuming we take the first droplet for testing
        public_ip = droplet.public_ip()
        print(f"Public IP: {public_ip}")
        droplet.ssh_exec("ls")
        print()
        rtn_value = droplet.ssh_exec("this is a bad call")
        print(f"Return Value: {rtn_value}")
        self.assertTrue(rtn_value.returncode != 0)
        droplet.delete()


if __name__ == "__main__":
    unittest.main()
