# src/utils/constants.py

"""
Constants and configuration values for BigLinux Calamares Configuration Tool
"""

from pathlib import Path

# Application Information
APP_NAME = "BigLinux Calamares Config"
APP_ID = "com.biglinux.calamares-config"
APP_VERSION = "1.0.0"

# Paths and Directories
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CALAMARES_CONFIG_DIR = Path("/etc/calamares")
CALAMARES_MODULES_DIR = CALAMARES_CONFIG_DIR / "modules"

# Data Files
ICON_MAPPING_FILE = DATA_DIR / "icon-mapping.json"
MINIMAL_PACKAGES_FILE = DATA_DIR / "minimal-packages.json"
PARTITION_CONF_FILE = DATA_DIR / "partition.conf"
NETINSTALL_XIVASTUDIO_CONF = DATA_DIR / "netinstall-xivastudio.conf"
NETINSTALL_XIVASTUDIO_YAML = DATA_DIR / "netinstall-xivastudio.yaml"

# System Paths
BOOT_MOUNT_DIR = Path("/run/miso/bootmnt")
TEMP_DIR = Path("/tmp")

# Temporary Files (used by installation process)
TEMP_FILES = {
    "wait_install": TEMP_DIR / "biglinux-wait-install",
    "start_calamares": TEMP_DIR / "start_calamares",
    "installed_packages": TEMP_DIR / "big-installed-packages.txt",
    "available_to_remove": TEMP_DIR / "pkgAvaliableToRemove.txt",
    "packages_to_remove": TEMP_DIR / "listPkgsRemove",
    "packages_no_remove": TEMP_DIR / "listPkgsNoRemove.txt",
    "package_remove_list": TEMP_DIR / "packageRemove",
    "package_install_list": TEMP_DIR / "packageInstallList",
}

# System Commands
COMMANDS = {
    "pacman_query": "pacman -Qq",
    "pacman_check": "pacman -Q",
    "geticons": "geticons -s 48",
    "uname_kernel": "uname -r | cut -f1 -d-",
    "efi_check": "[ -d /sys/firmware/efi ]",
    "grub_restore": "biglinux-grub-restore",
    "timeshift": "timeshift-launcher",
    "efi_manager": "qefientrymanager-launcher",
    "calamares": "calamares",
}

# File System Types
FILESYSTEM_TYPES = {"btrfs": "btrfs", "ext4": "ext4"}

# Default Settings
DEFAULTS = {
    "filesystem": "btrfs",
    "swap_choice": "none",
    "partition_table": "gpt",
    "efi_partition": "/boot/efi",
    "icon_size": 48,
    "window_width": 1080,
    "window_height": 640,
    "min_window_width": 600,
    "min_window_height": 400,
}

# Installation Options
INSTALLATION_OPTIONS = {
    "btrfs": {
        "filesystem": "btrfs",
        "config_source": PARTITION_CONF_FILE,
    },
    "ext4": {
        "filesystem": "ext4",
        "config_source": PARTITION_CONF_FILE,
    },
}

# Calamares Configuration Files
CALAMARES_CONFIGS = {
    "settings": CALAMARES_CONFIG_DIR / "settings.conf",
    "partition": CALAMARES_MODULES_DIR / "partition.conf",
    "packages": CALAMARES_MODULES_DIR / "packages.conf",
    "unpackfs": CALAMARES_MODULES_DIR / "unpackfs.conf",
    "shellprocess_pacman": CALAMARES_MODULES_DIR
    / "shellprocess_initialize_pacman.conf",
    "shellprocess_display": CALAMARES_MODULES_DIR
    / "shellprocess_displaymanager_biglinux.conf",
}

# System Detection Patterns
SYSTEM_PATTERNS = {
    "sfs_folders": ["manjaro", "$HOSTNAME"],
    "sfs_exclude": ["/efi/", "/boot/"],
    "boot_modes": {"uefi": "UEFI", "bios": "BIOS (Legacy)"},
    "session_types": {"wayland": "Wayland", "x11": "X11"},
}

# Package Categories (for future netinstall support)
PACKAGE_CATEGORIES = {
    "image": {
        "name": "Image Editing",
        "packages": ["gimp", "inkscape", "krita", "darktable"],
    },
    "video": {
        "name": "Video Editing",
        "packages": ["kdenlive", "shotcut", "blender", "obs-studio"],
    },
    "audio": {
        "name": "Audio Production",
        "packages": ["audacity", "ardour", "lmms", "musescore"],
    },
    "cad": {
        "name": "3D & CAD",
        "packages": ["freecad", "blender", "openscad", "librecad"],
    },
    "browser": {
        "name": "Web Browsers",
        "packages": ["brave-browser", "firefox", "chromium", "vivaldi"],
    },
}

# UI Settings
UI_SETTINGS = {
    "transition_duration": 300,
    "toast_timeout": 3,
    "error_toast_timeout": 5,
    "grid_spacing": 24,
    "margin_size": 24,
    "icon_size": 64,
}

# Error Messages
ERROR_MESSAGES = {
    "missing_dependencies": "Required system dependencies are missing: {deps}",
    "file_not_found": "Required file not found: {file}",
    "permission_denied": "Permission denied accessing: {path}",
    "command_failed": "Command failed: {command}",
    "invalid_filesystem": "Invalid filesystem type: {fs_type}",
    "calamares_config_failed": "Failed to configure Calamares: {error}",
}

# Success Messages
SUCCESS_MESSAGES = {
    "packages_updated": "Package selection updated successfully",
    "config_saved": "Configuration saved successfully",
    "installation_started": "Installation process started",
    "backup_completed": "System backup completed",
}

# URLs and Links
URLS = {
    "forum": "https://forum.biglinux.com.br",
    "website": "https://www.biglinux.com.br",
    "documentation": "https://github.com/biglinux/biglinux-calamares-config/wiki",
    "issues": "https://github.com/biglinux/biglinux-calamares-config/issues",
}

# Debug Settings
DEBUG = {"log_commands": True, "save_temp_files": False, "verbose_logging": True}
