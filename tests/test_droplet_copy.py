"""
Unit test file.
"""

import tempfile
import unittest
from pathlib import Path

from digital_ocean_cluster import DigitalOceanCluster, DropletManager

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
assert (PROJECT_ROOT / "pyproject.toml").exists()

TEST_FILE = PROJECT_ROOT / "pyproject.toml"

_TAGS = ["test", "copy"]


class DropletCopyTester(unittest.TestCase):
    """Main tester class."""

    # @unittest.skip("Skipping test")
    def test_ssh_exec_ls(self) -> None:
        """Test command line interface (CLI)."""
        # all_droplets = DropletManager.list_droplets()
        DigitalOceanCluster.delete_cluster(tags=_TAGS)
        droplet = DropletManager.create_droplet(name="test-droplet-ls", tags=_TAGS)
        assert not isinstance(droplet, Exception)
        assert droplet is not None
        with tempfile.TemporaryDirectory() as tmpdir:
            # test uploading a folder
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "test.txt").write_text("Hello World!")
            droplet.copy_to(tmpdir_path, Path("/root/folder"))
            print("Uploaded files:")
            cp = droplet.ssh_exec("ls /root/folder")
            self.assertTrue("test.txt" in cp.stdout)
        DigitalOceanCluster.delete_cluster(tags=_TAGS)


if __name__ == "__main__":
    unittest.main()
