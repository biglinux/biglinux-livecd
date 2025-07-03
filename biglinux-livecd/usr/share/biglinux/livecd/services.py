import subprocess
import os
import re
from typing import List, Tuple
from config import SetupConfig


class SystemService:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        if self.test_mode:
            print("--- RUNNING IN TEST MODE: No system changes will be applied. ---")

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

        # Temp files for script compatibility
        self.tmp_lang_file = "/tmp/big_language"
        self.tmp_keyboard_file = "/tmp/big_keyboard"
        self.tmp_desktop_file = "/tmp/big_desktop_changed"
        self.tmp_theme_file = "/tmp/big_desktop_theme"

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
            print(
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
            print(f"Error: {err_msg}")
            return False, err_msg
        except subprocess.CalledProcessError as e:
            err_msg = f"Error running command '{' '.join(e.cmd)}': {e.stderr}"
            print(err_msg)
            return False, e.stderr.strip()
        except Exception as e:
            err_msg = f"An unexpected error occurred with command '{' '.join(command)}': {e}"
            print(err_msg)
            return False, str(e)


    def _write_tmp_file(self, filepath: str, content: str):
        """Helper to write to a temp file."""
        if self.test_mode:
            print(
                f"[TEST MODE] Suppressed write to {filepath}: '{content[:50]}{'...' if len(content) > 50 else ''}'"
            )
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            print(f"Error writing to {filepath}: {e}")

    def _write_user_config_file(self, filepath: str, content: str):
        """Helper to write a file in the user's home directory."""
        if self.test_mode:
            print(
                f"[TEST MODE] Suppressed write to {filepath}: '{content[:50]}{'...' if len(content) > 50 else ''}'"
            )
            return
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            print(f"Error writing to {filepath}: {e}")

    def apply_language_settings(self, lang_code: str, timezone: str):
        """Applies language, locale, and timezone settings."""
        print(f"Setting language to {lang_code} and timezone to {timezone}")
        self._write_tmp_file(self.tmp_lang_file, lang_code)

        self._run_command(["timedatectl", "set-timezone", timezone], as_root=True)
        self._run_command(["timedatectl", "set-ntp", "1"], as_root=True)
        self._run_command(
            ["localectl", "set-locale", f"LANG={lang_code}.UTF-8"], as_root=True
        )
        self._run_command(["/usr/share/biglinux/livecd/script/biglinux-verify-md5sum.sh"], as_root=False)

    def apply_keyboard_layout(self, layout: str):
        """Applies the selected keyboard layout."""
        print(f"Setting keyboard layout to: {layout}")
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
            print(f"Warning: Desktop script not found at {self.desktop_list_script}")
            return []
        success, output = self._run_command([self.desktop_list_script], read_only=True)
        return output.splitlines() if success else []

    def apply_desktop_layout(self, layout: str):
        """Applies the selected desktop layout."""
        print(f"Applying desktop layout: {layout}")
        self._write_tmp_file(self.tmp_desktop_file, layout)
        self._run_command([self.desktop_apply_script, layout, "quiet"])

    def get_available_themes(self) -> List[str]:
        """Returns a list of available theme names."""
        if not os.path.exists(self.theme_list_script):
            print(f"Warning: Theme script not found at {self.theme_list_script}")
            return []
        success, output = self._run_command([self.theme_list_script], read_only=True)
        return output.splitlines() if success else []

    def apply_theme(self, theme: str):
        """Applies the selected theme."""
        print(f"Applying theme: {theme}")
        self._write_tmp_file(self.tmp_theme_file, theme)
        self._run_command([self.theme_apply_script, theme])

    def finalize_setup(self, config: SetupConfig):
        """Performs final setup steps, including creating flag files."""
        print("Finalizing setup...")
        self._run_command(
            ["cp", "-f", self.tmp_theme_file, "/etc/default-theme-biglinux"],
            as_root=True,
        )
        self._run_command(
            ["cp", "-f", self.tmp_desktop_file, "/etc/big_desktop_changed"],
            as_root=True,
        )

        if config.enable_jamesdsp:
            print("JamesDSP enabled, creating flag file.")
            self._run_command(["touch", "/etc/big_enable_jamesdsp"], as_root=True)
            self._run_command(["sed", "-i", "s|AutoStartEnabled=false|AutoStartEnabled=true|g", "~/.config/jamesdsp/application.conf"], as_root=False)
        else:
            print("JamesDSP not enabled, removing flag file if it exists.")
            self._run_command(["rm", "-f", "/etc/big_enable_jamesdsp"], as_root=True)
            self._run_command(["sed", "-i", "s|AutoStartEnabled=true|AutoStartEnabled=false|g", "~/.config/jamesdsp/application.conf"], as_root=False)

        if config.enable_enhanced_contrast:
            print("Enhanced contrast enabled, creating flag file.")
            self._run_command(["touch", "/etc/big_improve_constrast"], as_root=True)
            self._run_command(["/usr/share/biglinux/livecd/script/icc_enable.sh"], as_root=False)
        else:
            print("Enhanced contrast not enabled, removing flag file if it exists.")
            self._run_command(["rm", "-f", "/etc/big_improve_constrast"], as_root=True)
            self._run_command(["/usr/share/biglinux/livecd/script/icc_disable.sh"], as_root=False)

        self._run_command(["killall", "kwin_wayland"])

    def get_desktop_image_path(self, layout_name: str) -> str:
        return self.desktop_image_path.format(layout_name)

    def get_theme_image_path(self, theme_name: str) -> str:
        return self.theme_image_path.format(theme_name)

    def check_jamesdsp_availability(self) -> bool:
        """Checks if JamesDSP executable exists."""
        return os.path.exists("/usr/bin/jamesdsp")

    def check_enhanced_contrast_availability(self) -> bool:
        """Checks for the AppleRGB ICC profile and if kwin_wayland is running."""
        icc_profile_exists = os.path.exists("/usr/share/color/icc/colord/ECI-RGBv1.icc")

        # Check if kwin_wayland process is running
        try:
            result = subprocess.run(
                ["pgrep", "-x", "kwin_wayland"], capture_output=True, check=False
            )
            kwin_running = result.returncode == 0
        except FileNotFoundError:
            kwin_running = False  # pgrep not found

        return icc_profile_exists and kwin_running

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
            print(f"Could not read or parse /proc/meminfo: {e}")
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
