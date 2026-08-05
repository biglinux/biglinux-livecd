"""Prepare the selected Calamares profile for installation."""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

from ..infrastructure import (
    CALAMARES_CONFIG_DIR,
    CALAMARES_CONFIGS,
    CALAMARES_MODULES_DIR,
    PARTITION_CONF_FILE,
    TEMP_FILES,
    copy_file_safe,
    ensure_directory,
    read_text_file,
    write_text_file,
)
from .system_service import SystemService


@dataclass
class InstallationConfig:
    """Values that change after the user confirms an installation."""

    filesystem_type: str = "btrfs"
    packages_to_remove: list[str] = field(default_factory=list)
    packages_to_install: list[str] = field(default_factory=list)
    sfs_folder: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "filesystem_type": self.filesystem_type,
            "packages_to_remove": self.packages_to_remove,
            "packages_to_install": self.packages_to_install,
            "sfs_folder": self.sfs_folder,
        }


class InstallService:
    """Write the few Calamares files that depend on live-session state."""

    def __init__(self, system_service: SystemService) -> None:
        self.logger = logging.getLogger(__name__)
        self.system_service = system_service
        self._current_config = InstallationConfig()
        self._is_initialized = False

    def initialize(self) -> None:
        if self._is_initialized:
            return
        ensure_directory(CALAMARES_CONFIG_DIR)
        ensure_directory(CALAMARES_MODULES_DIR)
        self._is_initialized = True

    def cleanup(self) -> None:
        try:
            TEMP_FILES["wait_install"].unlink(missing_ok=True)
        except OSError as error:
            self.logger.warning(
                "Could not remove %s: %s", TEMP_FILES["wait_install"], error
            )
        self._is_initialized = False

    def configure_installation(self, config: InstallationConfig) -> bool:
        self.logger.info("Configuring installation with: %s", config.to_dict())
        self._current_config = config
        try:
            TEMP_FILES["wait_install"].touch()
            TEMP_FILES["start_calamares"].unlink(missing_ok=True)
            return (
                self._configure_partition_settings()
                and self._configure_unpack_settings()
                and self._configure_package_settings()
                and self._mark_ready()
            )
        except OSError as error:
            self.logger.error("Failed to configure installation: %s", error)
            return False

    def _mark_ready(self) -> bool:
        TEMP_FILES["start_calamares"].touch()
        self.logger.info("Installation configuration completed")
        return True

    def _configure_partition_settings(self) -> bool:
        if not PARTITION_CONF_FILE.exists():
            self.logger.error(
                "Partition config template not found: %s", PARTITION_CONF_FILE
            )
            return False
        destination = CALAMARES_CONFIGS["partition"]
        if not copy_file_safe(PARTITION_CONF_FILE, destination):
            return False
        if self._current_config.filesystem_type != "ext4":
            return True

        content = read_text_file(destination)
        setting = 'defaultFileSystemType:  "btrfs"'
        if content is None or setting not in content:
            self.logger.error("Could not read a valid partition configuration")
            return False
        return write_text_file(
            content.replace(setting, 'defaultFileSystemType:  "ext4"'), destination
        )

    def _configure_unpack_settings(self) -> bool:
        sfs_folder = self.system_service.get_sfs_folder()
        if not sfs_folder:
            self.logger.error("SFS folder not detected")
            return False

        self._current_config.sfs_folder = sfs_folder
        content = f"""---
unpack:
    - source: "/run/miso/bootmnt/{sfs_folder}/x86_64/rootfs.sfs"
      sourcefs: "squashfs"
      destination: ""
    - source: "/run/miso/bootmnt/{sfs_folder}/x86_64/desktopfs.sfs"
      sourcefs: "squashfs"
      destination: ""
"""
        return write_text_file(content, CALAMARES_CONFIGS["unpackfs"])

    def _configure_package_settings(self) -> bool:
        packages = (
            self._current_config.packages_to_remove
            + self._current_config.packages_to_install
        )
        package_pattern = re.compile(r"^[a-z0-9][a-z0-9@._+-]*$")
        if any(not package_pattern.fullmatch(package) for package in packages):
            self.logger.error("Package configuration contains an invalid name")
            return False

        content = """---

backend: pacman

skip_if_no_internet: true
update_db: false
update_system: false

pacman:
    num_retries: 10
    disable_download_timeout: true
    needed_only: true
"""
        if (
            self._current_config.packages_to_remove
            or self._current_config.packages_to_install
        ):
            content += "\noperations:\n"
            if self._current_config.packages_to_remove:
                content += "    - remove:\n"
                content += "".join(
                    f"        - {package}\n"
                    for package in self._current_config.packages_to_remove
                )
            if self._current_config.packages_to_install:
                content += "    - install:\n"
                content += "".join(
                    f"        - {package}\n"
                    for package in self._current_config.packages_to_install
                )
        return write_text_file(content, CALAMARES_CONFIGS["packages"])

    def start_installation(
        self,
        filesystem_type: str = "btrfs",
        packages_to_remove: list[str] | None = None,
    ) -> bool:
        config = InstallationConfig(
            filesystem_type=filesystem_type,
            packages_to_remove=packages_to_remove or [],
        )
        return self.configure_installation(config)

    def start_maintenance_tool(self, tool_name: str) -> bool:
        commands = {
            "grub_restore": ["/usr/bin/biglinux-grub-restore"],
            "timeshift": ["/usr/bin/timeshift-launcher"],
            "efi_manager": ["/usr/bin/bigsudo", "QEFIEntryManager"],
        }
        command = commands.get(tool_name)
        if command is None:
            self.logger.error("Unknown maintenance tool: %s", tool_name)
            return False
        try:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            self.logger.error("Could not start %s: %s", tool_name, error)
            return False
        return True

    def check_installation_requirements(self) -> dict[str, bool]:
        return {
            "config_dir": CALAMARES_CONFIG_DIR.is_dir(),
            "modules_dir": CALAMARES_MODULES_DIR.is_dir(),
            "partition_template": PARTITION_CONF_FILE.is_file(),
            "sfs_detected": bool(self.system_service.get_sfs_folder()),
            "live_mode": self.system_service.is_live_mode(),
        }
