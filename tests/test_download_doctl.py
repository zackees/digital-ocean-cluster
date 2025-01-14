"""
Unit test file.
"""

import unittest
from pathlib import Path

from digital_ocean_cluster.download_doctl import download_doctl

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
assert (PROJECT_ROOT / "pyproject.toml").exists()

TEST_FILE = PROJECT_ROOT / "pyproject.toml"


class DownloadDoctlTester(unittest.TestCase):
    """Main tester class."""

    def test_download_doctl(self) -> None:
        """Test command line interface (CLI)."""
        path: Path = download_doctl()
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
