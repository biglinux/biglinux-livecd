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
# 5. Pre-installation wizard configs (minimal mode, XivaStudio packages)
#

import libcalamares
import os
import shutil
import subprocess
from libcalamares.utils import debug


def copy_calamares_configs(root_mount_point):
    """
    Copy Calamares-generated configuration files that need to persist.
    These are additional configs created by the pre-installation wizard.
    """
    # Copy minimal package removal list if it exists
    minimal_list = "/tmp/calamares_remove_packages"
    if os.path.isfile(minimal_list):
        dst = os.path.join(root_mount_point, "tmp/calamares_remove_packages")
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(minimal_list, dst)
            debug("Copied minimal packages list")
        except Exception as e:
            debug(f"Warning: Could not copy minimal list: {e}")

    # Copy XivaStudio netinstall config if it exists
    xiva_config = "/tmp/calamares_xivastudio_packages"
    if os.path.isfile(xiva_config):
        dst = os.path.join(root_mount_point, "tmp/calamares_xivastudio_packages")
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(xiva_config, dst)
            debug("Copied XivaStudio packages list")
        except Exception as e:
            debug(f"Warning: Could not copy XivaStudio list: {e}")


def run():
    """
    Main entry point for the Calamares module.

    Performs BigLinux-specific post-installation setup:
    1. Runs biglinux-install-setup.sh for:
       - GRUB configuration (theme, parameters)
       - SDDM session setup (Wayland/X11)
       - Fstab optimization (btrfs compression)
       - Live session config migration (theme, desktop, JamesDSP, display)
    2. Copies Calamares pre-installation wizard configs
    """
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")

    if not root_mount_point:
        return (
            "Root mount point not found",
            "Could not determine the installation target",
        )

    debug(f"Running BigLinux installation setup on {root_mount_point}")

    # Run biglinux-install-setup.sh passing the root mount point
    # This script handles GRUB, SDDM, fstab and live session config migration
    try:
        result = subprocess.call([
            "/usr/bin/biglinux-install-setup.sh",
            root_mount_point,
        ])
        if result != 0:
            debug(f"biglinux-install-setup.sh returned non-zero exit code: {result}")
    except Exception as e:
        debug(f"Warning: Could not run biglinux-install-setup.sh: {e}")

    # Copy Calamares pre-installation wizard configs
    copy_calamares_configs(root_mount_point)

    debug("BigLinux installation setup completed successfully")
    return None
