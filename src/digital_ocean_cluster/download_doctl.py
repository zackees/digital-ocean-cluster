import os
from pathlib import Path

from appdirs import user_cache_dir
from download import download
from filelock import FileLock

_VERSION = os.environ.get("DOCTL_VERSION", "1.120.2")


def _lock_file() -> FileLock:
    cache_dir = Path(user_cache_dir("doctl"))
    cache_dir.mkdir(exist_ok=True, parents=True)
    return FileLock(cache_dir / "doctl.lock")


_LOCK = _lock_file()
_DOCTL_PATH: Path | None = None


def download_doctl() -> Path:
    import platform
    import shutil
    import tarfile
    import zipfile
    from pathlib import Path

    global _DOCTL_PATH

    if _DOCTL_PATH is not None:
        return _DOCTL_PATH

    # Determine OS and architecture
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Map architecture names
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "i386": "386",
        "i686": "386",
    }
    arch = arch_map.get(machine, machine)

    # Construct base URL
    base_url = f"https://github.com/digitalocean/doctl/releases/download/v{_VERSION}"

    # Construct filename based on platform
    if system == "windows":
        filename = f"doctl-{_VERSION}-windows-{arch}.zip"
    else:
        filename = f"doctl-{_VERSION}-{system}-{arch}.tar.gz"

    url = f"{base_url}/{filename}"

    with _LOCK:
        # Use user_cache_dir for downloads and binary storage
        cache_dir = Path(user_cache_dir("doctl"))
        cache_dir.mkdir(exist_ok=True, parents=True)

        binary_name = "doctl.exe" if system == "windows" else "doctl"
        dest = cache_dir / f"doctl-{_VERSION}{'.exe' if system == 'windows' else ''}"
        if dest.exists():
            return dest

        # Download the file
        downloaded_file = cache_dir / filename
        download(url, str(downloaded_file), replace=True)

        # Extract the binary
        if system == "windows":
            with zipfile.ZipFile(downloaded_file, "r") as zip_ref:
                zip_ref.extractall(cache_dir)
            binary_name = "doctl.exe"
        else:
            with tarfile.open(downloaded_file, "r:gz") as tar_ref:
                tar_ref.extractall(cache_dir)
            binary_name = "doctl"

        # Move binary to final location in cache directory
        source = cache_dir / binary_name
        dest = cache_dir / f"doctl-{_VERSION}{'.exe' if system == 'windows' else ''}"

        shutil.move(str(source), str(dest))

        # Make binary executable on Unix-like systems
        if system != "windows":
            dest.chmod(0o755)

        # Clean up downloaded archive
        downloaded_file.unlink()
        _DOCTL_PATH = dest
        return dest
