# ui/keyboard_view.py

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gdk
from translations import _
import os

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))


class KeyboardView(Adw.Bin):
    __gtype_name__ = "KeyboardView"
    sig_keyboard_selected = GObject.Signal("keyboard-selected", arg_types=[str])

    def __init__(self, primary_layout: str, **kwargs):
        super().__init__(**kwargs)
        self.primary_layout = primary_layout

        self.set_vexpand(True)
        self.set_child(self._build_ui())
        self.load_layouts()
        self.connect("map", self._on_map)

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root_box.set_margin_top(24)
        root_box.set_margin_bottom(24)
        root_box.set_margin_start(24)
        root_box.set_margin_end(24)

        self.title_label = Gtk.Label(
            label=_("Choose Your Keyboard Layout"), halign=Gtk.Align.CENTER
        )
        self.title_label.add_css_class("title-2")
        root_box.append(self.title_label)

        # Centered vertical box for keyboard selection and image
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_vexpand(True)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_margin_bottom(70)  # Add space between title and buttons
        root_box.append(center_box)

        clamp = Adw.Clamp(maximum_size=800)
        clamp.set_halign(Gtk.Align.CENTER)
        center_box.append(clamp)

        self.flow_box = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.SINGLE,
            activate_on_single_click=True,
            max_children_per_line=2,
            min_children_per_line=2,
            homogeneous=True,
            column_spacing=12,
            row_spacing=12,
            hexpand=False,
            vexpand=False,
            margin_bottom=18,
        )
        self.flow_box.set_can_focus(True)
        self.flow_box.set_halign(Gtk.Align.CENTER)

        # Connect to FlowBox-level signals
        self.flow_box.connect("child-activated", self._on_child_activated)
        self.flow_box.connect("activate-cursor-child", self._on_activate_cursor_child)

        # Add key controller for Enter key handling
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.flow_box.add_controller(key_controller)

        # Controller to clear selection when mouse leaves the entire flow box
        flow_motion_controller = Gtk.EventControllerMotion.new()
        flow_motion_controller.connect("leave", self._on_flow_leave)
        self.flow_box.add_controller(flow_motion_controller)

        clamp.set_child(self.flow_box)

        # Keyboard.svg centered below buttons
        image_path = os.path.join(ASSETS_DIR, "keyboard.svg")
        if os.path.exists(image_path):
            from gi.repository import Gio

            gfile = Gio.File.new_for_path(image_path)
            img = Gtk.Picture.new_for_file(gfile)
            img.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
            center_box.append(img)

        return root_box

    def _retranslate_ui(self):
        """Updates the view's title to the current language."""
        if hasattr(self, "title_label"):
            self.title_label.set_label(_("Choose Your Keyboard Layout"))

    def load_layouts(self):
        # Clear existing children
        child = self.flow_box.get_first_child()
        while child:
            self.flow_box.remove(child)
            child = self.flow_box.get_first_child()

        # Determine layouts to show, avoiding duplicates.
        # The primary layout (e.g., 'br') comes first, followed by 'us' as an alternative.
        layouts = []
        if self.primary_layout:
            layouts.append((self.primary_layout.upper(), self.primary_layout))

        if self.primary_layout != "us":
            layouts.append(("US", "us"))

        # Create FlowBoxChild widgets for each layout
        for name, layout_id in layouts:
            child = self._create_layout_child(name, layout_id)
            self.flow_box.append(child)

        GLib.idle_add(self._select_first_item)

    def _create_layout_child(self, name, layout_id):
        """Create a FlowBoxChild with a keyboard layout card."""
        flow_child = Gtk.FlowBoxChild()
        flow_child.layout_data = {"name": name, "layout_id": layout_id}

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            css_classes=["keyboard-item-card"],
        )

        label = Gtk.Label(label=name)
        label.add_css_class("title-2")
        box.append(label)

        flow_child.set_child(box)

        # Add motion controller for hover-to-select
        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("enter", self._on_item_enter, flow_child)
        box.add_controller(motion_controller)

        # Gtk.GestureClick is not needed because the FlowBox has
        # activate_on_single_click=True, which emits the 'child-activated' signal.

        return flow_child

    def _select_first_item(self):
        child = self.flow_box.get_first_child()
        if child:
            self.flow_box.select_child(child)
        return GLib.SOURCE_REMOVE

    def _on_child_activated(self, flow_box, child):
        """Handle FlowBox child-activated signal."""
        self._activate_child(child)

    def _on_activate_cursor_child(self, flow_box):
        """Handle activate-cursor-child signal (Enter key on selected item)."""
        selected = flow_box.get_selected_children()
        if selected:
            self._activate_child(selected[0])

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press events, specifically Enter key."""
        if keyval == Gdk.KEY_Return:  # GDK_KEY_Return
            selected = self.flow_box.get_selected_children()
            if selected:
                self._activate_child(selected[0])
                return True
        return False

    def _activate_child(self, child):
        """Activate a FlowBoxChild and emit the selection signal."""
        if hasattr(child, "layout_data"):
            layout_id = child.layout_data["layout_id"]
            self.sig_keyboard_selected.emit(layout_id)

    def _on_item_enter(self, controller, x, y, child):
        """Select the item when the mouse pointer enters it."""
        self.flow_box.select_child(child)

    def _on_flow_leave(self, controller, *args):
        """Clear selection when the mouse pointer leaves the flow box."""
        self.flow_box.unselect_all()

    def _on_map(self, *args):
        self.grab_focus()
        GLib.idle_add(self._select_first_item)

    def update_primary_layout(self, new_layout):
        self.primary_layout = new_layout
        self.load_layouts()
