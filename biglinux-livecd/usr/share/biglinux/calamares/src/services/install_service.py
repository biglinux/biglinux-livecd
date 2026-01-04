# src/services/install_service.py

"""
Install Service for BigLinux Calamares Configuration Tool
Handles Calamares configuration and installation process
"""

import logging
import subprocess
from typing import Any, Dict, List

from ..utils import (
    CALAMARES_CONFIG_DIR,
    CALAMARES_CONFIGS,
    CALAMARES_MODULES_DIR,
    COMMANDS,
    NETINSTALL_XIVASTUDIO_CONF,
    NETINSTALL_XIVASTUDIO_YAML,
    PARTITION_CONF_FILE,
    TEMP_FILES,
    copy_file_safe,
    ensure_directory,
    read_text_file,
    write_text_file,
)


class InstallationConfig:
    """Configuration for Calamares installation"""

    def __init__(self):
        self.filesystem_type = "btrfs"
        self.packages_to_remove = []
        self.packages_to_install = []
        self.custom_desktop = False
        self.login_manager = ""
        self.use_minimal = False
        self.sfs_folder = ""
        self.enable_xivastudio_netinstall = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "filesystem_type": self.filesystem_type,
            "packages_to_remove": self.packages_to_remove,
            "packages_to_install": self.packages_to_install,
            "custom_desktop": self.custom_desktop,
            "login_manager": self.login_manager,
            "use_minimal": self.use_minimal,
            "sfs_folder": self.sfs_folder,
            "enable_xivastudio_netinstall": self.enable_xivastudio_netinstall,
        }


class InstallService:
    """Service for installation configuration and process management"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._current_config = InstallationConfig()
        self._is_initialized = False

    def initialize(self):
        """Initialize the install service"""
        if self._is_initialized:
            return

        self.logger.info("Initializing InstallService")
        self._ensure_directories()
        self._is_initialized = True
        self.logger.info("InstallService initialized successfully")

    def cleanup(self):
        """Cleanup install service resources"""
        self.logger.info("Cleaning up InstallService")
        self._cleanup_temp_files()
        self._is_initialized = False

    def _ensure_directories(self):
        """Ensure required directories exist"""
        ensure_directory(CALAMARES_CONFIG_DIR)
        ensure_directory(CALAMARES_MODULES_DIR)

    def _cleanup_temp_files(self):
        """Clean up temporary installation files"""
        temp_files = [TEMP_FILES["wait_install"], TEMP_FILES["start_calamares"]]

        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")

    def configure_installation(self, config: InstallationConfig) -> bool:
        """
        Configure Calamares for installation

        Args:
            config: Installation configuration

        Returns:
            True if configuration was successful
        """
        self.logger.info(f"Configuring installation with: {config.to_dict()}")
        self._current_config = config

        try:
            # Create wait file
            TEMP_FILES["wait_install"].touch()

            # Remove old start file
            if TEMP_FILES["start_calamares"].exists():
                TEMP_FILES["start_calamares"].unlink()

            # Configure partition settings
            if not self._configure_partition_settings():
                return False

            # Configure unpack settings
            if not self._configure_unpack_settings():
                return False

            # Configure package settings if needed (for minimal, explicit packages, or netinstall)
            if config.packages_to_remove or config.use_minimal or config.enable_xivastudio_netinstall:
                if not self._configure_package_settings():
                    return False

            # Configure main settings
            if not self._configure_main_settings():
                return False

            # Configure shell processes
            if not self._configure_shell_processes():
                return False

            # Create start file to signal configuration complete
            TEMP_FILES["start_calamares"].touch()

            self.logger.info("Installation configuration completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure installation: {e}")
            return False

    def _configure_partition_settings(self) -> bool:
        """Configure partition.conf for Calamares"""
        try:
            source_config = PARTITION_CONF_FILE

            if not source_config.exists():
                self.logger.error(
                    f"Partition config template not found: {source_config}"
                )
                return False

            # Copy base configuration
            if not copy_file_safe(source_config, CALAMARES_CONFIGS["partition"]):
                return False

            # Modify for ext4 if needed
            if self._current_config.filesystem_type == "ext4":
                config_content = read_text_file(CALAMARES_CONFIGS["partition"])
                if config_content:
                    # Replace default filesystem type
                    modified_content = config_content.replace(
                        'defaultFileSystemType:  "btrfs"',
                        'defaultFileSystemType:  "ext4"',
                    )
                    write_text_file(modified_content, CALAMARES_CONFIGS["partition"])

            self.logger.debug("Partition configuration completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure partition settings: {e}")
            return False

    def _configure_unpack_settings(self) -> bool:
        """Configure unpackfs.conf for Calamares"""
        try:
            # Get SFS folder from system service
            from . import get_system_service

            system_service = get_system_service()
            sfs_folder = system_service.get_sfs_folder()

            if not sfs_folder:
                self.logger.error("SFS folder not detected")
                return False

            self._current_config.sfs_folder = sfs_folder

            # Create unpack configuration
            config_content = f"""---
