import os
from pathlib import Path

from digital_ocean_cluster.download_doctl import download_doctl


def ensure_doctl() -> Path:
    path = download_doctl()
    assert path.exists()
    prev_path = os.environ["PATH"]
    if "doctl" in prev_path:
        return path
    os_sep = ";" if os.name == "nt" else ":"
    os.environ["PATH"] = f"{path.parent}{os_sep}{prev_path}"
    return path
