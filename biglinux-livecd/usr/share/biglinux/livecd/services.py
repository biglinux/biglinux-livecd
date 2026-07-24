import os
import re
import subprocess
import tempfile
from typing import List, Tuple

from config import SetupConfig
from desktop_theme import (
    apply_packaged_theme,
    available_theme_names,
    modify_settings_file,
    settings_file_path,
)
from desktop_theme import (
    apply_simple_theme as apply_simple_desktop_theme,
)
from gnome_layout import LAYOUT_DISPLAY_NAMES, LAYOUT_NAMES, normalize_layout_text
from logging_config import get_logger
from user_config import update_ini_file
from user_config import write_text as write_user_config_text

logger = get_logger()


class SystemService:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        if self.test_mode:
            logger.info(
                "--- RUNNING IN TEST MODE: No system changes will be applied. ---"
            )

        # Base paths from the original scripts
        self.base_themes_path = "/usr/share/biglinux/biglinux-themes-gui"
        self.desktop_list_script = os.path.join(
            self.base_themes_path, "list-desktops.sh"
        )
        self.desktop_apply_script = os.path.join(
            self.base_themes_path, "apply-desktop.sh"
        )
        self.theme_list_script = os.path.join(self.base_themes_path, "list-themes.sh")
        self.theme_apply_script = os.path.join(self.base_themes_path, "apply-theme.sh")

        # Image paths
        self.desktop_image_path = os.path.join(self.base_themes_path, "img/{}.svg")
        self.theme_image_path = os.path.join(self.base_themes_path, "img/{}.png")
        self.assets_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "assets")
        )
        # GNOME layout definitions (.txt) and previews (.svg) come straight from
        # the layout-switcher package — single source of truth, no longer
        # duplicated under assets/gnome-layouts/. The GNOME layout chooser only
        # runs on the GNOME profile, where layout-switcher is installed, so this
        # is not a hard dependency of biglinux-livecd (KDE/XFCE ISOs don't use it).
        self.gnome_layouts_path = "/usr/share/layout-switcher/layouts"
        self.gnome_layouts_icons_path = "/usr/share/layout-switcher/icons"

        # Boot-scoped live state consumed by startbiglive and install setup.
        self.live_state_dir = "/tmp"
        self.language_state_file = "/tmp/big_language"
        self.keyboard_state_file = "/tmp/big_keyboard"
        self.desktop_state_file = "/tmp/big_desktop_changed"
        self.gnome_layout_state_file = "/tmp/big_gnome_layout"
        self.gnome_settings_state_file = "/tmp/big_gnome_settings"
        self.theme_state_file = "/tmp/big_desktop_theme"
        self.jamesdsp_state_file = "/tmp/big_enable_jamesdsp"
        self.display_profile_state_file = "/tmp/big_improve_display"
        self._gnome_input_sources: str | None = None

    def _run_command(
        self,
        command: List[str],
        as_root: bool = False,
        read_only: bool = False,
        wait_for_completion: bool = False,
    ) -> Tuple[bool, str]:
        """
        Helper to run external commands.
        - If wait_for_completion or read_only is True, it runs synchronously and returns output.
        - Otherwise, it runs in the background (asynchronously) and detaches.
        """
        if self.test_mode and not read_only:
            logger.debug(
                f"[TEST MODE] Suppressed command: {'sudo ' if as_root else ''}{' '.join(command)}"
            )
            return True, ""

        if read_only:
            wait_for_completion = True

        if as_root:
            command.insert(0, "sudo")

        try:
            if wait_for_completion:
                # Run synchronously and capture output (for read-only commands)
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                    encoding="utf-8",
                )
                return True, result.stdout.strip()
            else:
                # Run in the background and detach
                # Redirect stdout/stderr to /dev/null to prevent terminal clutter
                subprocess.Popen(
                    command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return True, ""  # Assume success on launch
        except FileNotFoundError:
            err_msg = f"Command not found: {command[0]}"
            logger.error(err_msg)
            return False, err_msg
        except subprocess.CalledProcessError as e:
            err_msg = f"Error running command '{' '.join(e.cmd)}': {e.stderr}"
            logger.error(err_msg)
            return False, e.stderr.strip()
        except Exception as e:
            err_msg = (
                f"An unexpected error occurred with command '{' '.join(command)}': {e}"
            )
            logger.error(err_msg)
            return False, str(e)

    def _write_live_state_file(self, filepath: str, content: str) -> bool:
        """Atomically commit one boot-scoped live state file."""
        if self.test_mode:
            logger.debug(
                f"[TEST MODE] Suppressed write to {filepath}: '{content[:50]}{'...' if len(content) > 50 else ''}'"
            )
            return True
        if os.path.dirname(filepath) != self.live_state_dir:
            logger.error("Refusing live state path outside the contract directory")
            return False
        temporary_path = ""
        try:
            directory_stat = os.lstat(self.live_state_dir)
            if not os.path.isdir(self.live_state_dir) or os.path.islink(
                self.live_state_dir
            ):
                raise OSError("live state directory is missing or unsafe")
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.live_state_dir,
                prefix=f".{os.path.basename(filepath)}.",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, filepath)
            temporary_path = ""
            directory_fd = os.open(
                self.live_state_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                verified_directory = os.fstat(directory_fd)
                if (verified_directory.st_dev, verified_directory.st_ino) != (
                    directory_stat.st_dev,
                    directory_stat.st_ino,
                ):
                    raise OSError("live state directory changed while writing")
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return True
        except OSError as e:
            logger.error(f"Error writing to {filepath}: {e}")
            return False
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def _remove_live_state_file(self, filepath: str) -> bool:
        if self.test_mode:
            logger.debug(f"[TEST MODE] Suppressed removal of {filepath}")
            return True
        if os.path.dirname(filepath) != self.live_state_dir:
            logger.error("Refusing live state path outside the contract directory")
            return False
        try:
            os.unlink(filepath)
        except FileNotFoundError:
            return True
        except OSError as error:
            logger.error(f"Error removing {filepath}: {error}")
            return False
        directory_fd = os.open(
            self.live_state_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True

    def _write_user_config_file(self, filepath: str, content: str) -> bool:
        if self.test_mode:
            return True
        try:
            write_user_config_text(filepath, content)
            return True
        except OSError as error:
            logger.error("Could not write user configuration: %s", error)
            return False

    def _update_ini_settings(
        self, filepath: str, section: str, settings: dict[str, str]
    ) -> bool:
        if self.test_mode:
            return True
        try:
            update_ini_file(filepath, section, settings)
            return True
        except (OSError, UnicodeError) as error:
            logger.error("Could not update user configuration: %s", error)
            return False

    def _apply_gtk_settings_ini(self, dark: bool, icon_theme: str):
        """Keep GTK settings.ini in sync for XFCE/Cinnamon sessions."""
        home = os.path.expanduser("~")
        gtk_theme = "adw-gtk3-dark" if dark else "adw-gtk3"
        prefer_dark = "true" if dark else "false"
        settings = {
            "gtk-application-prefer-dark-theme": prefer_dark,
            "gtk-theme-name": gtk_theme,
            "gtk-icon-theme-name": icon_theme,
        }

        for gtk_dir in ("gtk-3.0", "gtk-4.0"):
            settings_path = os.path.join(home, ".config", gtk_dir, "settings.ini")
            self._update_ini_settings(settings_path, "Settings", settings)

    def apply_language_settings(self, lang_code: str, timezone: str):
        """Applies language, locale, and timezone settings."""
        logger.info(f"Setting language to {lang_code} and timezone to {timezone}")
        self._write_live_state_file(self.language_state_file, lang_code)

        self._run_command(["timedatectl", "set-timezone", timezone], as_root=True)
        self._run_command(["timedatectl", "set-ntp", "1"], as_root=True)
        self._run_command(
            ["localectl", "set-locale", f"LANG={lang_code}.UTF-8"], as_root=True
        )

    def apply_keyboard_layout(self, layout: str):
        """Applies the selected keyboard layout."""
        logger.info(f"Setting keyboard layout to: {layout}")
        layout_cleaned = layout.replace("\\", "")
        self._write_live_state_file(self.keyboard_state_file, layout_cleaned)
        self._run_command(["setxkbmap", layout_cleaned])
        xkb_layout, xkb_variant = self._split_xkb_layout(layout_cleaned)
        self._run_command(
            [
                "localectl",
                "set-x11-keymap",
                xkb_layout,
                "pc105",
                xkb_variant,
                "terminate:ctrl_alt_bksp",
            ],
            as_root=True,
        )

        home = os.path.expanduser("~")
        desktop_env = self.get_desktop_environment()

        if desktop_env == "Cinnamon":
            # Configure keyboard layout via dconf settings file for Cinnamon
            settings_file = settings_file_path(desktop_env)
            if settings_file:
                sources_value = f"[('xkb', '{layout_cleaned}')]"
                modify_settings_file(
                    self,
                    settings_file,
                    {
                        "org/cinnamon/desktop/input-sources": {
                            "sources": sources_value
                        },
                        "org/gnome/desktop/input-sources": {"sources": sources_value},
                    },
                )
                logger.info(
                    f"Configured keyboard layout '{layout_cleaned}' in settings.cinnamon"
                )
        elif desktop_env == "GNOME":
            xkb_id = f"{xkb_layout}+{xkb_variant}" if xkb_variant else xkb_layout
            self._gnome_input_sources = f"[('xkb', '{xkb_id}')]"
            settings_file = settings_file_path(desktop_env)
            self._stamp_gnome_input_sources(settings_file)
            logger.info(
                f"Configured keyboard layout '{layout_cleaned}' for GNOME input-sources"
            )
        else:
            # KDE/Plasma uses kxkbrc
            kxkbrc_path = os.path.join(home, ".config", "kxkbrc")
            kxkbrc_content = (
                "[Layout]\n"
                "DisplayNames=\n"
                f"LayoutList={xkb_layout}\n"
                "Model=pc105\n"
                "Options=terminate:ctrl_alt_bksp\n"
                "ResetOldOptions=true\n"
                "Use=true\n"
                f"VariantList={xkb_variant}\n"
            )
            self._write_user_config_file(kxkbrc_path, kxkbrc_content)

    def get_available_desktops(self) -> List[str]:
        """Returns a list of available desktop layout names."""
        if self.get_desktop_environment() == "GNOME":
            layouts = [
                layout
                for layout in LAYOUT_NAMES
                if os.path.exists(self._get_gnome_layout_file_path(layout))
            ]
            if not layouts:
                logger.warning(f"No GNOME layouts found at {self.gnome_layouts_path}")
            return layouts

        if not os.path.exists(self.desktop_list_script):
            logger.warning(f"Desktop script not found at {self.desktop_list_script}")
            return []
        success, output = self._run_command([self.desktop_list_script], read_only=True)
        return output.splitlines() if success else []

    def apply_desktop_layout(self, layout: str):
        """Applies the selected desktop layout."""
        logger.info(f"Applying desktop layout: {layout}")
        if self.get_desktop_environment() == "GNOME":
            self.apply_gnome_desktop_layout(layout)
            return

        self._write_live_state_file(self.desktop_state_file, layout)
        self._run_command([self.desktop_apply_script, layout, "quiet"])

    def apply_gnome_desktop_layout(self, layout: str):
        """Prepare the selected GNOME layout for startgnome-community."""
        layout_file = self._get_gnome_layout_file_path(layout)
        if not layout_file or not os.path.exists(layout_file):
            logger.error(f"GNOME layout file not found for: {layout}")
            return

        try:
            with open(layout_file, "r", encoding="utf-8") as f:
                layout_text = f.read()
        except OSError as e:
            logger.error(f"Failed to read GNOME layout {layout_file}: {e}")
            return

        settings_text = normalize_layout_text(layout_text)
        settings_file = settings_file_path("GNOME")
        if not self._write_user_config_file(settings_file, settings_text):
            return

        self._stamp_gnome_input_sources(settings_file)

        self._write_live_state_file(self.desktop_state_file, layout)
        self._write_live_state_file(self.gnome_layout_state_file, layout)
        self._sync_gnome_settings_tmp()
        logger.info(f"Prepared GNOME layout '{layout}' in {settings_file}")

    def get_available_themes(self) -> List[str]:
        """Returns a list of available theme names."""
        return available_theme_names(self)

    def apply_theme(self, theme: str) -> bool:
        """Applies the selected theme."""
        return apply_packaged_theme(self, theme)

    def apply_simple_theme(self, theme: str) -> bool:
        """Apply an allowlisted light or dark desktop theme."""
        return apply_simple_desktop_theme(self, theme)

    def finalize_setup(self, config: SetupConfig):
        """
        Performs final setup steps, including creating flag files.

        All config files are saved under /run/biglinux-live during the live session.
        Calamares will copy them to /etc/big-default-config/ on the installed system.
        """
        logger.info("Finalizing setup...")

        self._finalize_jamesdsp(config.enable_jamesdsp)
        self._finalize_display_profile(config.enable_enhanced_contrast)
        self._run_command(["killall", "kwin_wayland"])

    def _finalize_jamesdsp(self, is_enabled: bool) -> None:
        jamesdsp_conf = os.path.expanduser("~/.config/jamesdsp/application.conf")
        replacement = (
            "s|AutoStartEnabled=false|AutoStartEnabled=true|g"
            if is_enabled
            else "s|AutoStartEnabled=true|AutoStartEnabled=false|g"
        )
        service_action = "restart" if is_enabled else "stop"
        if is_enabled:
            self._write_live_state_file(self.jamesdsp_state_file, "enabled")
        else:
            self._remove_live_state_file(self.jamesdsp_state_file)
        if os.path.exists(jamesdsp_conf):
            self._run_command(["sed", "-i", replacement, jamesdsp_conf], as_root=False)
            self._run_command(
                ["systemctl", "--user", service_action, "jamesdsp-autostart.service"],
                as_root=False,
            )

    def _finalize_display_profile(self, is_enabled: bool) -> None:
        action = "enable" if is_enabled else "disable"
        if is_enabled:
            self._write_live_state_file(self.display_profile_state_file, "enabled")
        else:
            self._remove_live_state_file(self.display_profile_state_file)
        self._run_command(["/usr/bin/icc_profile_apply", action], as_root=False)

    def get_desktop_image_path(self, layout_name: str) -> str:
        if self.get_desktop_environment() == "GNOME":
            return os.path.join(self.gnome_layouts_icons_path, f"{layout_name}.svg")
        return self.desktop_image_path.format(layout_name)

    def get_theme_image_path(self, theme_name: str) -> str:
        return self.theme_image_path.format(theme_name)

    def get_desktop_display_name(self, layout_name: str) -> str:
        return LAYOUT_DISPLAY_NAMES.get(layout_name, layout_name)

    def apply_jamesdsp_settings(self, enabled: bool):
        """
        Applies JamesDSP configuration immediately.
        This is called when a theme is selected, based on the switch state.
        """
        home = os.path.expanduser("~")
        jamesdsp_conf = os.path.join(home, ".config/jamesdsp/application.conf")

        if enabled:
            logger.info("Applying JamesDSP enabled settings...")
            self._write_live_state_file(self.jamesdsp_state_file, "enabled")
            if os.path.exists(jamesdsp_conf):
                self._run_command(
                    [
                        "sed",
                        "-i",
                        "s|AutoStartEnabled=false|AutoStartEnabled=true|g",
                        jamesdsp_conf,
                    ],
                    as_root=False,
                )
                # Restart the systemd service so JamesDSP actually starts
                self._run_command(
                    ["systemctl", "--user", "restart", "jamesdsp-autostart.service"],
                    as_root=False,
                )
        else:
            logger.info("Applying JamesDSP disabled settings...")
            self._remove_live_state_file(self.jamesdsp_state_file)
            if os.path.exists(jamesdsp_conf):
                self._run_command(
                    [
                        "sed",
                        "-i",
                        "s|AutoStartEnabled=true|AutoStartEnabled=false|g",
                        jamesdsp_conf,
                    ],
                    as_root=False,
                )
                # Stop the systemd service so JamesDSP actually stops
                self._run_command(
                    ["systemctl", "--user", "stop", "jamesdsp-autostart.service"],
                    as_root=False,
                )

    def apply_icc_profile_settings(self, enabled: bool):
        """
        Applies ICC profile configuration immediately.
        This is called when a theme is selected, based on the switch state.
        """
        if enabled:
            logger.info("Applying ICC profile enabled settings...")
            self._write_live_state_file(self.display_profile_state_file, "enabled")
            self._run_command(
                ["/usr/bin/icc_profile_apply", "enable"],
                as_root=False,
            )
        else:
            logger.info("Applying ICC profile disabled settings...")
            self._remove_live_state_file(self.display_profile_state_file)
            self._run_command(
                ["/usr/bin/icc_profile_apply", "disable"],
                as_root=False,
            )

    def check_jamesdsp_availability(self) -> bool:
        """Checks if JamesDSP executable exists."""
        return os.path.exists("/usr/bin/jamesdsp")

    def check_enhanced_contrast_availability(self) -> bool:
        """Checks for the AppleRGB ICC profile and if running on Wayland."""
        icc_profile_exists = os.path.exists("/usr/share/color/icc/colord/ECI-RGBv1.icc")
        logger.debug(f"ICC profile exists: {icc_profile_exists}")

        # Check if running on Wayland (works for GNOME, KDE, etc)
        wayland_running = False

        # Method 1: Check XDG_SESSION_TYPE environment variable
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        logger.debug(f"XDG_SESSION_TYPE: {session_type}")
        if session_type == "wayland":
            wayland_running = True

        # Method 2: Check if WAYLAND_DISPLAY is set
        wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
        logger.debug(f"WAYLAND_DISPLAY: {wayland_display}")
        if not wayland_running and wayland_display:
            wayland_running = True

        # Method 3: Check for compositor processes (fallback)
        if not wayland_running:
            try:
                # Check for kwin_wayland (KDE) or gnome-shell on Wayland
                result = subprocess.run(
                    ["pgrep", "-x", "kwin_wayland"], capture_output=True, check=False
                )
                wayland_running = result.returncode == 0
            except FileNotFoundError:
                pass

        logger.info(
            f"Enhanced contrast availability: ICC={icc_profile_exists}, Wayland={wayland_running}, Result={icc_profile_exists and wayland_running}"
        )
        return icc_profile_exists and wayland_running

    def get_total_memory_gb(self) -> float:
        """Gets total system memory in Gigabytes from /proc/meminfo."""
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                meminfo = f.read()
            match = re.search(r"MemTotal:\s+(\d+)\s+kB", meminfo)
            if match:
                kb = int(match.group(1))
                gb = kb / (1024 * 1024)
                return gb
        except (FileNotFoundError, ValueError, IndexError) as e:
            logger.warning(f"Could not read or parse /proc/meminfo: {e}")
        return 0.0  # Safe fallback

    def is_virtual_machine(self) -> bool:
        """Checks if the system is running inside a virtual machine using systemd-detect-virt."""
        try:
            # systemd-detect-virt returns 0 if in a VM, 1 otherwise.
            result = subprocess.run(
                ["systemd-detect-virt"], capture_output=True, check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            # Fallback if the command doesn't exist. Assume not a VM for safety.
            return False

    def get_desktop_environment(self) -> str:
        """Detects the desktop environment by checking specific startup files."""
        if os.path.exists("/usr/bin/startgnome-community"):
            return "GNOME"
        elif os.path.exists("/usr/bin/startcinnamon-community"):
            return "Cinnamon"
        elif os.path.exists("/usr/bin/startxfce-community"):
            return "XFCE"
        else:
            return "other"

    def is_simplified_environment(self) -> bool:
        """Checks if we should use simplified UI (GNOME/XFCE/Cinnamon)."""
        desktop_env = self.get_desktop_environment()
        return desktop_env in ["GNOME", "XFCE", "Cinnamon"]

    def uses_simple_theme_selector(self) -> bool:
        """Checks if the theme step should be light/dark only."""
        return self.get_desktop_environment() in ["GNOME", "XFCE", "Cinnamon"]

    def has_desktop_layout_step(self) -> bool:
        """Checks if the wizard should show the desktop layout step."""
        desktop_env = self.get_desktop_environment()
        return desktop_env == "GNOME" or not self.is_simplified_environment()

    def _get_gnome_layout_file_path(self, layout: str) -> str:
        if layout not in LAYOUT_NAMES:
            return ""
        return os.path.join(self.gnome_layouts_path, f"{layout}.txt")

    @staticmethod
    def _split_xkb_layout(layout: str) -> tuple[str, str]:
        match = re.fullmatch(r"([^()]+)\(([^()]+)\)", layout)
        if match:
            return match.group(1), match.group(2)
        return layout, ""

    def _stamp_gnome_input_sources(self, settings_file: str) -> None:
        if not self._gnome_input_sources or not os.path.isfile(settings_file):
            return
        modify_settings_file(
            self,
            settings_file,
            {"org/gnome/desktop/input-sources": {"sources": self._gnome_input_sources}},
        )

    def _ensure_gnome_settings_file(self):
        settings_file = settings_file_path("GNOME")
        if os.path.exists(settings_file):
            return
        default_layout = LAYOUT_NAMES[0]
        logger.info(f"Creating GNOME settings from default layout: {default_layout}")
        self.apply_gnome_desktop_layout(default_layout)

    def _sync_gnome_settings_tmp(self):
        settings_file = settings_file_path("GNOME")
        if not os.path.exists(settings_file):
            return
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                self._write_live_state_file(self.gnome_settings_state_file, f.read())
        except OSError as e:
            logger.error(f"Failed to sync GNOME settings temp file: {e}")

    # XivaStudio detection with caching
    _xivastudio_cache: bool | None = None

    # XivaStudio custom logo paths
    XIVASTUDIO_LOGO_PNG = "/usr/share/pixmaps/icon-logo-xivastudio.png"
    XIVASTUDIO_LOGO_GIF = "/usr/share/pixmaps/icon-logo-xivastudio.gif"

    def is_xivastudio(self) -> bool:
        """
        Checks if running on XivaStudio variant.
        Result is cached after first check.
        """
        if SystemService._xivastudio_cache is None:
            SystemService._xivastudio_cache = os.path.exists(
                self.XIVASTUDIO_LOGO_PNG
            ) or os.path.exists(self.XIVASTUDIO_LOGO_GIF)
        return SystemService._xivastudio_cache

    def get_xivastudio_logo_path(self) -> str | None:
        """
        Returns XivaStudio logo path if available.
        PNG is preferred over GIF.
        """
        if os.path.exists(self.XIVASTUDIO_LOGO_PNG):
            return self.XIVASTUDIO_LOGO_PNG
        if os.path.exists(self.XIVASTUDIO_LOGO_GIF):
            return self.XIVASTUDIO_LOGO_GIF
        return None
