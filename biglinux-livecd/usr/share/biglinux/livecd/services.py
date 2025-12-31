import subprocess
import os
import re
from typing import List, Tuple
from config import SetupConfig
from logging_config import get_logger

logger = get_logger()


class SystemService:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        if self.test_mode:
            logger.info(
                "--- RUNNING IN TEST MODE: No system changes will be applied. ---"
            )

        # Base paths from the original scripts
        self.base_themes_path = "/usr/share/bigbashview/apps/biglinux-themes-gui"
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

        # Temp files for live session - Calamares will copy these to /etc/big-default-config/
        self.tmp_lang_file = "/tmp/big_language"
        self.tmp_keyboard_file = "/tmp/big_keyboard"
        self.tmp_desktop_file = "/tmp/big_desktop_changed"
        self.tmp_theme_file = "/tmp/big_desktop_theme"
        self.tmp_jamesdsp_file = "/tmp/big_enable_jamesdsp"
        self.tmp_display_profile_file = "/tmp/big_improve_display"
        self.tmp_simple_theme_file = "/tmp/big_simple_theme"

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
            err_msg = f"An unexpected error occurred with command '{' '.join(command)}': {e}"
            logger.error(err_msg)
            return False, str(e)


    def _write_tmp_file(self, filepath: str, content: str):
        """Helper to write to a temp file."""
        if self.test_mode:
            logger.debug(
                f"[TEST MODE] Suppressed write to {filepath}: '{content[:50]}{'...' if len(content) > 50 else ''}'"
            )
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            logger.error(f"Error writing to {filepath}: {e}")

    def _write_user_config_file(self, filepath: str, content: str):
        """Helper to write a file in the user's home directory."""
        if self.test_mode:
            logger.debug(
                f"[TEST MODE] Suppressed write to {filepath}: '{content[:50]}{'...' if len(content) > 50 else ''}'"
            )
            return
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            logger.error(f"Error writing to {filepath}: {e}")

    def apply_language_settings(self, lang_code: str, timezone: str):
        """Applies language, locale, and timezone settings."""
        logger.info(f"Setting language to {lang_code} and timezone to {timezone}")
        self._write_tmp_file(self.tmp_lang_file, lang_code)

        self._run_command(["timedatectl", "set-timezone", timezone], as_root=True)
        self._run_command(["timedatectl", "set-ntp", "1"], as_root=True)
        self._run_command(
            ["localectl", "set-locale", f"LANG={lang_code}.UTF-8"], as_root=True
        )
        self._run_command(["/usr/share/biglinux/livecd/script/biglinux-verify-md5sum.sh"], as_root=False)

    def apply_keyboard_layout(self, layout: str):
        """Applies the selected keyboard layout."""
        logger.info(f"Setting keyboard layout to: {layout}")
        layout_cleaned = layout.replace("\\", "")
        self._write_tmp_file(self.tmp_keyboard_file, layout_cleaned)
        self._run_command(["setxkbmap", layout_cleaned])

        home = os.path.expanduser("~")
        kxkbrc_path = os.path.join(home, ".config", "kxkbrc")
        kxkbrc_content = f"[Layout]\nLayoutList={layout_cleaned}\nUse=true\n"
        self._write_user_config_file(kxkbrc_path, kxkbrc_content)

    def get_available_desktops(self) -> List[str]:
        """Returns a list of available desktop layout names."""
        if not os.path.exists(self.desktop_list_script):
            logger.warning(f"Desktop script not found at {self.desktop_list_script}")
            return []
        success, output = self._run_command([self.desktop_list_script], read_only=True)
        return output.splitlines() if success else []

    def apply_desktop_layout(self, layout: str):
        """Applies the selected desktop layout."""
        logger.info(f"Applying desktop layout: {layout}")
        self._write_tmp_file(self.tmp_desktop_file, layout)
        self._run_command([self.desktop_apply_script, layout, "quiet"])

    def get_available_themes(self) -> List[str]:
        """Returns a list of available theme names."""
        if not os.path.exists(self.theme_list_script):
            logger.warning(f"Theme script not found at {self.theme_list_script}")
            return []
        success, output = self._run_command([self.theme_list_script], read_only=True)
        return output.splitlines() if success else []

    def apply_theme(self, theme: str):
        """Applies the selected theme."""
        logger.info(f"Applying theme: {theme}")
        self._write_tmp_file(self.tmp_theme_file, theme)
        self._run_command([self.theme_apply_script, theme])

    def apply_simple_theme(self, theme: str):
        """
        Applies light or dark theme for simplified environments (GNOME/XFCE/Cinnamon).

        Args:
            theme: Either "light" or "dark"
        """
        logger.info(f"Applying simple theme: {theme}")
        self._write_tmp_file(self.tmp_simple_theme_file, theme)

        desktop_env = self.get_desktop_environment()

        if theme == "dark":
            self._apply_dark_theme(desktop_env)
        else:
            self._apply_light_theme(desktop_env)

    def _apply_dark_theme(self, desktop_env: str):
        """Applies dark theme configuration."""
        logger.info("Applying dark theme configuration")

        # Set GTK4 color scheme for GNOME/Cinnamon
        if desktop_env in ["GNOME", "Cinnamon"]:
            self._run_command([
                "dconf", "write",
                "/org/gnome/desktop/interface/color-scheme",
                "'prefer-dark'"
            ])

        # Set GTK theme for each desktop environment
        if desktop_env == "Cinnamon":
            logger.info("Setting Cinnamon GTK theme to Big-Orange")
            self._run_command([
                "dconf", "write",
                "/org/cinnamon/desktop/interface/gtk-theme",
                "'Big-Orange'"
            ])
        elif desktop_env == "GNOME":
            logger.info("Setting GNOME GTK theme to Big-Blue")
            self._run_command([
                "dconf", "write",
                "/org/gnome/desktop/interface/gtk-theme",
                "'Big-Blue'"
            ])
        elif desktop_env == "XFCE":
            logger.info("Setting XFCE GTK theme to Big-Blue")
            self._run_command([
                "xfconf-query", "-c", "xsettings",
                "-p", "/Net/ThemeName",
                "-s", "Big-Blue"
            ])

        # Configure Kvantum theme
        home = os.path.expanduser("~")
        kvantum_dir = os.path.join(home, ".config", "Kvantum")
        kvantum_conf = os.path.join(kvantum_dir, "kvantum.kvconfig")

        kvantum_content = "[General]\ntheme=BigAdwaitaRoundGtkDark\n"
        self._write_user_config_file(kvantum_conf, kvantum_content)

        # Copy kdeglobals for dark theme
        kdeglobals_source = "/usr/share/sync-kde-and-gtk-places/biglinux-dark"
        kdeglobals_dest = os.path.join(home, ".config", "kdeglobals")
        if os.path.exists(kdeglobals_source):
            self._run_command(["cp", "-f", kdeglobals_source, kdeglobals_dest])
        else:
            logger.warning(f"Dark theme kdeglobals not found at {kdeglobals_source}")

        # Apply dark icon theme
        self._apply_icon_theme_variant(desktop_env, dark=True)

    def _apply_light_theme(self, desktop_env: str):
        """Applies light theme configuration."""
        logger.info("Applying light theme configuration")

        # Set GTK4 color scheme for GNOME/Cinnamon
        if desktop_env in ["GNOME", "Cinnamon"]:
            self._run_command([
                "dconf", "write",
                "/org/gnome/desktop/interface/color-scheme",
                "'default'"
            ])

        # Set GTK theme for each desktop environment
        if desktop_env == "Cinnamon":
            logger.info("Setting Cinnamon GTK theme to Big-Orange-Light")
            self._run_command([
                "dconf", "write",
                "/org/cinnamon/desktop/interface/gtk-theme",
                "'Big-Orange-Light'"
            ])
        elif desktop_env == "GNOME":
            logger.info("Setting GNOME GTK theme to Big-Blue-Light")
            self._run_command([
                "dconf", "write",
                "/org/gnome/desktop/interface/gtk-theme",
                "'Big-Blue-Light'"
            ])
        elif desktop_env == "XFCE":
            logger.info("Setting XFCE GTK theme to Big-Blue-Light")
            self._run_command([
                "xfconf-query", "-c", "xsettings",
                "-p", "/Net/ThemeName",
                "-s", "Big-Blue-Light"
            ])

        # Configure Kvantum theme
        home = os.path.expanduser("~")
        kvantum_dir = os.path.join(home, ".config", "Kvantum")
        kvantum_conf = os.path.join(kvantum_dir, "kvantum.kvconfig")

        kvantum_content = "[General]\ntheme=BigAdwaitaRoundGtk\n"
        self._write_user_config_file(kvantum_conf, kvantum_content)

        # Copy kdeglobals for light theme
        kdeglobals_source = "/usr/share/sync-kde-and-gtk-places/biglinux"
        kdeglobals_dest = os.path.join(home, ".config", "kdeglobals")
        if os.path.exists(kdeglobals_source):
            self._run_command(["cp", "-f", kdeglobals_source, kdeglobals_dest])
        else:
            logger.warning(f"Light theme kdeglobals not found at {kdeglobals_source}")

        # Apply light icon theme
        self._apply_icon_theme_variant(desktop_env, dark=False)

    def _apply_icon_theme_variant(self, desktop_env: str, dark: bool):
        """Applies appropriate icon theme variant (dark or light)."""
        logger.debug(f"Applying {'dark' if dark else 'light'} icon theme variant")

        # Get current icon theme
        icon_theme = ""
        if desktop_env == "XFCE":
            success, icon_theme = self._run_command([
                "xfconf-query", "-c", "xsettings",
                "-p", "/Net/IconThemeName"
            ], read_only=True)
            if success:
                icon_theme = icon_theme.strip()
        else:
            # GNOME or Cinnamon
            if desktop_env == "Cinnamon":
                success, icon_theme = self._run_command([
                    "dconf", "read",
                    "/org/cinnamon/desktop/interface/icon-theme"
                ], read_only=True)
            else:
                success, icon_theme = self._run_command([
                    "dconf", "read",
                    "/org/gnome/desktop/interface/icon-theme"
                ], read_only=True)

            if success:
                icon_theme = icon_theme.strip("'\"")

        if not icon_theme:
            logger.warning("Could not detect current icon theme")
            return

        # Find appropriate variant
        home = os.path.expanduser("~")
        search_paths = [
            "/usr/share/icons",
            os.path.join(home, ".local/share/icons")
        ]

        new_theme = icon_theme
        if dark:
            # Look for dark variant
            for base_path in search_paths:
                if os.path.exists(base_path):
                    # Try adding -dark suffix
                    dark_icon_path = os.path.join(base_path, f"{icon_theme}-dark")
                    if os.path.isdir(dark_icon_path):
                        new_theme = f"{icon_theme}-dark"
                        logger.debug(f"Found dark icon theme: {new_theme}")
                        break
        else:
            # Remove -dark suffix if present
            new_theme = icon_theme.replace("-dark", "").replace("-Dark", "")
            logger.debug(f"Using light icon theme: {new_theme}")

        # Apply the icon theme
        self._set_icon_theme(desktop_env, new_theme)

    def _set_icon_theme(self, desktop_env: str, theme_name: str):
        """Sets the icon theme for the desktop environment."""
        logger.info(f"Setting icon theme to: {theme_name}")

        if desktop_env == "Cinnamon":
            self._run_command([
                "dconf", "write",
                "/org/cinnamon/desktop/interface/icon-theme",
                f"'{theme_name}'"
            ])
        elif desktop_env == "XFCE":
            self._run_command([
                "xfconf-query", "-c", "xsettings",
                "-p", "/Net/IconThemeName",
                "-s", theme_name
            ])
        else:  # GNOME
            self._run_command([
                "dconf", "write",
                "/org/gnome/desktop/interface/icon-theme",
                f"'{theme_name}'"
            ])

    def finalize_setup(self, config: SetupConfig):
        """
        Performs final setup steps, including creating flag files.

        All config files are saved to /tmp during the live session.
        Calamares will copy them to /etc/big-default-config/ on the installed system.
        """
        logger.info("Finalizing setup...")

        # JamesDSP configuration - save flag to /tmp
        if config.enable_jamesdsp:
            logger.info("JamesDSP enabled, creating flag file.")
            self._run_command(["touch", self.tmp_jamesdsp_file], as_root=False)
            # Configure JamesDSP in live session
            home = os.path.expanduser("~")
            jamesdsp_conf = os.path.join(home, ".config/jamesdsp/application.conf")
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
        else:
            logger.info("JamesDSP not enabled, removing flag file if it exists.")
            self._run_command(["rm", "-f", self.tmp_jamesdsp_file], as_root=False)
            home = os.path.expanduser("~")
            jamesdsp_conf = os.path.join(home, ".config/jamesdsp/application.conf")
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

        # Display profile/ICC configuration - save flag to /tmp
        if config.enable_enhanced_contrast:
            logger.info("Enhanced contrast enabled, creating flag file.")
            self._run_command(["touch", self.tmp_display_profile_file], as_root=False)
            self._run_command(
                ["/usr/bin/icc_profile_apply", "enable"],
                as_root=False,
            )
        else:
            logger.info(
                "Enhanced contrast not enabled, removing flag file if it exists."
            )
            self._run_command(
                ["rm", "-f", self.tmp_display_profile_file], as_root=False
            )
            self._run_command(
                ["/usr/bin/icc_profile_apply", "disable"],
                as_root=False,
            )

        self._run_command(["killall", "kwin_wayland"])

    def get_desktop_image_path(self, layout_name: str) -> str:
        return self.desktop_image_path.format(layout_name)

    def get_theme_image_path(self, theme_name: str) -> str:
        return self.theme_image_path.format(theme_name)

    def apply_jamesdsp_settings(self, enabled: bool):
        """
        Applies JamesDSP configuration immediately.
        This is called when a theme is selected, based on the switch state.
        """
        home = os.path.expanduser("~")
        jamesdsp_conf = os.path.join(home, ".config/jamesdsp/application.conf")
        
        if enabled:
            logger.info("Applying JamesDSP enabled settings...")
            self._run_command(["touch", self.tmp_jamesdsp_file], as_root=False)
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
        else:
            logger.info("Applying JamesDSP disabled settings...")
            self._run_command(["rm", "-f", self.tmp_jamesdsp_file], as_root=False)
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

    def apply_icc_profile_settings(self, enabled: bool):
        """
        Applies ICC profile configuration immediately.
        This is called when a theme is selected, based on the switch state.
        """
        if enabled:
            logger.info("Applying ICC profile enabled settings...")
            self._run_command(["touch", self.tmp_display_profile_file], as_root=False)
            self._run_command(
                ["/usr/bin/icc_profile_apply", "enable"],
                as_root=False,
            )
        else:
            logger.info("Applying ICC profile disabled settings...")
            self._run_command(
                ["rm", "-f", self.tmp_display_profile_file], as_root=False
            )
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

        logger.info(f"Enhanced contrast availability: ICC={icc_profile_exists}, Wayland={wayland_running}, Result={icc_profile_exists and wayland_running}")
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
