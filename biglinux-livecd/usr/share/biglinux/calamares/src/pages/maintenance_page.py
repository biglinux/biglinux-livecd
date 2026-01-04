# src/pages/maintenance_page.py

"""
Maintenance Page for BigLinux Calamares Configuration Tool
System maintenance and restore tools page
"""

import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject
from ..utils.i18n import _
from ..services import get_system_service, get_install_service


class MaintenancePage(Gtk.Box):
    """Page with system maintenance and restore options"""

    __gsignals__ = {
        'navigate': (GObject.SignalFlags.RUN_FIRST, None, (str, object))
    }

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )

        self.logger = logging.getLogger(__name__)
        self.install_service = get_install_service()
        self.system_service = get_system_service()

        self.add_css_class("maintenance-page")
        self.set_margin_top(24)
        self.set_margin_bottom(24)

        self.create_content()
        self.logger.debug("MaintenancePage initialized")

    def _create_option_card(self, icon_name, title, description, button_text, button_style, callback, description2=None):
        """Factory function to create a card widget."""
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card_box.set_size_request(280, 320)
        card_box.set_valign(Gtk.Align.CENTER)
        card_box.set_halign(Gtk.Align.CENTER)

        card_bin = Adw.Bin()
        card_bin.add_css_class("card")
        card_box.append(card_bin)

        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.FILL,
            hexpand=True,
            vexpand=True,
            margin_top=24, margin_bottom=24, margin_start=24, margin_end=24
        )
        card_bin.set_child(content_box)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(64)
        icon.add_css_class("option-icon")
        content_box.append(icon)

        title_label = Gtk.Label(label=title, halign=Gtk.Align.CENTER)
        title_label.add_css_class("title-2")
        content_box.append(title_label)

        desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, vexpand=True, valign=Gtk.Align.CENTER)
        content_box.append(desc_box)
        
        desc_label = Gtk.Label(
            label=description, wrap=True, justify=Gtk.Justification.CENTER,
            halign=Gtk.Align.CENTER, max_width_chars=35
        )
        desc_label.add_css_class("body")
        desc_box.append(desc_label)

        if description2:
            desc2_label = Gtk.Label(
                label=description2, wrap=True, justify=Gtk.Justification.CENTER,
                halign=Gtk.Align.CENTER, max_width_chars=35
            )
            desc2_label.add_css_class("body")
            desc_box.append(desc2_label)

        button = Gtk.Button(label=button_text, halign=Gtk.Align.CENTER, valign=Gtk.Align.END)
        button.add_css_class(button_style)
        button.add_css_class("pill")
        button.connect("clicked", callback)
        content_box.append(button)
        
        return card_box

    def create_content(self):
        """Create the maintenance page content."""
        clamp = Adw.Clamp(maximum_size=1200)
        self.append(clamp)

        grid_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=24,
            halign=Gtk.Align.CENTER,
            homogeneous=True
        )
        grid_box.set_margin_start(24)
        grid_box.set_margin_end(24)
        clamp.set_child(grid_box)

        snapshot_card = self._create_option_card(
            icon_name="document-save-as",
            title=_("Snapshot and backups"),
            description=_("Restore restore points of the installed system."),
            button_text=_("Start"),
            button_style="secondary",
            callback=self.on_snapshot_clicked
        )
        grid_box.append(snapshot_card)

        restore_card = self._create_option_card(
            icon_name="document-revert",
            title=_("Restore system settings"),
            description=_("Utility that facilitates the restoration of the installed system, especially the restoration of the system boot (Grub).\n\nIt can also be used to access the package manager and terminal of the installed system."),
            button_text=_("Start"),
            button_style="suggested-action",
            callback=self.on_restore_clicked
        )
        grid_box.append(restore_card)

        if self.system_service.can_manage_efi_entries():
            efi_card = self._create_option_card(
                icon_name="drive-harddisk-system",
                title=_("EFI Entry Manager"),
                description=_("Advanced tool to add, remove, or change boot entries in the UEFI firmware."),
                button_text=_("Start"),
                button_style="secondary",
                callback=self.on_efi_manager_clicked
            )
            grid_box.append(efi_card)

    def on_restore_clicked(self, button):
        self.logger.info("System restore tool requested")
        self.install_service.start_maintenance_tool('grub_restore')

    def on_snapshot_clicked(self, button):
        self.logger.info("Snapshot backup tool requested")
        self.install_service.start_maintenance_tool('timeshift')

    def on_efi_manager_clicked(self, button):
        self.logger.info("EFI Entry Manager requested")
        self.install_service.start_maintenance_tool('efi_manager')

    def on_page_activated(self):
        self.logger.debug("MaintenancePage activated")

    def cleanup(self):
        self.logger.debug("MaintenancePage cleanup")

GObject.type_register(MaintenancePage)