unpack:
    - source: "/run/miso/bootmnt/{sfs_folder}/x86_64/rootfs.sfs"
      sourcefs: "squashfs"
      destination: ""
"""

            # Add desktop SFS if not using custom desktop
            if not self._current_config.custom_desktop:
                config_content += f"""    - source: "/run/miso/bootmnt/{sfs_folder}/x86_64/desktopfs.sfs"
      sourcefs: "squashfs"
      destination: ""
"""

            write_text_file(config_content, CALAMARES_CONFIGS["unpackfs"])
            self.logger.debug("Unpack configuration completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure unpack settings: {e}")
            return False

    def _configure_package_settings(self) -> bool:
        """Configure packages.conf for Calamares"""
        try:
            packages_to_remove = self._current_config.packages_to_remove
            packages_to_install = self._current_config.packages_to_install

            # Base configuration - always create if netinstall is enabled
            config_content = """---

backend: pacman

skip_if_no_internet: false
update_db: true
update_system: true

pacman:
    num_retries: 10
    disable_download_timeout: true
    needed_only: true
"""

            # Add operations section only if there are packages to manage
            if packages_to_remove or packages_to_install:
                config_content += """
operations:
"""

                # Add remove operations
                if packages_to_remove:
                    config_content += "    - remove:\n"
                    for package in packages_to_remove:
                        config_content += f"        - {package}\n"

                # Add install operations
                if packages_to_install:
                    config_content += "    - install:\n"
                    for package in packages_to_install:
                        config_content += f"        - {package}\n"

            write_text_file(config_content, CALAMARES_CONFIGS["packages"])
            self.logger.debug("Package configuration completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure package settings: {e}")
            return False

    def _configure_main_settings(self) -> bool:
        """Configure main settings.conf for Calamares"""
        try:
            # Build instances block
            instances_block = """
- id:       initialize_pacman
  module:   shellprocess
  config:   shellprocess_initialize_pacman.conf

- id:       displaymanager_biglinux
  module:   shellprocess
  config:   shellprocess_displaymanager_biglinux.conf
"""

            # Add XivaStudio netinstall instance if enabled
            if self._current_config.enable_xivastudio_netinstall:
                instances_block += """
- id:       xivastudio
  module:   netinstall
  config:   netinstall-xivastudio.conf
"""

            # Build show sequence
            show_sequence = """    - show:
        - welcome
        - locale
        - keyboard
        - partition"""

            # Add netinstall@xivastudio to show sequence if enabled
            if self._current_config.enable_xivastudio_netinstall:
                show_sequence += """
        - netinstall@xivastudio"""

            show_sequence += """
        - users
        - summary"""

            config_content = f"""---
modules-search: [ local ]

instances:
{instances_block}
sequence:
{show_sequence}
    - exec:
        - partition
        - mount
        - unpackfs
        - networkcfg
        - machineid
        - fstab
        - locale
        - keyboard
