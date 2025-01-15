"""
Unit test file.
"""

import os
import unittest
from pathlib import Path

from digital_ocean_cluster.ensure_doctl import ensure_doctl

# os.environ["home"] = "/home/niteris"

IS_GITHUB = os.environ.get("GITHUB_ACTIONS", False)


class DoctlTester(unittest.TestCase):
    """Main tester class."""

    @unittest.skipIf(IS_GITHUB, "Skipping test for GitHub Actions")
    def test_doctl_binary_exists(self) -> None:
        """Test command line interface (CLI)."""
        path: Path = ensure_doctl()
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
