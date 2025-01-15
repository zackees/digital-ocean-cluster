import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent

PYTHON_EXE = sys.executable


def build_wheel(setup_py: Path, dist_dir: Path, python: str | None = None) -> None:
    python = python or PYTHON_EXE
    if not setup_py.exists():
        raise FileNotFoundError(f"setup.py not found: {setup_py}")
    if setup_py.name != "setup.py":
        raise ValueError(f"Input setup_py must be setup.py: {setup_py}")
    dist_dir.parent.mkdir(exist_ok=True, parents=True)
    project_root = setup_py.parent
    # python setup.py bdist_wheel
    subprocess.run(
        [PYTHON_EXE, "setup.py", "bdist_wheel"], check=True, cwd=str(project_root)
    )
