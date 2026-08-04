"""Repository-local bootstrap and diagnostics entry point.

This tiny stdlib-only launcher exists so the project can create its isolated
virtual environment before any third-party dependency is available.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"


def doctor() -> int:
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "project_root": str(PROJECT_ROOT),
                "venv_exists": VENV_DIR.is_dir(),
            },
            indent=2,
        )
    )
    return 0


def bootstrap() -> int:
    if sys.version_info < (3, 11):
        raise SystemExit("GeoForge Studio requires Python 3.11 or newer (3.12 recommended).")
    if not VENV_DIR.exists():
        venv.EnvBuilder(with_pip=True, upgrade_deps=False).create(VENV_DIR)
    pip = VENV_DIR / "bin" / "python"
    subprocess.run(
        [str(pip), "-m", "pip", "install", "--disable-pip-version-check", "-e", ".[dev]"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return doctor()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GeoForge Studio local project launcher")
    parser.add_argument("command", choices=("doctor", "bootstrap"), nargs="?", default="doctor")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(bootstrap() if args.command == "bootstrap" else doctor())
