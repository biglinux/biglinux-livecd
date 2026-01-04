"""
Main GTK4 Application class for BigLinux Calamares Configuration Tool
"""

import logging
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib
from .window import CalamaresWindow
from .utils.i18n import _


class CalamaresApp(Adw.Application):
    """Main application class following GNOME HIG guidelines"""

    def __init__(self):
        super().__init__(
            application_id="com.biglinux.calamares-config",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        
        # Set the desktop file and icon name for proper Wayland taskbar integration
        GLib.set_prgname("com.biglinux.calamares-config")
        GLib.set_application_name("BigLinux Installation")

        self.logger = logging.getLogger(__name__)
        self.window = None

        # Connect application signals
        self.connect("activate", self.on_activate)
        self.connect("shutdown", self.on_shutdown)

        # Setup application actions
        self.setup_actions()

        # Setup application menu and keyboard shortcuts
        self.setup_menu()

    def setup_actions(self):
        """Setup application-wide actions"""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_action)
        self.add_action(quit_action)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)

        # Preferences action (if needed in future)
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self.on_preferences_action)
        self.add_action(preferences_action)

    def setup_menu(self):
        """Setup keyboard shortcuts"""
        # Quit shortcut
        self.set_accels_for_action("app.quit", ["<Control>q"])

        # About shortcut
        self.set_accels_for_action("app.about", ["F1"])

    def on_activate(self, app):
        """Called when application is activated"""
        self.logger.info("Application activated")

        # Initialize services first
        from .services import initialize_services

        initialize_services()

        # Create main window if it doesn't exist
        if not self.window:
            self.window = CalamaresWindow(application=self)

        # Present the window
        self.window.present()

    def on_shutdown(self, app):
        """Called when application is shutting down"""
        self.logger.info("Application shutting down")

        # Cleanup resources if needed
        if self.window:
            self.window.cleanup()

    def on_quit_action(self, action, param):
        """Handle quit action"""
        self.logger.info("Quit action triggered")
        self.quit()

    def on_about_action(self, action, param):
        """Show about dialog"""
        if not self.window:
            return

        about_dialog = Adw.AboutWindow(
            transient_for=self.window,
            modal=True,
            application_name=_("BigLinux Calamares Config"),
            application_icon="system-software-install",
            version="1.0.0",
            developer_name="BigLinux Team",
            website="https://www.biglinux.com.br",
            support_url="https://forum.biglinux.com.br",
            issue_url="https://github.com/biglinux/biglinux-calamares-config",
            license_type=Gtk.License.GPL_3_0,
            copyright="© 2024 BigLinux Team",
            developers=[
                "BigLinux Development Team",
            ],
            designers=[
                "BigLinux Design Team",
            ],
        )

        about_dialog.add_link(_("Forum"), "https://forum.biglinux.com.br")
        about_dialog.add_link(
            _("Documentation"),
            "https://github.com/biglinux/biglinux-calamares-config/wiki",
        )

        about_dialog.present()

    def on_preferences_action(self, action, param):
        """Handle preferences action (placeholder for future use)"""
        self.logger.info("Preferences action triggered")

        # Create a simple toast notification for now
        if self.window:
            toast = Adw.Toast(title=_("Preferences not implemented yet"), timeout=3)
            self.window.show_toast(toast)

    def show_error_dialog(self, title, message, details=None):
        """Show error dialog to user"""
        if not self.window:
            return

        dialog = Adw.MessageDialog(
            transient_for=self.window, modal=True, heading=title, body=message
        )

        if details:
            dialog.set_body_use_markup(True)
            dialog.set_body(f"{message}\n\n<tt>{details}</tt>")

        dialog.add_response("ok", _("OK"))
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")

        dialog.present()

    def show_confirmation_dialog(self, title, message, callback):
        """Show confirmation dialog with callback"""
        if not self.window:
            return

        dialog = Adw.MessageDialog(
            transient_for=self.window, modal=True, heading=title, body=message
        )

        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("confirm", _("Confirm"))
        dialog.set_default_response("confirm")
        dialog.set_close_response("cancel")

        def on_response(dialog, response):
            if response == "confirm" and callback:
                callback()

        dialog.connect("response", on_response)
        dialog.present()
