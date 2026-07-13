#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://github.com/calamares> ===
#
#   Copyright 2014, Kevin Kofler <kevin.kofler@chello.at>
#   Copyright 2016, Philip Müller <philm@manjaro.org>
#   Copyright 2017, Alf Gaida <agaida@siduction.org>
#   Copyright 2024, Bruno Goncalves <www.biglinux.com.br>
#
#   Calamares is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Calamares is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Calamares. If not, see <http://www.gnu.org/licenses/>.
#
# BigLinux Installation Setup Module
#
# This Calamares module applies BigLinux-specific configurations to the
# installed system. It runs after the main installation is complete and
# handles the following tasks:
#
# 1. GRUB configuration (BigLinux theme, kernel parameters, cleanup)
# 2. SDDM session configuration (Wayland/X11 based on boot mode)
# 3. Fstab optimization (btrfs compression levels)
# 4. Live session config migration (theme, desktop, JamesDSP, display profile)
#

import os
import subprocess

import libcalamares
from libcalamares.utils import debug


def run() -> tuple[str, str] | None:
    """
    Main entry point for the Calamares module.

    Performs BigLinux-specific post-installation setup:
    1. Runs biglinux-install-setup.sh for:
       - GRUB configuration (theme, parameters)
       - SDDM session setup (Wayland/X11)
       - Fstab optimization (btrfs compression)
       - Live session config migration (theme, desktop, JamesDSP, display)
    """
    requested_root = libcalamares.globalstorage.value("rootMountPoint")

    if not isinstance(requested_root, str) or not requested_root:
        return (
            "Root mount point not found",
            "Could not determine the installation target",
        )

    root_mount_point = os.path.realpath(requested_root)
    if root_mount_point == "/" or not os.path.isdir(root_mount_point):
        return (
            "Unsafe installation target",
            "The installation target is missing or resolves to the running system.",
        )

    debug(f"Running BigLinux installation setup on {root_mount_point}")

    # Run biglinux-install-setup.sh passing the root mount point
    # This script handles GRUB, SDDM, fstab and live session config migration
    try:
        subprocess.run(
            ["/usr/bin/biglinux-install-setup.sh", root_mount_point],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        debug(f"BigLinux installation setup failed: {error}")
        return (
            "BigLinux installation setup failed",
            "The installed system could not be finalized safely. See the installation log.",
        )

    debug("BigLinux installation setup completed successfully")
    return None