"""

            # Add package operations if needed (for netinstall, minimal, or explicit packages)
            if (
                self._current_config.packages_to_remove
                or self._current_config.packages_to_install
                or self._current_config.use_minimal
                or self._current_config.enable_xivastudio_netinstall
            ):
                config_content += """        - shellprocess@initialize_pacman
        - packages
"""

            # Add display manager configuration if custom desktop
            if (
                self._current_config.custom_desktop
                and self._current_config.login_manager
            ):
                config_content += "        - shellprocess@displaymanager_biglinux\n"

            # Add remaining steps
            config_content += """        - localecfg
        - luksopenswaphookcfg
        - luksbootkeyfile
        - initcpiocfg
        - initcpio
        - users
        - displaymanager
        - mhwdcfg
        - hwclock
        - services
        - grubcfg
        - grubcfg-fix
        - bootloader
        - postcfg
        - btrfs-fix
        - umount
    - show:
        - finished

branding: biglinux

prompt-install: true

dont-chroot: false
oem-setup: false
disable-cancel: false
disable-cancel-during-exec: false
quit-at-end: false
"""

            write_text_file(config_content, CALAMARES_CONFIGS["settings"])
            self.logger.debug("Main settings configuration completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure main settings: {e}")
            return False

    def _configure_shell_processes(self) -> bool:
        """Configure shell process modules"""
        try:
            # Configure pacman initialization
            pacman_config = """---

dontChroot: false

script:
    - "pacman-key --init"
    - command: "pacman-key --populate archlinux manjaro biglinux"
      timeout: 1200

i18n:
    name: "Init pacman-key"
"""
            write_text_file(pacman_config, CALAMARES_CONFIGS["shellprocess_pacman"])

            # Configure display manager if needed
            if self._current_config.login_manager:
                display_config = f"""---

dontChroot: false

script:
    - "systemctl enable {self._current_config.login_manager}"

i18n:
    name: "Enable login manager"
