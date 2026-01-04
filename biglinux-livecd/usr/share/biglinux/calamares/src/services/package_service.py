"""
Package Service for BigLinux Calamares Configuration Tool
Handles package management, icon mapping, and package selection
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..utils import (
    load_json_file,
    pacman_query_installed,
    validate_package_name,
    ICON_MAPPING_FILE,
    MINIMAL_PACKAGES_FILE,
    TEMP_FILES,
)


class Package:
    """Represents a package with its metadata"""

    def __init__(
        self,
        name: str,
        icon: Optional[str] = None,
        installed: bool = False,
        selected: bool = True,
    ):
        self.name = name
        self.icon = icon or name  # Fallback to package name
        self.installed = installed
        self.selected = selected
        self.description = ""
        self.size = 0

    def __repr__(self):
        return f"Package(name='{self.name}', installed={self.installed}, selected={self.selected})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert package to dictionary"""
        return {
            "name": self.name,
            "icon": self.icon,
            "installed": self.installed,
            "selected": self.selected,
            "description": self.description,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Package":
        """Create package from dictionary"""
        pkg = cls(
            name=data.get("name", ""),
            icon=data.get("icon"),
            installed=data.get("installed", False),
            selected=data.get("selected", True),
        )
        pkg.description = data.get("description", "")
        pkg.size = data.get("size", 0)
        return pkg


class PackageService:
    """Service for package management operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._icon_mapping = {}
        self._minimal_packages = []
        self._installed_packages = set()
        self._package_cache = {}
        self._is_initialized = False

    def initialize(self):
        """Initialize the package service"""
        if self._is_initialized:
            return

        self.logger.info("Initializing PackageService")

        # Load configuration files
        self._load_icon_mapping()
        self._load_minimal_packages()
        self._refresh_installed_packages()

        self._is_initialized = True
        self.logger.info("PackageService initialized successfully")

    def cleanup(self):
        """Cleanup package service resources"""
        self.logger.info("Cleaning up PackageService")
        self._icon_mapping.clear()
        self._minimal_packages.clear()
        self._installed_packages.clear()
        self._package_cache.clear()
        self._is_initialized = False

    def _load_icon_mapping(self):
        """Load icon mapping from JSON file"""
        try:
            data = load_json_file(ICON_MAPPING_FILE)
            if data:
                self._icon_mapping = data
                self.logger.debug(f"Loaded {len(self._icon_mapping)} icon mappings")
            else:
                self.logger.warning("Icon mapping file not found or empty")
                self._icon_mapping = {}
        except Exception as e:
            self.logger.error(f"Failed to load icon mapping: {e}")
            self._icon_mapping = {}

    def _load_minimal_packages(self):
        """Load minimal packages list from JSON file"""
        try:
            data = load_json_file(MINIMAL_PACKAGES_FILE)
            if data and "packages" in data:
                self._minimal_packages = data["packages"]
                self.logger.debug(
                    f"Loaded {len(self._minimal_packages)} minimal packages"
                )
            else:
                self.logger.warning("Minimal packages file not found or invalid format")
                self._minimal_packages = []
        except Exception as e:
            self.logger.error(f"Failed to load minimal packages: {e}")
            self._minimal_packages = []

    def _refresh_installed_packages(self):
        """Refresh list of installed packages"""
        try:
            installed_list = pacman_query_installed()
            self._installed_packages = set(installed_list)

            # Save to temp file (used by installation process)
            temp_file = TEMP_FILES["installed_packages"]
            with open(temp_file, "w") as f:
                f.write("\n".join(installed_list))

            self.logger.debug(
                f"Found {len(self._installed_packages)} installed packages"
            )

        except Exception as e:
            self.logger.error(f"Failed to refresh installed packages: {e}")
            self._installed_packages = set()

    def get_package_icon_path(self, package_name: str) -> Optional[str]:
        """
        Get icon name for a package.

        Args:
            package_name: Name of the package

        Returns:
            Icon name for GTK IconTheme lookup
        """
        try:
            # Check icon mapping first - this maps package names to icon names
            mapped_icon = self._icon_mapping.get(package_name, package_name)
            self.logger.debug(f"Icon for '{package_name}': mapped to '{mapped_icon}'")
            return mapped_icon

        except Exception as e:
            self.logger.warning(f"Failed to get icon for package {package_name}: {e}")
            return package_name  # Return package name as icon name fallback

    def is_package_installed(self, package_name: str) -> bool:
        """
        Check if a package is installed

        Args:
            package_name: Name of the package

        Returns:
            True if package is installed
        """
        return package_name in self._installed_packages

    def get_minimal_packages(self) -> List[Package]:
        """
        Get list of minimal packages that can be removed

        Returns:
            List of Package objects
        """
        packages = []

        for pkg_name in self._minimal_packages:
            if not validate_package_name(pkg_name):
                self.logger.warning(f"Invalid package name: {pkg_name}")
                continue

            # Only include if package is actually installed
            if self.is_package_installed(pkg_name):
                icon_path = self.get_package_icon_path(pkg_name)

                package = Package(
                    name=pkg_name,
                    icon=icon_path,
                    installed=True,
                    selected=True,  # Default selected for removal
                )

                packages.append(package)

        # Save available packages to temp file (used by installation process)
        available_packages = [pkg.name for pkg in packages]
        temp_file = TEMP_FILES["available_to_remove"]
        with open(temp_file, "w") as f:
            f.write("\n".join(available_packages))

        self.logger.info(f"Found {len(packages)} removable packages")
        return packages

    def get_packages_for_removal(self, selected_packages: List[str]) -> List[str]:
        """
        Get list of packages marked for removal

        Args:
            selected_packages: List of selected package names

        Returns:
            List of package names to remove
        """
        # Filter only valid and installed packages
        packages_to_remove = []

        for pkg_name in selected_packages:
            if (
                validate_package_name(pkg_name)
                and self.is_package_installed(pkg_name)
                and pkg_name in self._minimal_packages
            ):
                packages_to_remove.append(pkg_name)

        # Save to temp file for installation process
        temp_file = TEMP_FILES["packages_to_remove"]
        with open(temp_file, "w") as f:
            f.write("\n".join(packages_to_remove))

        self.logger.info(f"Prepared {len(packages_to_remove)} packages for removal")
        return packages_to_remove

    def create_package_removal_config(self, packages_to_remove: List[str]) -> bool:
        """
        Create Calamares package removal configuration

        Args:
            packages_to_remove: List of package names to remove

        Returns:
            True if config was created successfully
        """
        try:
            if not packages_to_remove:
                self.logger.info("No packages to remove, skipping config creation")
                return True

            # Create packages.conf content for Calamares
            config_content = """---

backend: pacman

skip_if_no_internet: false
update_db: false
update_system: false

pacman:
    num_retries: 0
    disable_download_timeout: false
    needed_only: false

operations:
    - remove:
        - --cascade
"""

            # Add each package to remove
            for pkg in packages_to_remove:
                config_content += f"        - {pkg}\n"

            # Write to Calamares modules directory
            config_file = Path("/etc/calamares/modules/packages.conf")
            with open(config_file, "w") as f:
                f.write(config_content)

            self.logger.info(
                f"Created package removal config with {len(packages_to_remove)} packages"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to create package removal config: {e}")
            return False

    def refresh_package_data(self):
        """Refresh all package data"""
        self.logger.info("Refreshing package data")
        self._refresh_installed_packages()

        # Clear package cache to force reload
        self._package_cache.clear()

    def get_package_info(self, package_name: str) -> Optional[Package]:
        """
        Get detailed package information

        Args:
            package_name: Name of the package

        Returns:
            Package object or None
        """
        if package_name in self._package_cache:
            return self._package_cache[package_name]

        try:
            icon_path = self.get_package_icon_path(package_name)
            installed = self.is_package_installed(package_name)

            package = Package(
                name=package_name, icon=icon_path, installed=installed, selected=True
            )

            # Cache the package info
            self._package_cache[package_name] = package
            return package

        except Exception as e:
            self.logger.error(f"Failed to get package info for {package_name}: {e}")
            return None

    def search_packages(self, query: str) -> List[Package]:
        """
        Search for packages by name

        Args:
            query: Search query

        Returns:
            List of matching packages
        """
        if not query:
            return []

        query = query.lower()
        matches = []

        # Search in minimal packages
        for pkg_name in self._minimal_packages:
            if query in pkg_name.lower():
                package = self.get_package_info(pkg_name)
                if package:
                    matches.append(package)

        return matches

    def get_package_statistics(self) -> Dict[str, int]:
        """
        Get package statistics

        Returns:
            Dictionary with package counts
        """
        minimal_packages = self.get_minimal_packages()

        return {
            "total_installed": len(self._installed_packages),
            "minimal_packages": len(self._minimal_packages),
            "removable_packages": len(minimal_packages),
            "selected_for_removal": sum(1 for pkg in minimal_packages if pkg.selected),
        }

    def validate_package_selection(
        self, selected_packages: List[str]
    ) -> Dict[str, List[str]]:
        """
        Validate package selection

        Args:
            selected_packages: List of selected package names

        Returns:
            Dictionary with validation results
        """
        valid = []
        invalid = []
        not_installed = []
        not_removable = []

        for pkg_name in selected_packages:
            if not validate_package_name(pkg_name):
                invalid.append(pkg_name)
            elif not self.is_package_installed(pkg_name):
                not_installed.append(pkg_name)
            elif pkg_name not in self._minimal_packages:
                not_removable.append(pkg_name)
            else:
                valid.append(pkg_name)

        return {
            "valid": valid,
            "invalid": invalid,
            "not_installed": not_installed,
            "not_removable": not_removable,
        }
