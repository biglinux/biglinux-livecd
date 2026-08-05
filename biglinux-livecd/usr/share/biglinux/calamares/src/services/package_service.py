"""Load the removable package list used by the minimal installation page."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..infrastructure import (
    ICON_MAPPING_FILE,
    MINIMAL_PACKAGES_FILE,
    TEMP_FILES,
    load_json_file,
    pacman_query_installed,
    validate_package_name,
)


@dataclass(slots=True)
class Package:
    name: str
    icon: str
    selected: bool = True


class PackageService:
    """Provide the installed subset of the packaged removal list."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._icon_mapping: dict[str, str] = {}
        self._minimal_packages: list[str] = []
        self._installed_packages: set[str] = set()

    def initialize(self) -> None:
        icon_mapping = load_json_file(ICON_MAPPING_FILE)
        if isinstance(icon_mapping, dict):
            self._icon_mapping = {
                str(name): str(icon) for name, icon in icon_mapping.items()
            }

        package_data = load_json_file(MINIMAL_PACKAGES_FILE)
        if isinstance(package_data, dict):
            package_data = package_data.get("packages", [])
        if isinstance(package_data, list):
            self._minimal_packages = [
                package for package in package_data if isinstance(package, str)
            ]

        self._installed_packages = set(pacman_query_installed())
        TEMP_FILES["installed_packages"].write_text(
            "\n".join(sorted(self._installed_packages)), encoding="utf-8"
        )

    def cleanup(self) -> None:
        self._icon_mapping.clear()
        self._minimal_packages.clear()
        self._installed_packages.clear()

    def get_minimal_packages(self) -> list[Package]:
        packages = [
            Package(
                name=name,
                icon=self._icon_mapping.get(name, name),
            )
            for name in self._minimal_packages
            if validate_package_name(name) and name in self._installed_packages
        ]
        TEMP_FILES["available_to_remove"].write_text(
            "\n".join(package.name for package in packages), encoding="utf-8"
        )
        return packages

    def get_packages_for_removal(self, selected_packages: list[str]) -> list[str]:
        packages = [
            name
            for name in selected_packages
            if validate_package_name(name)
            and name in self._installed_packages
            and name in self._minimal_packages
        ]
        TEMP_FILES["packages_to_remove"].write_text(
            "\n".join(packages), encoding="utf-8"
        )
        return packages
