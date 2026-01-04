# src/pages/tips_page.py

"""
Tips Page for BigLinux Calamares Configuration Tool
Installation tips and guidance page using Adw.PreferencesPage.
"""

import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject
from ..utils.i18n import _


class TipsPage(Gtk.Box):
    """Page displaying installation tips and guidance, clamped for readability."""

    __gsignals__ = {
        'navigate': (GObject.SignalFlags.RUN_FIRST, None, (str, object))
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.logger = logging.getLogger(__name__)

        clamp = Adw.Clamp(maximum_size=800, vexpand=True, valign=Gtk.Align.FILL)
        self.append(clamp)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        clamp.set_child(scrolled)

        self.page = Adw.PreferencesPage()
        scrolled.set_child(self.page)
        
        self.page.set_title(_("Important Tips"))
        self.page.set_icon_name("dialog-information-symbolic")

        self.create_content()
        self.logger.debug("TipsPage initialized")

    def create_content(self):
        """Create the tips page content using Adw.PreferencesGroup."""
        tips_group = Adw.PreferencesGroup(
            title=_("Manual Partitioning Recommendations"),
            description=_("If you opt for automatic partitioning, these tips will be applied by default.")
        )
        self.page.add(tips_group)

        tips_data = [
            {'title': _("Use BTRFS"), 'description': _("This file system allows for automatic compression and restore points.")},
            {'title': _("Keep /boot within the / partition"), 'description': _("Placing it in a separate partition hampers BTRFS snapshots.")},
            {'title': _("Do not create a SWAP partition"), 'description': _("We have implemented dynamic virtual memory management with Zram and SWAP files. SWAP partitions will not be used.")}
        ]

        for tip in tips_data:
            row = Adw.ActionRow(title=tip['title'], subtitle=tip['description'])
            row.set_title_lines(1)
            row.set_subtitle_lines(2)
            tips_group.add(row)

    def do_continue_action(self, button):
        """This method is called by the main window's continue button."""
        self.logger.info("Continue from tips page - closing application")

        try:
            self.logger.info("The installer will now proceed...")
            application = self.get_root().get_application()
            if application:
                button.set_sensitive(False)
                GObject.timeout_add(1000, application.quit)
        except Exception as e:
            self.logger.error(f"Error closing application: {e}")

    def on_page_activated(self):
        self.logger.info("User reached tips page - installation configured")

    def cleanup(self):
        self.logger.debug("TipsPage cleanup")

GObject.type_register(TipsPage)
