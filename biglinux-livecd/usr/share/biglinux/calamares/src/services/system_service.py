# src/services/system_service.py

"""
System Service for BigLinux Calamares Configuration Tool
Handles system detection and information gathering
"""

import os
import logging
from pathlib import Path
from typing import Optional
from ..utils import _, get_command_output, check_command_exists, COMMANDS


class SystemService:
    """Service for system information detection and management"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._system_info = {}
        self._is_initialized = False

    def initialize(self):
        """Initialize the system service"""
        if self._is_initialized:
            return

        self.logger.info("Initializing SystemService")
        self._detect_system_info()
        self._is_initialized = True
        self.logger.info("SystemService initialized successfully")

    def cleanup(self):
        """Cleanup system service resources"""
        self.logger.info("Cleaning up SystemService")
        self._system_info.clear()
        self._is_initialized = False

    def _is_efi_available(self) -> bool:
        """Directly check if the system has an EFI directory."""
        try:
            return Path("/sys/firmware/efi").is_dir()
        except Exception:
            return False

    def _detect_system_info(self):
        """Detect and cache system information"""
        self.logger.debug("Detecting system information")

        is_efi = self._is_efi_available()

        self.logger.info(f"EFI available: {is_efi}")

        self._system_info = {
            "boot_mode": "UEFI" if is_efi else "BIOS (Legacy)",
            "kernel_version": self._detect_kernel_version(),
            "session_type": self._detect_session_type(),
            "architecture": self._detect_architecture(),
            "hostname": self._detect_hostname(),
            "live_mode": self._detect_live_mode(),
            "efi_available": is_efi,
            "sfs_folder": self._detect_sfs_folder(),
        }

        self.logger.info(f"System detected: {self._system_info}")

    def _detect_kernel_version(self) -> str:
        """Detect kernel version"""
        try:
            full_version = get_command_output("uname -r")
            return full_version.split("-")[0] if full_version else "Unknown"
        except Exception as e:
            self.logger.warning(f"Failed to detect kernel version: {e}")
            return "Unknown"

    def _detect_session_type(self) -> str:
        """Detect graphical session type"""
        try:
            session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
            return session_type.title() if session_type else "Unknown"
        except Exception as e:
            self.logger.warning(f"Failed to detect session type: {e}")
            return "Unknown"

    def _detect_architecture(self) -> str:
        """Detect system architecture"""
        try:
            return get_command_output("uname -m") or "Unknown"
        except Exception as e:
            self.logger.warning(f"Failed to detect architecture: {e}")
            return "Unknown"

    def _detect_hostname(self) -> str:
        """Detect system hostname"""
        try:
            return (
                os.environ.get("HOSTNAME")
                or get_command_output("hostname")
                or "Unknown"
            )
        except Exception as e:
            self.logger.warning(f"Failed to detect hostname: {e}")
            return "Unknown"

    def _detect_live_mode(self) -> bool:
        """Detect if system is running in live mode"""
        try:
            return Path("/run/miso").exists() or Path("/live").exists()
        except Exception as e:
            self.logger.warning(f"Failed to detect live mode: {e}")
            return False

    def _detect_sfs_folder(self) -> Optional[str]:
        """Detect SFS folder for live system"""
        try:
            boot_mount = Path("/run/miso/bootmnt")
            if not boot_mount.exists():
                return None

            for item in boot_mount.iterdir():
                if (
                    item.is_dir()
                    and item.name not in ["efi", "boot"]
                    and (item / "x86_64").exists()
                ):
                    return item.name
            return None
        except Exception as e:
            self.logger.warning(f"Failed to detect SFS folder: {e}")
            return None

    def get_boot_mode(self) -> str:
        return self._system_info.get("boot_mode", "Unknown")

    def get_kernel_version(self) -> str:
        return self._system_info.get("kernel_version", "Unknown")

    def get_session_type(self) -> str:
        return self._system_info.get("session_type", "Unknown")

    def is_live_mode(self) -> bool:
        return self._system_info.get("live_mode", False)

    def is_efi_system(self) -> bool:
        return self._system_info.get("efi_available", False)

    def get_sfs_folder(self) -> Optional[str]:
        return self._system_info.get("sfs_folder")

    def get_efi_manager_command(self) -> Optional[str]:
        """Get the command to manage EFI entries if available."""
        command_name = COMMANDS.get("efi_manager")
        if command_name and check_command_exists(command_name):
            return command_name
        return None

    def can_manage_efi_entries(self) -> bool:
        """Check if EFI entries can be managed."""
        return self.is_efi_system() and self.get_efi_manager_command() is not None

    def get_system_summary(self) -> str:
        boot_mode = self.get_boot_mode()
        kernel = self.get_kernel_version()
        session = self.get_session_type()
        return f"{_('The system is in')} {boot_mode}, Linux {kernel} {_('and graphical mode')} {session}."
