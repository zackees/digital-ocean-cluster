import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent

PYTHON_EXE = sys.executable


def _file_list_whl(path: Path) -> list[Path]:
    out = list(path.iterdir())
    out = [x for x in out if x.is_file() and x.suffix == ".whl"]
    return out


def build_wheel(setup_py: Path, dist_dir: Path, python: str | None = None) -> Path:
    python = python or PYTHON_EXE
    if not setup_py.exists():
        raise FileNotFoundError(f"setup.py not found: {setup_py}")
    if setup_py.name != "setup.py":
        raise ValueError(f"Input setup_py must be setup.py: {setup_py}")
    dist_dir.mkdir(exist_ok=True, parents=True)
    project_root = setup_py.parent
    # python setup.py bdist_wheel
    old_wheels = _file_list_whl(dist_dir)
    cmd_list = [python, "setup.py", "bdist_wheel", "--dist-dir", str(dist_dir)]
    cmd_str = subprocess.list2cmdline(cmd_list)
    dist_dir.mkdir(exist_ok=True, parents=True)
    print(f"Running: {cmd_str}")
    subprocess.run(
        cmd_list,
        check=True,
        cwd=str(project_root),
    )
    # now find the new file
    new_wheels = _file_list_whl(dist_dir)
    if len(new_wheels) != 1:
        raise ValueError(
            f"Expected one wheel file, got {len(new_wheels)}: {new_wheels}"
        )
    diff = set(new_wheels) - set(old_wheels)
    if len(diff) != 1:
        # second course of action, look at the files and grab the one with the most recent timestamp
        sorted_items = sorted(new_wheels, key=lambda x: x.stat().st_mtime, reverse=True)
        return sorted_items[0]
    return diff.pop()
