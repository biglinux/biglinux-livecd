import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import os

from gi.repository import Adw, Gdk, Gtk
from logging_config import get_logger
from ui.app_window import AppWindow

logger = get_logger()


class Application(Adw.Application):
    def __init__(self, system_service, **kwargs):
        super().__init__(application_id="biglinux-livecd", **kwargs)
        self.system_service = system_service
        self.win = None

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)

        # Add icon search paths
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

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
        self.win.present()