"""
                write_text_file(
                    display_config, CALAMARES_CONFIGS["shellprocess_display"]
                )

            self.logger.debug("Shell process configuration completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure shell processes: {e}")
            return False

    def start_installation(
        self, filesystem_type: str = "btrfs", packages_to_remove: List[str] = None
    ) -> bool:
        """
        Configure the installation process without launching Calamares.

        Args:
            filesystem_type: Type of filesystem (btrfs or ext4)
            packages_to_remove: List of packages to remove

        Returns:
            True if installation was configured successfully
        """
        try:
            # Prepare configuration (preserve netinstall flag if already set)
            enable_netinstall = self._current_config.enable_xivastudio_netinstall
            
            config = InstallationConfig()
            config.filesystem_type = filesystem_type
            config.packages_to_remove = packages_to_remove or []
            config.use_minimal = bool(packages_to_remove)
            config.enable_xivastudio_netinstall = enable_netinstall

            # Configure Calamares
            if not self.configure_installation(config):
                return False
            
            self.logger.info("Installation configured successfully. Calamares can be launched externally.")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start installation: {e}")
            return False

    def start_maintenance_tool(self, tool_name: str) -> bool:
        """
        Start a maintenance tool without blocking (fire-and-forget).

        Args:
            tool_name: Name of the maintenance tool to launch.

        Returns:
            True if the tool was spawned successfully, False otherwise.
        """
        tools = {
            "grub_restore": COMMANDS["grub_restore"],
            "timeshift": COMMANDS["timeshift"],
            "efi_manager": COMMANDS["efi_manager"],
        }

        if tool_name not in tools:
            self.logger.error(f"Unknown maintenance tool: {tool_name}")
            return False

        command = tools[tool_name]
        try:
            self.logger.info(f"Spawning maintenance tool: {command}")
            # Use Popen to launch the process without waiting for it to complete.
            # This makes the UI feel responsive and delegates the tool's lifecycle
            # to the window manager.
            # stdout, stderr, and stdin are redirected to DEVNULL to fully detach.
            subprocess.Popen(
                command.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            return True

        except FileNotFoundError:
            self.logger.error(f"Command not found for tool '{tool_name}': {command}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to spawn maintenance tool {tool_name}: {e}")
            return False

    def get_installation_status(self) -> Dict[str, Any]:
        """
        Get current installation status

        Returns:
            Dictionary with installation status information
        """
        status = {
            "configured": TEMP_FILES["start_calamares"].exists(),
            "in_progress": TEMP_FILES["wait_install"].exists(),
            "config": self._current_config.to_dict(),
        }

        return status

    def check_installation_requirements(self) -> Dict[str, bool]:
        """
        Check installation requirements

        Returns:
            Dictionary with requirement check results
        """
        requirements = {}

        # Check required directories
        requirements["config_dir"] = CALAMARES_CONFIG_DIR.exists()
        requirements["modules_dir"] = CALAMARES_MODULES_DIR.exists()

        # Check partition config template
        requirements["partition_template"] = PARTITION_CONF_FILE.exists()

        # Check system requirements
        from . import get_system_service

        system_service = get_system_service()
        requirements["sfs_detected"] = system_service.get_sfs_folder() is not None
        requirements["live_mode"] = system_service.is_live_mode()

        return requirements

    def get_current_config(self) -> InstallationConfig:
        """Get current installation configuration"""
        return self._current_config

    def configure_xivastudio_netinstall(self) -> bool:
        """
        Prepare XivaStudio netinstall configuration files.

        This should only be called when:
        1. System is detected as XivaStudio
        2. Internet connection is available

        The method copies the required configuration files to the
        Calamares modules directory. The actual settings.conf modification
        is handled by _configure_main_settings() when enable_xivastudio_netinstall
        is True.

        Returns:
            True if configuration files were copied successfully, False otherwise
        """
        self.logger.info("Preparing XivaStudio netinstall configuration files...")

        try:
            # Verify netinstall config files exist
            if not NETINSTALL_XIVASTUDIO_CONF.exists():
                self.logger.error(
                    f"XivaStudio netinstall config not found: {NETINSTALL_XIVASTUDIO_CONF}"
                )
                return False

            if not NETINSTALL_XIVASTUDIO_YAML.exists():
                self.logger.error(
                    f"XivaStudio netinstall YAML not found: {NETINSTALL_XIVASTUDIO_YAML}"
                )
                return False

            # Copy netinstall configuration files to Calamares modules directory
            netinstall_conf_dest = CALAMARES_MODULES_DIR / "netinstall-xivastudio.conf"
            netinstall_yaml_dest = CALAMARES_MODULES_DIR / "netinstall-xivastudio.yaml"

            if not copy_file_safe(NETINSTALL_XIVASTUDIO_CONF, netinstall_conf_dest):
                self.logger.error("Failed to copy netinstall config")
                return False

            if not copy_file_safe(NETINSTALL_XIVASTUDIO_YAML, netinstall_yaml_dest):
                self.logger.error("Failed to copy netinstall YAML")
                return False

            # Set the flag to enable netinstall in the configuration
            self._current_config.enable_xivastudio_netinstall = True

            self.logger.info("XivaStudio netinstall files prepared successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to prepare XivaStudio netinstall: {e}")
            return False

    def check_internet_connection(self) -> bool:
        """
        Check if internet connection is available by running pacman -Sy.

        Returns:
            True if internet is available, False otherwise
        """
        self.logger.info("Checking internet connection via pacman -Sy...")

        try:
            result = subprocess.run(
                ["sudo", "pacman", "-Sy"], capture_output=True, timeout=60
            )

            if result.returncode == 0:
                self.logger.info("Internet connection available")
                return True
            else:
                self.logger.warning("pacman -Sy failed - no internet connection")
                return False

        except subprocess.TimeoutExpired:
            self.logger.warning("pacman -Sy timed out - no internet connection")
            return False
        except Exception as e:
            self.logger.error(f"Failed to check internet connection: {e}")
            return False

    def reset_configuration(self):
        """Reset installation configuration to defaults"""
        self.logger.info("Resetting installation configuration")
        self._current_config = InstallationConfig()
        self._cleanup_temp_files()
