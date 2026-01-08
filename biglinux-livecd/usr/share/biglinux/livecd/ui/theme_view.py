# ui/theme_view.py

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import os

from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk
from logging_config import get_logger
from services import SystemService
from translations import _
from ui.base_view import BaseItemView

logger = get_logger()


class ThemeListItem(GObject.Object):
    """GObject wrapper for theme data."""

    __gtype_name__ = "ThemeListItem"

    def __init__(self, name, system_service: SystemService):
        super().__init__()
        self.name = name
        self.image_path = system_service.get_theme_image_path(name)


class ThemeView(BaseItemView):
    __gtype_name__ = "ThemeView"
    sig_theme_selected = GObject.Signal("theme-selected", arg_types=[str])

    def __init__(self, system_service: SystemService, simplified_mode: bool = False, **kwargs):
        self.jamesdsp_switch = None
        self.contrast_switch = None
        self._system_service = system_service  # Store reference for ICC callbacks
        self.simplified_mode = simplified_mode

        self.jamesdsp_available = system_service.check_jamesdsp_availability()

        # Contrast toggle only for GNOME in simplified environments
        if simplified_mode:
            desktop_env = system_service.get_desktop_environment()
            logger.info(f"ThemeView simplified mode - Desktop: {desktop_env}")
            contrast_check = system_service.check_enhanced_contrast_availability()
            self.contrast_available = (desktop_env == "GNOME" and contrast_check)
            logger.info(f"Contrast available in simplified mode: {self.contrast_available} (desktop={desktop_env}, check={contrast_check})")
        else:
            self.contrast_available = system_service.check_enhanced_contrast_availability()
            logger.info(f"Contrast available in full mode: {self.contrast_available}")

        total_ram_gb = system_service.get_total_memory_gb()
        self.default_jamesdsp_state = total_ram_gb > 7.0

        is_vm = system_service.is_virtual_machine()
        self.default_contrast_state = not is_vm

        # Call the parent's __init__ which will build the UI
        super().__init__(system_service=system_service, **kwargs)

    def _build_ui(self):
        # Get the base UI from the parent class (a ScrolledWindow with a content box)
        root_widget = super()._build_ui()

        # The parent _build_ui created self.main_box and self.flow_box.
        # We can now modify them or add other widgets to the main_box.
        if self.simplified_mode:
            # Simplified mode: larger cards, centered
            self.flow_box.set_max_children_per_line(2)
            self.flow_box.set_min_children_per_line(2)
            self.flow_box.set_column_spacing(24)
            self.flow_box.set_row_spacing(24)
            self.flow_box.set_vexpand(False)
            self.flow_box.set_halign(Gtk.Align.CENTER)
            self.flow_box.set_valign(Gtk.Align.CENTER)
        else:
            # Full mode: many small cards
            self.flow_box.set_max_children_per_line(8)
            self.flow_box.set_min_children_per_line(4)
            self.flow_box.set_column_spacing(0)
            self.flow_box.set_row_spacing(12)
            self.flow_box.set_vexpand(True)
            self.flow_box.set_valign(Gtk.Align.END)

        # --- Settings Section (Bottom) ---
        if self.jamesdsp_available or self.contrast_available:
            self.settings_title_label = Gtk.Label(
                label=_("Settings"), halign=Gtk.Align.CENTER
            )
            self.settings_title_label.add_css_class("title-2")
            self.settings_title_label.set_vexpand(True)
            self.settings_title_label.set_valign(Gtk.Align.END)
            self.main_box.append(self.settings_title_label)

            settings_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=12,
                vexpand=True,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.START,
            )
            self.main_box.append(settings_box)

            # Card for JamesDSP
            if self.jamesdsp_available:
                self._create_jamesdsp_card(settings_box)

            # Card for Enhanced Contrast
            if self.contrast_available:
                self._create_contrast_card(settings_box)

        return root_widget

    def _retranslate_ui(self):
        """Updates all translatable text in the theme view."""
        super()._retranslate_ui()  # Retranslate the main title from BaseItemView

        if self.jamesdsp_available or self.contrast_available:
            if hasattr(self, "settings_title_label"):
                self.settings_title_label.set_label(_("Settings"))

        if self.jamesdsp_available:
            if hasattr(self, "jamesdsp_title_label"):
                self.jamesdsp_title_label.set_label(_("JamesDSP Audio"))
            if hasattr(self, "jamesdsp_subtitle_label"):
                self.jamesdsp_subtitle_label.set_label(_("Enable audio improvements"))

        if self.contrast_available:
            if hasattr(self, "contrast_title_label"):
                self.contrast_title_label.set_label(_("Image quality"))
            if hasattr(self, "contrast_subtitle_label"):
                self.contrast_subtitle_label.set_label(_("Enable enhanced contrast"))

    def _create_jamesdsp_card(self, parent_box):
        audio_card = Gtk.Box(css_classes=["settings-card"])
        try:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
            audio_card.set_cursor(cursor)
        except Exception:
            pass
        parent_box.append(audio_card)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        audio_card.append(content)

        icon = Gtk.Image.new_from_icon_name("multimedia-volume-control-symbolic")
        icon.set_pixel_size(32)
        icon.set_valign(Gtk.Align.CENTER)
        content.append(icon)

        text_vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, hexpand=True, spacing=2
        )
        content.append(text_vbox)

        self.jamesdsp_title_label = Gtk.Label(
            label=_("JamesDSP Audio"), xalign=0, css_classes=["title-4"]
        )
        self.jamesdsp_subtitle_label = Gtk.Label(
            label=_("Enable audio improvements"), xalign=0
        )
        text_vbox.append(self.jamesdsp_title_label)
        text_vbox.append(self.jamesdsp_subtitle_label)

        self.jamesdsp_switch = Gtk.Switch(
            valign=Gtk.Align.CENTER, active=self.default_jamesdsp_state
        )
        content.append(self.jamesdsp_switch)

        controller = Gtk.GestureClick.new()
        controller.connect(
            "released", self._on_settings_card_clicked, self.jamesdsp_switch
        )
        audio_card.add_controller(controller)

    def _create_contrast_card(self, parent_box):
        contrast_card = Gtk.Box(css_classes=["settings-card"])
        try:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
            contrast_card.set_cursor(cursor)
        except Exception:
            pass
        parent_box.append(contrast_card)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        contrast_card.append(content)

        icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
        icon.set_pixel_size(32)
        icon.set_valign(Gtk.Align.CENTER)
        content.append(icon)

        text_vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, hexpand=True, spacing=2
        )
        content.append(text_vbox)

        self.contrast_title_label = Gtk.Label(
            label=_("Image quality"), xalign=0, css_classes=["title-4"]
        )
        self.contrast_subtitle_label = Gtk.Label(
            label=_("Enable enhanced contrast"), xalign=0
        )
        text_vbox.append(self.contrast_title_label)
        text_vbox.append(self.contrast_subtitle_label)

        self.contrast_switch = Gtk.Switch(
            valign=Gtk.Align.CENTER, active=self.default_contrast_state
        )
        # Connect callback to apply ICC profile immediately when switch state changes
        self.contrast_switch.connect("notify::active", self._on_contrast_switch_toggled)
        content.append(self.contrast_switch)

        controller = Gtk.GestureClick.new()
        controller.connect(
            "released", self._on_settings_card_clicked, self.contrast_switch
        )
        contrast_card.add_controller(controller)

    def _on_settings_card_clicked(self, gesture, n_press, x, y, switch):
        if n_press == 1:
            switch.set_active(not switch.get_active())

    # --- Implementation of BaseItemView abstract methods ---

    def get_title(self) -> str:
        if self.simplified_mode:
            return _("Choose a Theme Style")
        return _("Choose a System Theme")

    def get_items(self) -> list:
        if self.simplified_mode:
            return ["light", "dark"]
        return self.system_service.get_available_themes()

    def create_item_gobject(self, name: str) -> GObject.Object:
        return ThemeListItem(name, self.system_service)

    def emit_signal(self, name: str):
        self.sig_theme_selected.emit(name)

    def create_item_widget(self, item: ThemeListItem):
        if self.simplified_mode:
            # Simplified mode: large theme cards with icons
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            box.set_can_focus(True)
            box.add_css_class("theme-card")
            box.set_size_request(300, 250)

            try:
                cursor = Gdk.Cursor.new_from_name("pointer", None)
                box.set_cursor(cursor)
            except Exception:
                pass

            # Icon based on theme type
            if item.name == "dark":
                icon_name = "weather-clear-night-symbolic"
                label_text = _("Dark Theme")
            else:
                icon_name = "weather-clear-symbolic"
                label_text = _("Light Theme")

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(120)
            icon.set_halign(Gtk.Align.CENTER)
            icon.set_valign(Gtk.Align.CENTER)
            icon.set_vexpand(True)
            box.append(icon)

            label = Gtk.Label(label=label_text)
            label.add_css_class("title-4")
            label.set_halign(Gtk.Align.CENTER)
            box.append(label)

            return box
        else:
            # Full mode: standard small theme cards
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.set_can_focus(True)

            outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            outer_box.set_hexpand(True)
            outer_box.set_vexpand(True)

            try:
                cursor = Gdk.Cursor.new_from_name("pointer", None)
                outer_box.set_cursor(cursor)
            except Exception:
                pass

            if os.path.exists(item.image_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(item.image_path)
                    picture = Gtk.Picture.new_for_pixbuf(pixbuf)
                    picture.set_keep_aspect_ratio(True)
                    picture.set_hexpand(True)
                    picture.set_vexpand(True)
                    picture.set_can_shrink(True)
                    picture.set_halign(Gtk.Align.CENTER)
                    picture.set_valign(Gtk.Align.CENTER)
                    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
                except GLib.Error as e:
                    logger.error(f"Error loading image {item.image_path}: {e}")
                    picture = Gtk.Picture()
            else:
                picture = Gtk.Picture()

            outer_box.append(picture)
            box.append(outer_box)

            label = Gtk.Label()
            label.set_label(item.name.replace("-", " ").title())
            label.set_halign(Gtk.Align.CENTER)
            label.set_margin_top(6)
            label.set_ellipsize(True)
            label.set_max_width_chars(25)
            box.append(label)

            return box

    def is_jamesdsp_enabled(self) -> bool:
        if self.jamesdsp_switch:
            return self.jamesdsp_switch.get_active()
        return False

    def is_contrast_enabled(self) -> bool:
        if self.contrast_switch:
            return self.contrast_switch.get_active()
        return False

    def _on_contrast_switch_toggled(self, switch, param):
        """Called immediately when the ICC profile switch state changes."""
        enabled = switch.get_active()
        logger.info(f"ICC profile switch toggled: {'enabled' if enabled else 'disabled'}")
        self._system_service.apply_icc_profile_settings(enabled)
