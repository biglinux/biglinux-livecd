# src/pages/minimal_page.py

"""
Minimal Page for BigLinux Calamares Configuration Tool
Package selection page for minimal installation
"""

import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, GLib
from ..utils.i18n import _
from ..services import get_package_service, get_install_service
from ..services.package_service import Package


class MinimalPage(Gtk.Box):
    """Page for selecting packages to remove in minimal installation"""

    __gsignals__ = {
        'navigate': (GObject.SignalFlags.RUN_FIRST, None, (str, object))
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.logger = logging.getLogger(__name__)
        self.package_service = get_package_service()
        self.install_service = get_install_service()
        
        self.packages = []  # The data model: list of Package objects
        self.package_rows = {} # The view: maps package name to its Adw.ActionRow

        self.loading_box = None
        self.packages_listbox = None
        self.add_css_class("minimal-page")
        self.create_content()
        self.load_packages()
        self.logger.debug("MinimalPage initialized")

    def create_content(self):
        """Create the minimal page content with proper Adwaita layout."""
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        clamp = Adw.Clamp(maximum_size=800)
        scrolled.set_child(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        clamp.set_child(content_box)

        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True, margin_top=48)
        spinner = Gtk.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, vexpand=True)
        spinner.start()
        status_label = Gtk.Label(label=_("Loading packages..."), halign=Gtk.Align.CENTER)
        status_label.add_css_class("dim-label")
        self.loading_box.append(spinner)
        self.loading_box.append(status_label)
        content_box.append(self.loading_box)

        self.packages_listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, visible=False)
        self.packages_listbox.add_css_class("boxed-list")
        self.packages_listbox.set_margin_top(12)
        self.packages_listbox.set_margin_bottom(12)
        content_box.append(self.packages_listbox)

    def load_packages(self):
        """Load packages asynchronously."""
        def load_async():
            try:
                packages = self.package_service.get_minimal_packages()
                GLib.idle_add(self.on_packages_loaded, packages)
            except Exception as e:
                self.logger.error(f"Failed to load packages: {e}")
                GLib.idle_add(self.on_packages_load_error, str(e))
        import threading
        threading.Thread(target=load_async, daemon=True).start()

    def on_packages_loaded(self, packages: list[Package]):
        self.packages = packages
        self.logger.info(f"Loaded {len(packages)} packages")
        
        # Clear previous state
        self.package_rows.clear()
        child = self.packages_listbox.get_first_child()
        while child:
            self.packages_listbox.remove(child)
            child = self.packages_listbox.get_first_child()

        self.loading_box.set_visible(False)
        self.packages_listbox.set_visible(True)

        for package in self.packages:
            package.selected = True # Default to keep all
            row = self._create_package_row(package)
            self.packages_listbox.append(row)
            self.package_rows[package.name] = row

    def _create_package_row(self, package: Package) -> Adw.ActionRow:
        """Factory function to create a package row."""
        row = Adw.ActionRow(title=package.name, title_lines=1, subtitle="")
        row.add_css_class("package-row")

        icon_image = Gtk.Image()
        icon_image.set_pixel_size(36)
        
        # Use GTK icon name lookup - this works correctly as root
        # and properly handles icon themes without sandbox issues
        icon_name = package.icon if package.icon else "package-x-generic"
        self.logger.debug(f"Setting icon for '{package.name}': {icon_name}")
        icon_image.set_from_icon_name(icon_name)
        
        row.add_prefix(icon_image)

        switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=package.selected)
        switch.connect("notify::active", self.on_package_toggled, package)
        row.add_suffix(switch)
        row.set_activatable_widget(switch)

        self._update_row_style(row, package.selected)
        return row

    def on_package_toggled(self, switch: Gtk.Switch, _, package: Package):
        """Handle switch toggle for a package."""
        to_keep = switch.get_active()
        package.selected = to_keep
        self.logger.debug(f"Package {package.name} will be kept: {to_keep}")
        
        row = self.package_rows.get(package.name)
        if row:
            self._update_row_style(row, to_keep)

    def _update_row_style(self, row: Adw.ActionRow, to_keep: bool):
        """Update visual state. Dim items that will be REMOVED (switch is OFF)."""
        if to_keep:
            row.remove_css_class("dim-label")
        else:
            row.add_css_class("dim-label")

    def on_packages_load_error(self, error_message):
        self.loading_box.get_first_child().stop()
        self.loading_box.get_last_child().set_text(_("Failed to load packages: {}").format(error_message))
        self.loading_box.get_last_child().add_css_class("error")

    def on_check_all_clicked(self, button):
        """Corresponds to 'Keep All'"""
        self.set_all_selected(True)
        self.logger.info("All optional programs will be kept")

    def on_uncheck_all_clicked(self, button):
        """Corresponds to 'Remove All'"""
        self.set_all_selected(False)
        self.logger.info("All optional programs selected for removal")

    def set_all_selected(self, selected: bool):
        for package in self.packages:
            package.selected = selected
        
        for name, row in self.package_rows.items():
            switch = row.get_activatable_widget()
            if switch and switch.get_active() != selected:
                switch.set_active(selected)
            self._update_row_style(row, selected)

    def do_continue_action(self, button):
        """This method is called by the main window's continue button."""
        self.logger.info("Continue with minimal installation")
        packages_to_remove = [pkg.name for pkg in self.packages if not pkg.selected]

        if not packages_to_remove:
            self.logger.info("No programs selected for removal. Proceeding with standard installation.")
        
        button.set_sensitive(False)
        button.set_label(_("Starting..."))

        def reset_button_state():
            button.set_sensitive(True)
            button.set_label(_("Continue"))

        try:
            success = self.install_service.start_installation(
                filesystem_type="btrfs",
                packages_to_remove=packages_to_remove
            )
            if success:
                self.logger.info("Minimal installation configured successfully")
                self.emit('navigate', 'tips', None)
            else:
                self.logger.error("Failed to configure minimal installation")
                reset_button_state()
        except Exception as e:
            self.logger.error(f"Failed to configure minimal installation: {e}", exc_info=True)
            reset_button_state()

    def on_page_activated(self):
        self.logger.debug("MinimalPage activated")
        if not self.packages:
            self.load_packages()

    def cleanup(self):
        self.logger.debug("MinimalPage cleanup")
        self.package_rows.clear()
        self.packages.clear()

GObject.type_register(MinimalPage)
