"""
Utilities package for BigLinux Calamares Configuration Tool
Provides common functionality used across the application
"""

# Import translation function
# Import constants
from .constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    CALAMARES_CONFIG_DIR,
    CALAMARES_CONFIGS,
    CALAMARES_MODULES_DIR,
    COMMANDS,
    DATA_DIR,
    DEFAULTS,
    ERROR_MESSAGES,
    ICON_MAPPING_FILE,
    MINIMAL_PACKAGES_FILE,
    NETINSTALL_XIVASTUDIO_CONF,
    NETINSTALL_XIVASTUDIO_YAML,
    PARTITION_CONF_FILE,
    SUCCESS_MESSAGES,
    TEMP_FILES,
    UI_SETTINGS,
)

# Import helper functions
from .helpers import (
    cleanup_temp_files,
    copy_file_safe,
    ensure_directory,
    file_exists,
    format_package_list,
    human_readable_size,
    load_json_file,
    parse_package_list,
    read_text_file,
    save_json_file,
    truncate_text,
    validate_package_name,
    write_text_file,
)
from .i18n import _, setup_i18n

# Import shell execution utilities
from .shell import (
    CommandResult,
    ShellExecutor,
    check_command_exists,
    check_package_installed,
    cleanup_shell_resources,
    execute_command,
    execute_command_async,
    get_command_output,
    get_package_icon,
    get_system_info,
    pacman_query_installed,
    run_command_simple,
)

# Package metadata
__version__ = APP_VERSION
__author__ = "BigLinux Team"
__email__ = "contact@biglinux.com.br"

# Expose main utilities for easy importing
__all__ = [
    # Translation
    "_",
    "setup_i18n",
    # Constants (most commonly used)
    "APP_NAME",
    "APP_ID",
    "APP_VERSION",
    "DATA_DIR",
    "CALAMARES_CONFIG_DIR",
    "CALAMARES_MODULES_DIR",
    "ICON_MAPPING_FILE",
    "MINIMAL_PACKAGES_FILE",
    "PARTITION_CONF_FILE",
    "NETINSTALL_XIVASTUDIO_CONF",
    "NETINSTALL_XIVASTUDIO_YAML",
    "CALAMARES_CONFIGS",
    "UI_SETTINGS",
    "COMMANDS",
    "DEFAULTS",
    "ERROR_MESSAGES",
    "SUCCESS_MESSAGES",
    # Helper functions
    "load_json_file",
    "save_json_file",
    "ensure_directory",
    "file_exists",
    "copy_file_safe",
    "write_text_file",
    "read_text_file",
    "parse_package_list",
    "format_package_list",
    "human_readable_size",
    "cleanup_temp_files",
    "validate_package_name",
    "truncate_text",
    # Shell utilities
    "CommandResult",
    "ShellExecutor",
    "execute_command",
    "execute_command_async",
    "check_command_exists",
    "get_command_output",
    "run_command_simple",
    "cleanup_shell_resources",
    "pacman_query_installed",
    "check_package_installed",
    "get_system_info",
    "get_package_icon",
]


def initialize_utils():
    """Initialize utilities package - call this at application startup"""
    # Setup translations
    setup_i18n()

    # Ensure required directories exist
    ensure_directory(DATA_DIR)

    # Log initialization
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Utils package initialized")


def cleanup_utils():
    """Cleanup utilities package - call this at application shutdown"""
    # Cleanup shell resources
    cleanup_shell_resources()

    # Cleanup any temporary files if needed
    temp_file_list = list(TEMP_FILES.values())
    cleanup_temp_files(temp_file_list)

    # Log cleanup
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Utils package cleaned up")
