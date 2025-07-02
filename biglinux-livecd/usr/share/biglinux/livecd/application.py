import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk, Gdk
from ui.app_window import AppWindow
import os


class Application(Adw.Application):
    def __init__(self, system_service, **kwargs):
        super().__init__(application_id="biglinux-livecd", **kwargs)
        self.system_service = system_service
        self.win = None

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)

        # --- PERFORMANCE: Add system-wide icon theme path ---
        # 1. Get the default icon theme
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        # 2. Define the system path for circle flags
        flags_dir = "/usr/share/circle-flags-svg/"
        
        # 3. Add the directory to the icon theme's search path
        if os.path.isdir(flags_dir):
            icon_theme.add_search_path(flags_dir)
        else:
            print(f"Warning: System flag icon directory not found at {flags_dir}")

        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def do_activate(self):
        """Called when the application is activated (run)."""
        if not self.win:
            self.win = AppWindow(application=self, system_service=self.system_service)
        self.win.present()
