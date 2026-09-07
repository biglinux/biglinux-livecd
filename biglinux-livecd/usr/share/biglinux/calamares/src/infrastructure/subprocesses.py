"""Small wrappers around the system commands used by the installer UI."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence


def get_command_output(command: Sequence[str], *, timeout: int = 30) -> str | None:
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def pacman_query_installed() -> list[str]:
    if shutil.which("pacman") is None:
        return []
    output = get_command_output(["pacman", "-Qq"])
    return output.splitlines() if output else []
