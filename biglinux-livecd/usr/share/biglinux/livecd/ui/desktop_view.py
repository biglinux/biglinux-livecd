# ui/desktop_view.py

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GObject, GLib, GdkPixbuf, Gdk
from translations import _
from services import SystemService
from ui.base_view import BaseItemView
from logging_config import get_logger
import os

logger = get_logger()


class DesktopListItem(GObject.Object):
    """GObject wrapper for desktop layout data."""

    __gtype_name__ = "DesktopListItem"

    def __init__(self, name, system_service: SystemService):
        super().__init__()
        self.name = name
        self.image_path = system_service.get_desktop_image_path(name)


class DesktopView(BaseItemView):
    __gtype_name__ = "DesktopView"
    sig_desktop_selected = GObject.Signal("desktop-selected", arg_types=[str])

    def get_title(self) -> str:
        return _("Choose a Desktop Layout")

    def get_items(self) -> list:
        return self.system_service.get_available_desktops()

    def create_item_gobject(self, name: str) -> GObject.Object:
        return DesktopListItem(name, self.system_service)

    def create_item_widget(self, item: DesktopListItem):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_can_focus(True)
        try:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
            box.set_cursor(cursor)
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
            picture = Gtk.Picture.new_from_icon_name("image-missing-symbolic")

        box.append(picture)
        return box

    def emit_signal(self, name: str):
        self.sig_desktop_selected.emit(name)
