# src/window.py

"""
Main Window class for BigLinux Calamares Configuration Tool
Manages navigation between different pages using Gtk.Stack
"""

import logging
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw
from .utils.i18n import _
from .utils.constants import DEFAULTS
from .pages import MainPage, MaintenancePage, MinimalPage, TipsPage


# XivaStudio detection paths
XIVASTUDIO_LOGO_PNG = "/usr/share/pixmaps/icon-logo-xivastudio.png"
XIVASTUDIO_LOGO_GIF = "/usr/share/pixmaps/icon-logo-xivastudio.gif"


def is_xivastudio_system() -> bool:
    """
    Check if the system is XivaStudio by looking for logo files.
    
    Returns:
        True if XivaStudio is detected, False otherwise.
    """
    return os.path.exists(XIVASTUDIO_LOGO_PNG) or os.path.exists(XIVASTUDIO_LOGO_GIF)


class CalamaresWindow(Adw.ApplicationWindow):
    """Main application window with navigation stack and ToolbarView layout."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.logger = logging.getLogger(__name__)
        self.continue_signal_handler = None
        self.check_all_handler = None
        self.uncheck_all_handler = None
        self.back_signal_handler = None

        # Detect XivaStudio system for branding
        self.is_xivastudio = is_xivastudio_system()
        self.distro_name = "XivaStudio" if self.is_xivastudio else "BigLinux"

        self.setup_window()
        self.create_layout()
        self.create_pages()
        self.setup_navigation()

        self.logger.info("Main window initialized")

    def setup_window(self):
        """Configure window properties."""
        self.set_title(_("{distro} Installation").format(distro=self.distro_name))
        # Use constants for window sizing to ensure configurability.
        self.set_default_size(DEFAULTS['window_width'], DEFAULTS['window_height'])
        self.set_size_request(DEFAULTS['min_window_width'], DEFAULTS['min_window_height'])
        # Icon removed from the window itself to create a cleaner header bar.
        # The app icon will be handled by the .desktop file.
        self.set_deletable(True)

    def create_layout(self):
        """Create the main window layout using Adw.ToolbarView."""
        self.main_view = Adw.ToolbarView()
        self.set_content(self.main_view)

        self.header_bar = Adw.HeaderBar()
        self.main_view.add_top_bar(self.header_bar)

        self.toast_overlay = Adw.ToastOverlay()
        self.main_view.set_content(self.toast_overlay)
        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=300
        )
        self.toast_overlay.set_child(self.stack)

        # Bottom navigation bar
        nav_bar_container = Gtk.Box()
        nav_bar_container.add_css_class("toolbar")
        self.main_view.add_bottom_bar(nav_bar_container)
        
        self.nav_bar = Adw.Bin()
        nav_bar_container.append(self.nav_bar)

        nav_box = Gtk.Box(spacing=12)
        nav_box.set_margin_top(6)
        nav_box.set_margin_bottom(6)
        nav_box.set_margin_start(12)
        nav_box.set_margin_end(12)
        self.nav_bar.set_child(nav_box)

        # Container for buttons on the left (start)
        self.start_box = Gtk.Box(spacing=6)
        nav_box.append(self.start_box)

        # Container for centered buttons
        self.center_box = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER, hexpand=True)
        nav_box.append(self.center_box)

        # Container for buttons on the right (end)
        self.end_box = Gtk.Box(spacing=6)
        nav_box.append(self.end_box)

        # Create buttons and re-apply .pill style for a consistent rounded look.
        self.back_button = Gtk.Button(label=_("Back"))
        self.back_button.add_css_class("pill")

        self.check_all_button = Gtk.Button(label=_("Keep All"))
        self.check_all_button.add_css_class("pill")

        self.uncheck_all_button = Gtk.Button(label=_("Remove All"))
        self.uncheck_all_button.add_css_class("pill")

        self.continue_button = Gtk.Button(label=_("Continue"))
        self.continue_button.add_css_class("suggested-action")
        self.continue_button.add_css_class("pill")


    def create_pages(self):
        """Create and add all pages to the stack."""
        self.pages = {
            "main": MainPage(),
            "maintenance": MaintenancePage(),
            "minimal": MinimalPage(),
            "tips": TipsPage()
        }

        for name, page in self.pages.items():
            page.connect("navigate", self.on_navigate_requested)
            self.stack.add_named(page, name)

    def setup_navigation(self):
        self.navigate_to("main")

    def on_navigate_requested(self, widget, page_name, data=None):
        self.logger.info(f"Navigation requested to: {page_name}")
        if page_name == "back":
            self.navigate_back()
        else:
            self.navigate_to(page_name, data)

    def navigate_to(self, page_name, data=None):
        if page_name not in self.pages:
            self.logger.error(f"Page '{page_name}' not found")
            return
        self.stack.set_visible_child_name(page_name)
        self.update_navigation_state(page_name)
        current_page = self.stack.get_visible_child()
        
        # Pass data to the page if it supports it
        if data and hasattr(current_page, 'set_navigation_data'):
            current_page.set_navigation_data(data)
        
        if hasattr(current_page, 'on_page_activated'):
            current_page.on_page_activated()

    def navigate_back(self, button=None):
        current_page_name = self.stack.get_visible_child_name()
        if current_page_name in ["maintenance", "minimal", "tips"]:
             self.navigate_to("main")
        else:
            self.navigate_to("main")

    def clear_nav_boxes(self):
        """Remove all children from navigation boxes."""
        for box in [self.start_box, self.center_box, self.end_box]:
            child = box.get_first_child()
            while child:
                box.remove(child)
                child = box.get_first_child()

    def disconnect_signals(self):
        """Disconnect all dynamic signal handlers."""
        if self.continue_signal_handler:
            self.continue_button.disconnect(self.continue_signal_handler)
            self.continue_signal_handler = None
        if self.check_all_handler:
            self.check_all_button.disconnect(self.check_all_handler)
            self.check_all_handler = None
        if self.uncheck_all_handler:
            self.uncheck_all_button.disconnect(self.uncheck_all_handler)
            self.uncheck_all_handler = None
        if self.back_signal_handler:
            self.back_button.disconnect(self.back_signal_handler)
            self.back_signal_handler = None

    def update_navigation_state(self, page_name):
        """Update the entire navigation UI based on the current page."""
        self.disconnect_signals()
        self.clear_nav_boxes()

        current_page = self.pages[page_name]
        is_main_page = (page_name == "main")
        
        self.nav_bar.set_visible(not is_main_page)
        self.back_button.remove_css_class("suggested-action")  # Reset style
        
        # Reset button states - they may have been disabled by previous page
        self.continue_button.set_sensitive(True)
        self.back_button.set_sensitive(True)

        # Define titles - use distro_name for branding
        titles = {
            "main": _("{distro} Installation").format(distro=self.distro_name),
            "maintenance": _("System Maintenance"),
            "minimal": _("Uncheck the programs you want to remove"),
            "tips": _("Installation Tips"),
        }
        default_title = _("{distro} Installation").format(distro=self.distro_name)
        self.header_bar.set_title_widget(
            Adw.WindowTitle(title=titles.get(page_name, default_title))
        )

        if not is_main_page:
            self.back_signal_handler = self.back_button.connect("clicked", self.navigate_back)

            if page_name == "maintenance":
                self.center_box.append(self.back_button)
                self.back_button.add_css_class("suggested-action") # Blue button as requested
            
            elif page_name == "minimal":
                self.start_box.append(self.back_button)
                self.center_box.append(self.uncheck_all_button)
                self.center_box.append(self.check_all_button)
                self.end_box.append(self.continue_button)

                self.continue_button.set_label(_("Continue"))
                self.continue_signal_handler = self.continue_button.connect("clicked", lambda btn: current_page.do_continue_action(btn))
                self.check_all_handler = self.check_all_button.connect("clicked", current_page.on_check_all_clicked)
                self.uncheck_all_handler = self.uncheck_all_button.connect("clicked", current_page.on_uncheck_all_clicked)

            elif page_name == "tips":
                # Tips page only has centered Install button, no back button
                self.center_box.append(self.continue_button)
                
                self.continue_button.set_label(_("Continue"))
                self.continue_signal_handler = self.continue_button.connect("clicked", lambda btn: current_page.do_continue_action(btn))

    def show_toast(self, toast):
        if self.toast_overlay:
            self.toast_overlay.add_toast(toast)

    def show_error_toast(self, message, timeout=5):
        self.show_toast(Adw.Toast(title=message, timeout=timeout))

    def show_success_toast(self, message, timeout=3):
        self.show_toast(Adw.Toast(title=message, timeout=timeout))

    def cleanup(self):
        self.logger.info("Window cleanup started")
        self.disconnect_signals()
        for page in self.pages.values():
            if hasattr(page, 'cleanup'):
                page.cleanup()
        self.logger.info("Window cleanup completed")
