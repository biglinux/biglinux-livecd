from __future__ import annotations

import ast
import logging
import os
import stat
from collections.abc import Mapping
from typing import Protocol

logger = logging.getLogger(__name__)
GNOME_LIGHT_STYLE_UUID = "light-style@gnome-shell-extensions.gcampax.github.com"
GNOME_USER_THEME_UUID = "user-theme@gnome-shell-extensions.gcampax.github.com"
GNOME_KIWI_UUID = "kiwi@kemma"
GNOME_DTP_UUID = "dash-to-panel@jderose9.github.com"
MAX_SETTINGS_BYTES = 1024 * 1024

SettingsChanges = Mapping[str, Mapping[str, str]]


class ThemeHost(Protocol):
    test_mode: bool
    theme_list_script: str
    theme_apply_script: str
    theme_state_file: str

    def _run_command(
        self,
        command: list[str],
        *,
        as_root: bool = False,
        read_only: bool = False,
        wait_for_completion: bool = False,
    ) -> tuple[bool, str]: ...

    def _write_live_state_file(self, filepath: str, content: str) -> bool: ...

    def _write_user_config_file(self, filepath: str, content: str) -> bool: ...

    def _apply_gtk_settings_ini(self, dark: bool, icon_theme: str) -> None: ...

    def get_desktop_environment(self) -> str: ...

    def _ensure_gnome_settings_file(self) -> None: ...

    def _sync_gnome_settings_tmp(self) -> None: ...

    def _stamp_gnome_input_sources(self, settings_file: str) -> None: ...


def available_theme_names(host: ThemeHost) -> list[str]:
    if not os.path.isfile(host.theme_list_script):
        logger.warning("Theme list command is unavailable")
        return []
    success, output = host._run_command([host.theme_list_script], read_only=True)
    if not success:
        return []
    return [name for name in output.splitlines() if name]


def apply_packaged_theme(host: ThemeHost, theme: str) -> bool:
    if theme not in set(available_theme_names(host)):
        logger.error("Refusing unknown packaged theme: %s", theme)
        return False
    if not host._write_live_state_file(host.theme_state_file, theme):
        return False
    success, _output = host._run_command([host.theme_apply_script, theme])
    return success


def _simple_icon_theme(desktop_environment: str, dark: bool) -> str:
    if dark:
        return "bigicons-papient-dark"
    if desktop_environment == "XFCE":
        return "bigicons-papient-light"
    return "bigicons-papient"


def settings_file_path(desktop_environment: str) -> str:
    filenames = {
        "Cinnamon": "settings.cinnamon",
        "GNOME": "settings.gnome",
        "XFCE": "settings.xfce",
    }
    filename = filenames.get(desktop_environment)
    if filename is None:
        return ""
    return os.path.join(os.path.expanduser("~"), ".config", "dconf", filename)


def _read_regular_text(path: str) -> str:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError("settings source is not a regular file")
        if file_stat.st_size > MAX_SETTINGS_BYTES:
            raise OSError("settings source exceeds its size limit")
        with os.fdopen(descriptor, "r", encoding="utf-8") as settings_file:
            descriptor = -1
            content = settings_file.read(MAX_SETTINGS_BYTES + 1)
            if len(content.encode("utf-8")) > MAX_SETTINGS_BYTES:
                raise OSError("settings source grew beyond its size limit")
            return content
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def update_settings_text(  # noqa: C901 - single-pass parser preserves file structure
    text: str, changes: SettingsChanges
) -> str:
    output: list[str] = []
    current_section = ""
    seen_sections: set[str] = set()
    seen_keys: dict[str, set[str]] = {section: set() for section in changes}

    def append_missing(section: str) -> None:
        if section not in changes:
            return
        for key, value in changes[section].items():
            if key not in seen_keys[section]:
                output.append(f"{key}={value}\n")
                seen_keys[section].add(key)

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            append_missing(current_section)
            current_section = stripped[1:-1]
            seen_sections.add(current_section)
            output.append(line)
            continue
        if (
            current_section in changes
            and "=" in stripped
            and not stripped.startswith("#")
        ):
            key = stripped.partition("=")[0].strip()
            if key in changes[current_section]:
                if key not in seen_keys[current_section]:
                    output.append(f"{key}={changes[current_section][key]}\n")
                    seen_keys[current_section].add(key)
                continue
        output.append(line)

    append_missing(current_section)
    for section, keys in changes.items():
        if section in seen_sections:
            continue
        if output and output[-1].strip():
            output.append("\n")
        output.append(f"[{section}]\n")
        output.extend(f"{key}={value}\n" for key, value in keys.items())
    return "".join(output)


def modify_settings_file(
    host: ThemeHost, settings_file: str, changes: SettingsChanges
) -> bool:
    if host.test_mode:
        return True
    if not settings_file:
        logger.error("No settings file belongs to this desktop environment")
        return False
    try:
        current = _read_regular_text(settings_file)
    except (OSError, UnicodeError) as error:
        logger.error("Could not read desktop settings: %s", error)
        return False
    return host._write_user_config_file(
        settings_file, update_settings_text(current, changes)
    )


def _parse_settings_list(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value.strip())
    except (ValueError, SyntaxError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str) and item]


def _settings_key_values(
    settings_file: str, section_name: str
) -> dict[str, str] | None:
    try:
        text = _read_regular_text(settings_file)
    except (OSError, UnicodeError) as error:
        logger.error("Could not inspect GNOME settings: %s", error)
        return None
    values: dict[str, str] = {}
    current_section = ""
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1]
        elif current_section == section_name and "=" in stripped:
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()
    return values


