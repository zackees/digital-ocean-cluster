import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from digital_ocean_cluster.download_doctl import download_doctl

_DOCTL: Path | None = None


def _test_authenticated() -> bool:
    # doctl account get
    cp = subprocess.run(["doctl", "account", "get"], capture_output=True)
    return cp.returncode == 0


def ensure_doctl(token: str | None = None) -> Path:
    global _DOCTL
    if _DOCTL is not None:
        return _DOCTL

    doctl = download_doctl()
    assert doctl.exists()

    # Load environment variables from .env file
    load_dotenv()

    auth_token: str | None = None

    # If token is explicitly provided, use it
    if token is not None:
        auth_token = token
    # Otherwise check environment variable
    else:
        auth_token = os.getenv("DIGITALOCEAN_ACCESS_TOKEN")

    if auth_token is not None:
        # Initialize doctl with the token
        cmd_list = [str(doctl), "auth", "init", "-t", auth_token]
        cp = subprocess.run(cmd_list, capture_output=True)
        if cp.returncode != 0:
            raise RuntimeError(
                f"Failed to initialize doctl with token: {cp.stderr.decode()}"
            )

    if not _test_authenticated():
        raise RuntimeError(
            "No DigitalOcean access token found. Please either:\n"
            "1. Set DIGITALOCEAN_ACCESS_TOKEN in your .env file\n"
            "2. Set DIGITALOCEAN_ACCESS_TOKEN environment variable\n"
            "3. Provide token explicitly to this function"
        )

    _DOCTL = doctl
    return doctl
