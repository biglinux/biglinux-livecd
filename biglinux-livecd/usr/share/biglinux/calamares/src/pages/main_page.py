# src/pages/main_page.py

"""
Main Page for BigLinux Calamares Configuration Tool
Initial page with three main options: Maintenance, Installation, and Minimal
"""

import logging
import os
import subprocess
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject
from ..utils.i18n import _
from ..utils.widgets import create_option_card
from ..services import get_system_service, get_install_service


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


class MainPage(Gtk.Box):
    """Main page with three installation/maintenance options"""

    __gsignals__ = {
        'navigate': (GObject.SignalFlags.RUN_FIRST, None, (str, object))
    }

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.FILL,
            hexpand=True,
            vexpand=True
        )

        self.logger = logging.getLogger(__name__)
        self.system_service = get_system_service()
        self.install_service = get_install_service()

        # Detect XivaStudio for branding
        self.is_xivastudio = is_xivastudio_system()
        self.distro_name = "XivaStudio" if self.is_xivastudio else "BigLinux"

        self.add_css_class("main-page")
        
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self.create_content()
        self.logger.debug("MainPage initialized")

    def _create_option_card(self, icon_name, title, description, button_text, button_style, callback, description2=None):
        """Factory function to create a card widget. Delegates to shared utility."""
        return create_option_card(
            icon_name=icon_name,
            title=title,
            description=description,
            button_text=button_text,
            button_style=button_style,
            callback=callback,
            description2=description2
        )

    def _get_normal_user(self):
        """Detect normal user by finding the first folder in /home."""
        try:
            home_dirs = [d for d in os.listdir('/home') if os.path.isdir(os.path.join('/home', d))]
            if home_dirs:
                return home_dirs[0]
        except Exception as e:
            self.logger.warning(f"Failed to detect normal user: {e}")
        return None

    def _on_forum_link_activated(self, label, uri):
        """Handle forum link click - open with normal user, not root."""
        user = self._get_normal_user()
        
        try:
            if user:
                # Open browser as normal user using su
                subprocess.Popen(
                    ['su', user, '-c', f'xdg-open {uri}'],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Fallback to direct open
                subprocess.Popen(
                    ['xdg-open', uri],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception as e:
            self.logger.error(f"Failed to open forum link: {e}")
        
        # Return True to prevent default handler from opening the link as root
        return True

    def _create_system_info_bar(self):
        """Factory function to create the system info bar."""
        system_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        system_info_box.set_margin_top(8)
        system_info_box.set_margin_bottom(8)
        system_info_box.set_margin_start(12)
        system_info_box.set_margin_end(12)

        boot_mode = self.system_service.get_boot_mode()
        kernel_version = self.system_service.get_kernel_version()
        session_type = self.system_service.get_session_type()
        
        markup = (
            f"{_('The system is in')} <b>{boot_mode}</b>, "
            f"Linux <b>{kernel_version}</b> {_('and graphical mode')} <b>{session_type}</b>."
        )
        
        info_label = Gtk.Label(
            use_markup=True, label=markup, wrap=True,
            justify=Gtk.Justification.CENTER, halign=Gtk.Align.CENTER
        )
        system_info_box.append(info_label)

        # Use a label with markup for the forum link
        forum_label = Gtk.Label(
            use_markup=True,
            label=_('<a href="https://forum.biglinux.com.br">This is a collaborative system, if you need help consult our forum.</a>'),
            halign=Gtk.Align.CENTER
        )
        # Connect to activate-link to handle the click ourselves
        forum_label.connect("activate-link", self._on_forum_link_activated)
        system_info_box.append(forum_label)
        
        return system_info_box

    def create_content(self):
        """Create the main page content."""
        main_content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            valign=Gtk.Align.CENTER,
            vexpand=True
        )
        self.append(main_content_box)

        clamp = Adw.Clamp(maximum_size=1000)
        main_content_box.append(clamp)

        grid_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=24,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            homogeneous=True
        )
        clamp.set_child(grid_box)

        maintenance_card = self._create_option_card(
            icon_name="applications-utilities",
            title=_("Maintenance"),
            description=_("Tools that facilitate the maintenance of the installed system."),
            button_text=_("Restore"),
            button_style="secondary",
            callback=self.on_maintenance_clicked
        )
        grid_box.append(maintenance_card)

        self.installation_card = self._create_option_card(
            icon_name="system-software-install",
            title=_("Installation"),
            description=_("The system is in live mode, which has limitations."),
            description2=_("Install it for a complete experience."),
            button_text=_("Install"),
            button_style="suggested-action",
            callback=self.on_installation_clicked
        )
        grid_box.append(self.installation_card)

        minimal_card = self._create_option_card(
            icon_name="preferences-system",
            title=_("Minimal"),
            description=_("Remove pre-selected software to create a lean, personalized system."),
            button_text=_("Continue"),
            button_style="secondary",
            callback=self.on_minimal_clicked
        )
        grid_box.append(minimal_card)

        system_info_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            valign=Gtk.Align.END,
            vexpand=False
        )
        self.append(system_info_container)
        system_info_widget = self._create_system_info_bar()
        system_info_container.append(system_info_widget)

    def on_maintenance_clicked(self, button):
        self.logger.info("Maintenance option selected")
        self.emit('navigate', 'maintenance', None)

    def on_installation_clicked(self, button):
        """Handle installation button click.
        
        For XivaStudio systems with internet:
        - Configures Calamares to show netinstall page for multimedia packages
        
        For all systems:
        - Configures standard installation and proceeds to tips page
        """
        self.logger.info("Installation option selected")
        try:
            button.set_sensitive(False)
            button.set_label(_("Starting..."))
            
            # Check installation requirements
            requirements = self.install_service.check_installation_requirements()
            missing = [k for k, v in requirements.items() if not v]
            if missing:
                self.logger.warning(f"Installation requirements not met: {missing}")
                self.reset_button_state(button, _("Install"))
                return
            
            # Configure XivaStudio netinstall if applicable
            # This modifies Calamares settings to show multimedia package selection
            if self.is_xivastudio:
                self.logger.info("XivaStudio detected, checking internet for netinstall...")
                button.set_label(_("Checking connection..."))
                
                if self.install_service.check_internet_connection():
                    self.logger.info("Internet available, configuring XivaStudio netinstall")
                    if not self.install_service.configure_xivastudio_netinstall():
                        self.logger.warning("Failed to configure XivaStudio netinstall")
                else:
                    self.logger.info("No internet - XivaStudio netinstall disabled")
            
            button.set_label(_("Configuring..."))
            
            # Configure standard installation
            if self.install_service.start_installation("btrfs", packages_to_remove=[]):
                self.logger.info("Installation configured successfully")
                self.emit('navigate', 'tips', None)
            else:
                self.logger.error("Failed to configure installation")
                self.reset_button_state(button, _("Install"))
                
        except Exception as e:
            self.logger.error(f"Installation configuration failed: {e}")
            self.reset_button_state(button, _("Install"))

    def on_minimal_clicked(self, button):
        self.logger.info("Minimal installation option selected")
        self.emit('navigate', 'minimal', None)

    def reset_button_state(self, button, original_text):
        button.set_sensitive(True)
        button.set_label(original_text)

    def on_page_activated(self):
        self.logger.debug("MainPage activated")
        # Reset installation button state when returning to this page
        if hasattr(self, 'installation_card') and hasattr(self.installation_card, 'action_button'):
            self.reset_button_state(self.installation_card.action_button, _("Install"))

    def cleanup(self):
        self.logger.debug("MainPage cleanup")

GObject.type_register(MainPage)
