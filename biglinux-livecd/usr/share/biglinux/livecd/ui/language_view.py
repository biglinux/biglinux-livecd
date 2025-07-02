import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib
import json
import unicodedata
from urllib.parse import parse_qs, urlparse
from translations import _
from config import LanguageSelection
import os


def normalize_string(s: str) -> str:
    """Normalizes a string by converting to lowercase and removing diacritics."""
    if not s:
        return ""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


class LanguageListItem(GObject.Object):
    """GObject wrapper for language data. Holds an icon name."""

    __gtype_name__ = "LanguageListItem"

    def __init__(self, url, name, nameOrig, flag, code):
        super().__init__()
        self.url = url
        self.name = name
        self.name_orig = nameOrig
        self.code = code

        # This logic works for any path, including /usr/share/circle-flags-svg/br.svg
        self.flag_icon_name = os.path.splitext(os.path.basename(flag))[0]

        # Normalization is done on-the-fly, which is fast enough for this dataset.
        self.normalized_name = normalize_string(name)
        self.normalized_name_orig = normalize_string(nameOrig)


class LanguageView(Adw.Bin):
    __gtype_name__ = "LanguageView"
    sig_language_selected = GObject.Signal(
        "language-selected", arg_types=[GObject.TYPE_PYOBJECT]
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_vexpand(True)
        self._store = Gio.ListStore(item_type=LanguageListItem)
        self.filter_timeout_id = 0

        self.set_child(self._build_ui())
        GLib.idle_add(self._load_languages)

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        search_clamp = Adw.Clamp(maximum_size=400, margin_top=45, margin_bottom=10)
        self.search_entry = Gtk.SearchEntry(
            placeholder_text=_("Search for a language...")
        )
        self.search_entry.set_focusable(False)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_clamp.set_child(self.search_entry)
        root_box.append(search_clamp)

        scrolled_window = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vexpand=True,
        )
        root_box.append(scrolled_window)

        grid_clamp = Adw.Clamp(maximum_size=1000)
        scrolled_window.set_child(grid_clamp)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.grid_view = Gtk.GridView(
            model=self._create_filtered_model(),
            factory=factory,
            max_columns=3,
            min_columns=3,
        )
        self.grid_view.connect("activate", self._on_grid_view_activate)
        grid_clamp.set_child(self.grid_view)

        return root_box

    def _retranslate_ui(self):
        """Updates translatable text within the language view."""
        self.search_entry.set_placeholder_text(_("Search for a language..."))

    def _load_languages(self):
        try:
            # Point back to the original, non-preprocessed JSON file.
            path = os.path.join(
                os.path.dirname(__file__), "..", "assets", "localization.json"
            )
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            language_data = [LanguageListItem(**item) for item in raw_data]
            favorites = ["pt_BR", "en_US", "es_ES"]
            language_data.sort(key=lambda x: (x.code not in favorites, x.name))
            self._store.splice(0, 0, language_data)
            GLib.idle_add(self._post_load_setup)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading languages: {e}")
            self.set_child(Gtk.Label(label=_("Could not load language data.")))

        return GLib.SOURCE_REMOVE

    def _create_filtered_model(self):
        self.filter = Gtk.CustomFilter.new(self._filter_func, None)
        self.filter_model = Gtk.FilterListModel(model=self._store, filter=self.filter)
        selection_model = Gtk.SingleSelection(model=self.filter_model)
        return selection_model

    def _activate_item(self, item):
        if not item:
            return
        params = parse_qs(urlparse(item.url).query)
        params_flat = {k: v[0] for k, v in params.items()}
        self.sig_language_selected.emit(
            LanguageSelection(code=item.code, name=item.name, url_params=params_flat)
        )

    def _on_grid_view_activate(self, grid_view, position):
        selection_model = grid_view.get_model()
        item = selection_model.get_item(position)
        if item:
            self._activate_item(item)

    def _on_search_changed(self, entry):
        if self.filter_timeout_id > 0:
            GLib.source_remove(self.filter_timeout_id)
        self.filter_timeout_id = GLib.timeout_add(50, self._trigger_filter_update)

    def _trigger_filter_update(self):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        GLib.idle_add(self._select_first_item_after_filter)
        self.filter_timeout_id = 0
        return GLib.SOURCE_REMOVE

    def _select_first_item_after_filter(self):
        if self.grid_view.get_model().get_n_items() > 0:
            self.grid_view.get_model().set_selected(0)

    def _post_load_setup(self):
        self._select_first_item_after_filter()
        self.grid_view.grab_focus()

    def _filter_func(self, item, _user_data):
        query = normalize_string(self.search_entry.get_text())
        if not query:
            return True
        return query in item.normalized_name or query in item.normalized_name_orig

    def _on_factory_setup(self, factory, list_item):
        root_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.FILL,
            valign=Gtk.Align.CENTER,
            margin_top=0,
            margin_bottom=0,
            margin_start=30,
            margin_end=30,
            height_request=100,
        )
        content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=20,
            height_request=100,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )
        root_box.append(content_box)
        list_item.set_child(root_box)

        try:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
            root_box.set_cursor(cursor)
        except Exception:
            pass

        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", self._on_mouse_motion_item, list_item)
        root_box.add_controller(motion_controller)

    def _on_mouse_motion_item(self, controller, x, y, list_item):
        position = list_item.get_position()
        if position != Gtk.INVALID_LIST_POSITION:
            selection_model = self.grid_view.get_model()
            if selection_model and selection_model.get_selected() != position:
                selection_model.set_selected(position)

    def _on_factory_bind(self, factory, list_item):
        item = list_item.get_item()
        root_box = list_item.get_child()
        content_box = root_box.get_first_child()

        child = content_box.get_first_child()
        while child:
            content_box.remove(child)
            child = content_box.get_first_child()

        flag_widget = Gtk.Image.new_from_icon_name(item.flag_icon_name)
        flag_widget.set_pixel_size(36)

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )
        name_label = Gtk.Label(
            halign=Gtk.Align.START,
            label=item.name,
            wrap=True,
            justify=Gtk.Justification.LEFT,
        )
        name_label.add_css_class("heading")
        orig_name_label = Gtk.Label(
            halign=Gtk.Align.START,
            label=item.name_orig,
            wrap=True,
            justify=Gtk.Justification.LEFT,
        )
        orig_name_label.add_css_class("caption")
        vbox.append(name_label)
        vbox.append(orig_name_label)

        content_box.append(flag_widget)
        content_box.append(vbox)

        click_gesture = Gtk.GestureClick.new()
        click_gesture.connect("released", self._on_item_clicked, item)
        root_box.add_controller(click_gesture)

    def _on_item_clicked(self, gesture, n_press, x, y, item):
        if n_press == 1 and gesture.get_current_button() == Gdk.BUTTON_PRIMARY:
            self._activate_item(item)

    def handle_global_key_press(self, keyval):
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selection_model = self.grid_view.get_model()
            if (
                selection_model
                and selection_model.get_selected() != Gtk.INVALID_LIST_POSITION
            ):
                item = selection_model.get_item(selection_model.get_selected())
                if item:
                    self._activate_item(item)
                    return True
        elif keyval == Gdk.KEY_BackSpace:
            current_text = self.search_entry.get_text()
            if current_text:
                self.search_entry.set_text(current_text[:-1])
                self._on_search_changed(self.search_entry)
                return True
        else:
            char = Gdk.keyval_to_unicode(keyval)
            if char and char >= 32:
                self.search_entry.set_text(self.search_entry.get_text() + chr(char))
                self._on_search_changed(self.search_entry)
                return True
        return False
