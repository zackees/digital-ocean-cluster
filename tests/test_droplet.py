"""
Unit test file.
"""

import unittest

from digital_ocean_cluster import DropletManager


class DropletTester(unittest.TestCase):
    """Main tester class."""

    def test_authenticated(self) -> None:
        """Test command line interface (CLI)."""
        is_authenticated = DropletManager.is_authenticated()
        print(f"Authenticated: {is_authenticated}")
        self.assertTrue(DropletManager.is_authenticated())

    def test_machines(self) -> None:
        """Test command line interface (CLI)."""
        machines = DropletManager.list_machines()
        print(f"Machines: {machines}")
        self.assertTrue(len(machines) > 0)

    def test_list_ssh_keys(self) -> None:
        """Test command line interface (CLI)."""
        keys = DropletManager.list_ssh_keys()
        print(f"SSH Keys: {keys}")
        self.assertTrue(len(keys) > 0)

    def test_droplet_is_valid(self) -> None:
        """Test if a droplet is valid."""
        droplets = DropletManager.list_droplets()
        self.assertTrue(len(droplets) > 0, "No droplets found to test.")

        # Assuming we take the first droplet for testing
        droplet = droplets[0]
        is_valid = droplet.is_valid()
        print(f"Droplet ID: {droplet.id}, Name: {droplet.name}, Is Valid: {is_valid}")
        self.assertTrue(is_valid, f"Droplet {droplet.name} is not valid.")

    def test_list_droplets(self) -> None:
        """Test command line interface (CLI)."""
        droplets = DropletManager.list_droplets()
        print(f"Droplets: {droplets}")
        self.assertTrue(len(droplets) > 0)


if __name__ == "__main__":
    unittest.main()
