"""
Unit test file.
"""

import unittest
from pathlib import Path

from digital_ocean_cluster import DropletManager

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
assert (PROJECT_ROOT / "pyproject.toml").exists()

TEST_FILE = PROJECT_ROOT / "pyproject.toml"


class DropletCopyTester(unittest.TestCase):
    """Main tester class."""

    @unittest.skip("Skipping test")
    def test_ssh_exec_ls(self) -> None:
        """Test command line interface (CLI)."""
        all_droplets = DropletManager.list_droplets()
        print(f"All Droplets: {all_droplets}")
        droplets = DropletManager.find_droplets("test-droplet-copy")
        if not droplets:
            # create
            droplet = DropletManager.create_droplet(name="test-droplet-copy")
            assert not isinstance(droplet, Exception)
        else:
            droplet = droplets[0]
        assert droplet is not None
        stdout = droplet.copy_to(Path(TEST_FILE), Path("/root/pyproject.toml")).stdout
        print("stdout:", stdout)

        # ssh -i ~/.ssh/my-key root@165.227.209.16 'ls'
        # ssh_cmd = f"ssh -o StrictHostKeyChecking=no -i {get_pub_key_path()} root@{public_ip} 'ls'"
        # import subprocess
        # subprocess.run(ssh_cmd, shell=True, env=env)
        # droplet.ssh_exec("ls")
        print()


if __name__ == "__main__":
    unittest.main()
