#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import libcalamares


def run() -> tuple[str, str] | None:
    requested_root = libcalamares.globalstorage.value("rootMountPoint")
    if not isinstance(requested_root, str) or not requested_root:
        return (
            "Btrfs target missing",
            "The installation target could not be determined.",
        )

    root = Path(os.path.realpath(requested_root))
    if root == Path("/") or not root.is_dir():
        return (
            "Unsafe installation target",
            "The installation target is missing or resolves to the running system.",
        )

    filesystem = subprocess.run(
        [
            "/usr/bin/findmnt",
            "--noheadings",
            "--output",
            "FSTYPE",
            "--target",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if filesystem.returncode != 0:
        return (
            "Could not identify the installation filesystem",
            "findmnt could not determine whether the target uses Btrfs.",
        )
    if filesystem.stdout.strip() != "btrfs":
        return None

    for relative_path in ("usr/share/grub", "boot"):
        target = root / relative_path
        if not target.exists():
            continue
        if target.is_symlink():
            return (
                "Unsafe Btrfs target",
                f"The installation path contains a symbolic link: {target}",
            )
        try:
            resolved = target.resolve(strict=True)
        except OSError as error:
            return ("Could not resolve Btrfs target", str(error))
        if root not in resolved.parents:
            return (
                "Unsafe Btrfs target",
                f"The path escapes the installation root: {target}",
            )
        try:
            subprocess.run(
                [
                    "/usr/bin/btrfs",
                    "filesystem",
                    "defragment",
                    "--nocomp",
                    "-r",
                    str(resolved),
                ],
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            return (
                "Btrfs post-installation correction failed",
                f"Could not defragment {resolved}: {error}",
            )
    return None