def _gnome_extension_changes(
    settings_file: str, dark: bool
) -> dict[str, dict[str, str]]:
    values = _settings_key_values(settings_file, "org/gnome/shell")
    if values is None:
        return {}
    enabled = _parse_settings_list(values.get("enabled-extensions", "[]"))
    disabled = _parse_settings_list(values.get("disabled-extensions", "[]"))
    if dark:
        enabled = [item for item in enabled if item != GNOME_LIGHT_STYLE_UUID]
        disabled = [item for item in disabled if item != GNOME_USER_THEME_UUID]
        enabled.append(GNOME_USER_THEME_UUID)
        disabled.append(GNOME_LIGHT_STYLE_UUID)
    else:
        enabled = [item for item in enabled if item != GNOME_USER_THEME_UUID]
        disabled = [item for item in disabled if item != GNOME_LIGHT_STYLE_UUID]
        enabled.append(GNOME_LIGHT_STYLE_UUID)
        disabled.append(GNOME_USER_THEME_UUID)
    return {
        "org/gnome/shell": {
            "enabled-extensions": repr(list(dict.fromkeys(enabled))),
            "disabled-extensions": repr(list(dict.fromkeys(disabled))),
        }
    }


def _gnome_layout_class(settings_file: str) -> str:
    values = _settings_key_values(settings_file, "org/gnome/shell")
    if values is None:
        return "biggnome"
    enabled = _parse_settings_list(values.get("enabled-extensions", "[]"))
    if GNOME_KIWI_UUID in enabled:
        return "kiwi"
    if GNOME_DTP_UUID in enabled:
        return "panel"
    return "biggnome"


def _desktop_changes(
    desktop_environment: str, settings_file: str, dark: bool
) -> dict[str, dict[str, str]]:
    color_scheme = "'prefer-dark'" if dark else "'default'"
    gtk_theme = "'adw-gtk3-dark'" if dark else "'adw-gtk3'"
    icon_theme = f"'{_simple_icon_theme(desktop_environment, dark)}'"
    changes = {
        "org/gnome/desktop/interface": {
            "color-scheme": color_scheme,
            "gtk-theme": gtk_theme,
            "icon-theme": icon_theme,
        }
    }
    if desktop_environment == "Cinnamon":
        changes["org/cinnamon/desktop/interface"] = {
            "gtk-theme": gtk_theme,
            "icon-theme": icon_theme,
        }
        changes["org/cinnamon/theme"] = {
            "name": "'Big-Orange'" if dark else "'Big-Orange-Light'"
        }
    elif desktop_environment == "GNOME":
        layout_class = _gnome_layout_class(settings_file)
        if dark and layout_class != "kiwi":
            changes["org/gnome/shell/extensions/user-theme"] = {"name": "'Big-Blue'"}
            changes.update(_gnome_extension_changes(settings_file, dark=True))
        elif not dark and layout_class == "biggnome":
            changes["org/gnome/shell/extensions/user-theme"] = {"name": "'Big-Blue'"}
            changes.update(_gnome_extension_changes(settings_file, dark=True))
        elif not dark and layout_class == "panel":
            changes["org/gnome/shell/extensions/user-theme"] = {"name": "'Big-Blue'"}
            changes.update(_gnome_extension_changes(settings_file, dark=False))
    return changes


def _apply_xfce(host: ThemeHost, dark: bool) -> None:
    gtk_theme = "adw-gtk3-dark" if dark else "adw-gtk3"
    icon_theme = _simple_icon_theme("XFCE", dark)
    for channel, property_name, value in (
        ("xsettings", "/Net/ThemeName", gtk_theme),
        ("xsettings", "/Net/IconThemeName", icon_theme),
        ("xfwm4", "/general/theme", gtk_theme),
    ):
        host._run_command(
            ["xfconf-query", "-c", channel, "-p", property_name, "-s", value]
        )


def apply_simple_theme(host: ThemeHost, theme: str) -> bool:
    if theme not in {"dark", "light"}:
        logger.error("Refusing unsupported simple theme: %s", theme)
        return False
    if not host._write_live_state_file(host.theme_state_file, theme):
        return False
    dark = theme == "dark"
    desktop_environment = host.get_desktop_environment()
    if desktop_environment == "GNOME":
        host._ensure_gnome_settings_file()
    settings_file = settings_file_path(desktop_environment)
    if not modify_settings_file(
        host,
        settings_file,
        _desktop_changes(desktop_environment, settings_file, dark),
    ):
        return False
    if desktop_environment == "XFCE":
        _apply_xfce(host, dark)
    host._apply_gtk_settings_ini(
        dark=dark,
        icon_theme=_simple_icon_theme(desktop_environment, dark),
    )

    home = os.path.expanduser("~")
    kvantum_theme = "BigAdwaitaRoundGtkDark" if dark else "BigAdwaitaRoundGtk"
    if not host._write_user_config_file(
        os.path.join(home, ".config", "Kvantum", "kvantum.kvconfig"),
        f"[General]\ntheme={kvantum_theme}\n",
    ):
        return False
    source_name = "biglinux-dark" if dark else "biglinux"
    kdeglobals_source = f"/usr/share/sync-kde-and-gtk-places/{source_name}"
    if os.path.isfile(kdeglobals_source):
        success, _output = host._run_command(
            ["cp", "-f", kdeglobals_source, os.path.join(home, ".config", "kdeglobals")]
        )
        if not success:
            return False
    else:
        logger.warning("KDE theme settings are unavailable")
    if desktop_environment == "GNOME":
        host._stamp_gnome_input_sources(settings_file)
        host._sync_gnome_settings_tmp()
    return True
