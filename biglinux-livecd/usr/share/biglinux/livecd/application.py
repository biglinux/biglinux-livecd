import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import os
import stat

from gi.repository import Adw, Gdk, Gtk
from logging_config import get_logger
from ui.app_window import AppWindow

logger = get_logger()


class Application(Adw.Application):
    def __init__(self, system_service, **kwargs):
        super().__init__(application_id="br.com.biglinux.livecd", **kwargs)
        self.system_service = system_service
        self.win = None
        self._wizard_ready_notified = False

    def _mark_wizard_visible(self, *_args):
        """Notify systemd only after the wizard window is mapped."""
        if self._wizard_ready_notified:
            return

        runtime_directory = os.environ.get("XDG_RUNTIME_DIR", "")
        expected_directory = f"/run/user/{os.getuid()}"
        try:
            directory_stat = os.lstat(runtime_directory)
        except OSError as error:
            logger.warning(f"Could not inspect runtime directory: {error}")
            return
        if (
            runtime_directory != expected_directory
            or not stat.S_ISDIR(directory_stat.st_mode)
            or directory_stat.st_uid != os.getuid()
        ):
            logger.warning("Refusing unsafe runtime directory for wizard-ready marker")
            return

        marker = os.path.join(runtime_directory, "biglinux-live-wizard-ready")
        flags = os.O_WRONLY | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
        try:
            descriptor = os.open(marker, flags, 0o600)
            os.close(descriptor)
        except OSError as error:
            logger.warning(f"Could not create wizard-ready marker: {error}")
            return
        self._wizard_ready_notified = True

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)

        # Add icon search paths
        display = Gdk.Display.get_default()
        if display is None:
            logger.error("No graphical display is available")
            return
        icon_theme = Gtk.IconTheme.get_for_display(display)

        # Local icons (theme icons)
        icons_dir = "/usr/share/biglinux/livecd/assets/icons/"
        if os.path.isdir(icons_dir):
            icon_theme.add_search_path(icons_dir)

        # Circle flags
        flags_dir = "/usr/share/circle-flags-svg/"
        if os.path.isdir(flags_dir):
            icon_theme.add_search_path(flags_dir)
        else:
            logger.warning(f"System flag icon directory not found at {flags_dir}")

        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def do_activate(self):
        """Called when the application is activated (run)."""
        if not self.win:
            self.win = AppWindow(application=self, system_service=self.system_service)
            self.win.connect("map", self._mark_wizard_visible)
        self.win.present()
