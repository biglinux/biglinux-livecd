"""Shared paths and small file/command helpers for the installer UI."""

from .constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    CALAMARES_CONFIG_DIR,
    CALAMARES_CONFIGS,
    CALAMARES_MODULES_DIR,
    DATA_DIR,
    DEFAULTS,
    ICON_MAPPING_FILE,
    MINIMAL_PACKAGES_FILE,
    PARTITION_CONF_FILE,
    TEMP_FILES,
)
from .file_operations import (
    copy_file_safe,
    ensure_directory,
    load_json_file,
    read_text_file,
    validate_package_name,
    write_text_file,
)
from .i18n import _
from .subprocesses import get_command_output, pacman_query_installed

__all__ = [
    "_",
    "APP_NAME",
    "APP_ID",
    "APP_VERSION",
    "DATA_DIR",
    "CALAMARES_CONFIG_DIR",
    "CALAMARES_MODULES_DIR",
    "ICON_MAPPING_FILE",
    "MINIMAL_PACKAGES_FILE",
    "PARTITION_CONF_FILE",
    "CALAMARES_CONFIGS",
    "DEFAULTS",
    "TEMP_FILES",
    "load_json_file",
    "ensure_directory",
    "copy_file_safe",
    "write_text_file",
    "read_text_file",
    "validate_package_name",
    "get_command_output",
    "pacman_query_installed",
]
