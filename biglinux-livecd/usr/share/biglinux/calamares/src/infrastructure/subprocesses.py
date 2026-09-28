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


def pacman_required_by(packages: Sequence[str]) -> dict[str, list[str]]:
    """Map each installed package to the installed packages that depend on it."""
    if not packages or shutil.which("pacman") is None:
        return {}
    # "Required By" is a translated label, so pin the locale to parse it.
    output = get_command_output(
        ["env", "LC_ALL=C", "pacman", "-Qi", "--", *packages], timeout=60
    )
    if not output:
        return {}
    required_by: dict[str, list[str]] = {}
    name = ""
    field = ""
    for line in output.splitlines():
        if line[:1].isspace():
            # A value wrapped onto the next line belongs to the field above.
            key, value = field, line
        else:
            key, _sep, value = line.partition(":")
            key = key.strip()
            field = key
        if key == "Name":
            name = value.strip()
        elif key == "Required By" and name:
            values = [item for item in value.split() if item != "None"]
            required_by.setdefault(name, []).extend(values)
    return required_by
