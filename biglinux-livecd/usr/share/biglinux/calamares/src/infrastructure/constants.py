"""Constants shared by the Calamares interface."""

from pathlib import Path

APP_NAME = "BigLinux Calamares Config"
APP_ID = "com.biglinux.calamares-config"
APP_VERSION = "1.3.13"

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"

TEMP_DIR = Path("/run/biglinux-live/calamares")
CALAMARES_CONFIG_DIR = Path("/etc/calamares")
CALAMARES_MODULES_DIR = CALAMARES_CONFIG_DIR / "modules"

ICON_MAPPING_FILE = DATA_DIR / "icon-mapping.json"
MINIMAL_PACKAGES_FILE = DATA_DIR / "minimal-packages.json"
PARTITION_CONF_FILE = DATA_DIR / "partition.conf"
BOOT_MOUNT_DIR = Path("/run/miso/bootmnt")

TEMP_FILES = {
    "wait_install": TEMP_DIR / "biglinux-wait-install",
    "start_calamares": TEMP_DIR / "start_calamares",
    "installed_packages": TEMP_DIR / "big-installed-packages.txt",
    "available_to_remove": TEMP_DIR / "pkgAvailableToRemove.txt",
    "packages_to_remove": TEMP_DIR / "listPkgsRemove",
    "packages_no_remove": TEMP_DIR / "listPkgsNoRemove.txt",
    "package_remove_list": TEMP_DIR / "packageRemove",
    "package_install_list": TEMP_DIR / "packageInstallList",
}

CALAMARES_CONFIGS = {
    "partition": CALAMARES_MODULES_DIR / "partition.conf",
    "packages": CALAMARES_MODULES_DIR / "packages.conf",
    "unpackfs": CALAMARES_MODULES_DIR / "unpackfs.conf",
}

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
