import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib
import json
import subprocess
import unicodedata
from urllib.parse import parse_qs, urlparse
from translations import _
from config import LanguageSelection
from accessibility import announce
from logging_config import get_logger
import os

logger = get_logger()

# Clean native language names for screen reader pronunciation.
# Maps the 2-letter lang prefix to a short, clear native name.
_NATIVE_LANG_NAMES = {
    "be": "беларуская",
    "bg": "български",
    "cs": "čeština",
    "da": "dansk",
    "de": "Deutsch",
    "el": "ελληνικά",
    "en": "English",
    "es": "español",
    "et": "eesti",
    "fi": "suomi",
    "fr": "français",
    "he": "עברית",
    "hr": "hrvatski",
    "hu": "magyar",
    "is": "Íslenska",
    "it": "italiano",
    "ja": "日本語",
    "ko": "한국어",
    "nb": "norsk bokmål",
    "nl": "Nederlands",
    "nn": "norsk nynorsk",
    "pl": "polski",
    "pt": "Português",
    "ro": "română",
    "ru": "русский",
    "sk": "slovenčina",
    "sl": "slovenščina",
    "sv": "Svenska",
    "tr": "Türkçe",
    "uk": "українська",
    "zh": "中文",
}


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
        self.search_entry.update_property(
            [Gtk.AccessibleProperty.LABEL], [_("Search for a language...")]
        )
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
        self.grid_view.update_property(
            [Gtk.AccessibleProperty.LABEL],
            [_("Search for a language...")],
        )
        self.grid_view.connect("activate", self._on_grid_view_activate)
        grid_clamp.set_child(self.grid_view)

        return root_box

    def _retranslate_ui(self):
        """Updates translatable text within the language view."""
        self.search_entry.set_placeholder_text(_("Search for a language..."))
        self.search_entry.update_property(
            [Gtk.AccessibleProperty.LABEL], [_("Search for a language...")]
        )

    def _load_languages(self):
        try:
            # Point back to the original, non-preprocessed JSON file.
            path = os.path.join(
                os.path.dirname(__file__), "..", "assets", "localization.json"
            )
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            language_data = [LanguageListItem(**item) for item in raw_data]
            favorites_order = {"en_US": 0, "pt_BR": 1, "es_ES": 2}
            language_data.sort(key=lambda x: (x.code not in favorites_order, favorites_order.get(x.code, 999), x.name))
            self._store.splice(0, 0, language_data)
            GLib.idle_add(self._post_load_setup)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading languages: {e}")
            self.set_child(Gtk.Label(label=_("Could not load language data.")))

        return GLib.SOURCE_REMOVE

    def _create_filtered_model(self):
        self.filter = Gtk.CustomFilter.new(self._filter_func, None)
        self.filter_model = Gtk.FilterListModel(model=self._store, filter=self.filter)
        selection_model = Gtk.SingleSelection(model=self.filter_model)
        selection_model.connect("selection-changed", self._on_selection_changed)
        self._espeak_proc = None
        self._speak_timeout_id = 0
        # speech-dispatcher client for fast cancel (avoids subprocess overhead)
        self._spd_client = None
        self._spd_scope_all = None
        try:
            import speechd

            self._spd_client = speechd.SSIPClient("biglinux-wizard")
            self._spd_scope_all = speechd.Scope.ALL
        except Exception:
            pass
        return selection_model

    def _cancel_orca(self):
        """Cancel ALL speech-dispatcher clients (including ORCA) instantly."""
        if self._spd_client and self._spd_scope_all:
            try:
                self._spd_client.cancel(scope=self._spd_scope_all)
            except Exception:
                pass

    def _on_selection_changed(self, selection_model, position, n_items):
        """For pt_BR, let ORCA speak with the default Letícia voice.
        For other languages, cancel ORCA and use espeak-ng with the native voice."""
        # Cancel any pending delayed speak
        if self._speak_timeout_id > 0:
            GLib.source_remove(self._speak_timeout_id)
            self._speak_timeout_id = 0
        # Kill any ongoing espeak-ng process
        if self._espeak_proc and self._espeak_proc.poll() is None:
            self._espeak_proc.terminate()
            self._espeak_proc = None
        selected = selection_model.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION:
            return
        item = selection_model.get_item(selected)
        if not item:
            return
        # For pt_BR: do nothing, let ORCA read with Letícia voice
        if item.code == "pt_BR":
            return
        # Immediately cancel ORCA speech via Python API (instant, no fork)
        self._cancel_orca()
        # Schedule espeak-ng after a brief delay to also cancel any ORCA re-queue
        parts = item.name.split(" - ", 1)
        country = parts[1] if len(parts) > 1 else ""
        native_name = _NATIVE_LANG_NAMES.get(item.code[:2], item.name_orig)
        text = f"{native_name}, {country}" if country else native_name
        voice = item.code.replace("_", "-")  # "en_US" -> "en-US"
        self._speak_timeout_id = GLib.timeout_add(50, self._do_espeak, voice, text)

    def _do_espeak(self, voice, text):
        """Cancel ORCA speech and speak with espeak-ng in native voice."""
        self._speak_timeout_id = 0
        # Cancel any ORCA speech that was re-queued
        self._cancel_orca()
        # Speak with espeak-ng using the native voice
        try:
            self._espeak_proc = subprocess.Popen(
                ["espeak-ng", "-v", voice, "--", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.debug("espeak-ng not found")
        return GLib.SOURCE_REMOVE

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
        # Announce results count for screen readers
        count = self.filter_model.get_n_items()
        GLib.idle_add(lambda c=count: announce(self, _("%d results") % c))
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

        flag_widget = Gtk.Image(
            pixel_size=36,
            accessible_role=Gtk.AccessibleRole.PRESENTATION,
        )

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
        )
        # Heading: native name (ORCA reads this for pt_BR with Letícia voice)
        name_label = Gtk.Label(
            halign=Gtk.Align.START,
            wrap=True,
            justify=Gtk.Justification.LEFT,
        )
        name_label.add_css_class("heading")
        # Caption: hidden from ORCA (English name for visual reference only)
        orig_name_label = Gtk.Label(
            halign=Gtk.Align.START,
            wrap=True,
            justify=Gtk.Justification.LEFT,
            accessible_role=Gtk.AccessibleRole.PRESENTATION,
        )
        orig_name_label.add_css_class("caption")
        vbox.append(name_label)
        vbox.append(orig_name_label)

        content_box.append(flag_widget)
        content_box.append(vbox)
        root_box.append(content_box)

        # Store references for _on_factory_bind
        root_box._flag = flag_widget
        root_box._name_label = name_label
        root_box._orig_label = orig_name_label

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

        # Build native name heading: e.g. "Português, Brazil" or "English, United States"
        parts = item.name.split(" - ", 1)
        country = parts[1] if len(parts) > 1 else ""
        native_name = _NATIVE_LANG_NAMES.get(item.code[:2], item.name_orig)
        heading_text = f"{native_name}, {country}" if country else native_name

        # Heading: visual text
        root_box._name_label.set_label(heading_text)
        # Caption: English name (PRESENTATION — ORCA doesn't read)
        root_box._orig_label.set_label(item.name)

        root_box._flag.set_from_icon_name(item.flag_icon_name)

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
