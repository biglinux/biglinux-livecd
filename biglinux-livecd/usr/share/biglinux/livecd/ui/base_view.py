# ui/base_view.py

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gdk
from services import SystemService
from abc import ABCMeta, abstractmethod


class GObjectMeta(type(GObject.Object), ABCMeta):
    pass


class BaseItemView(Adw.Bin, metaclass=GObjectMeta):
    __gtype_name__ = "BaseItemView"

    def __init__(self, system_service: SystemService, **kwargs):
        super().__init__(**kwargs)
        self.system_service = system_service
        self.set_vexpand(True)
        self.items_loaded = False

        self.set_child(self._build_ui())
        self.connect("map", self._on_map)

    def _on_map(self, *args):
        """Load items only when the view is first mapped (made visible)."""
        if not self.items_loaded:
            self.load_items()
            self.items_loaded = True
        self.grab_focus()

    def _build_ui(self):
        scrolled_window = Gtk.ScrolledWindow(
            vexpand=True,
            hexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )

        # This box will contain all scrollable content
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.main_box.set_margin_top(24)
        self.main_box.set_margin_bottom(24)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        scrolled_window.set_child(self.main_box)

        title = Gtk.Label(label=self.get_title(), halign=Gtk.Align.CENTER)
        title.add_css_class("title-2")
        self.main_box.append(title)

        # This container centers the FlowBox vertically within the available space.
        centering_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, vexpand=True, valign=Gtk.Align.FILL
        )
        self.main_box.append(centering_box)

        clamp = Adw.Clamp(maximum_size=self.get_clamp_width())
        clamp.set_halign(Gtk.Align.CENTER)
        centering_box.append(clamp)

        self.flow_box = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.SINGLE,
            activate_on_single_click=True,
            max_children_per_line=self.get_max_columns(),
            min_children_per_line=self.get_min_columns(),
            homogeneous=True,
            column_spacing=12,
            row_spacing=12,
            hexpand=True,
            vexpand=True,
            valign=Gtk.Align.CENTER,
        )
        self.flow_box.set_can_focus(True)
        self.flow_box.set_halign(Gtk.Align.CENTER)

        self.flow_box.connect("child-activated", self._on_child_activated)
        self.flow_box.connect("activate-cursor-child", self._on_activate_cursor_child)

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.flow_box.add_controller(key_controller)

        flow_motion_controller = Gtk.EventControllerMotion.new()
        flow_motion_controller.connect("leave", self._on_flow_leave)
        self.flow_box.add_controller(flow_motion_controller)

        clamp.set_child(self.flow_box)

        return scrolled_window

    def load_items(self):
        items = self.get_items()
        if not items:
            self.emit_signal("default")
            return

        for name in items:
            item_obj = self.create_item_gobject(name)
            child_widget = self.create_item_widget(item_obj)

            flow_child = Gtk.FlowBoxChild()
            flow_child.set_child(child_widget)
            flow_child.set_can_focus(True)
            flow_child.item_data = item_obj

            # Hover-to-select functionality
            item_motion_controller = Gtk.EventControllerMotion.new()
            item_motion_controller.connect("enter", self._on_item_enter, flow_child)
            flow_child.add_controller(item_motion_controller)

            self.flow_box.append(flow_child)

        if items:
            GLib.idle_add(self._select_first_item)

    def grab_focus(self):
        self.flow_box.grab_focus()

    def _select_first_item(self):
        first_child = self.flow_box.get_first_child()
        if first_child:
            self.flow_box.select_child(first_child)
            self.grab_focus()
        return GLib.SOURCE_REMOVE

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected = self.flow_box.get_selected_children()
            if selected:
                self._on_child_activated(self.flow_box, selected[0])
                return True
        return False

    def _on_child_activated(self, flow_box, child):
        if hasattr(child, "item_data"):
            self.emit_signal(child.item_data.name)

    def _on_flow_leave(self, controller, *args):
        self.flow_box.unselect_all()

    def _on_item_enter(self, controller, x, y, flow_child):
        self.flow_box.select_child(flow_child)

    def _on_activate_cursor_child(self, flow_box):
        selected = flow_box.get_selected_children()
        if selected:
            self._on_child_activated(flow_box, selected[0])

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_items(self) -> list:
        pass

    @abstractmethod
    def create_item_gobject(self, name: str) -> GObject.Object:
        pass

    @abstractmethod
    def create_item_widget(self, item: GObject.Object):
        pass

    @abstractmethod
    def emit_signal(self, name: str):
        pass

    def get_clamp_width(self) -> int:
        return 1600

    def get_max_columns(self) -> int:
        return 3

    def get_min_columns(self) -> int:
        return 3
