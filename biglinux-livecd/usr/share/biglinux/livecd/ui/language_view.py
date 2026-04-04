import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib
import json
import subprocess
import tempfile
import threading
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

# ─── Kokoro TTS integration ───────────────────────────────────────────────
_VOICE_MAP_PATH = "/usr/share/biglinux-kokoro-tts/locale-voice-map.conf"
_KOKO_BIN = "/usr/bin/koko"
_KOKO_MODEL = "/usr/share/biglinux-kokoro-tts/model/model.onnx"
_KOKO_VOICES = "/usr/share/biglinux-kokoro-tts/voices/voices.bin"
_HAS_KOKO = all(os.path.isfile(p) for p in (_KOKO_BIN, _KOKO_MODEL, _KOKO_VOICES))


def _parse_voice_map():
    """Parse locale-voice-map.conf → {locale: (engine, voice, lang_code)}."""
    result = {}
    try:
        with open(_VOICE_MAP_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                locale, _, val = line.partition("=")
                locale = locale.strip()
                parts = [p.strip() for p in val.strip().split(":")]
                if len(parts) >= 2:
                    result[locale] = (
                        parts[0],
                        parts[1],
                        parts[2] if len(parts) > 2 else "",
                    )
    except FileNotFoundError:
        pass
    return result


_VOICE_MAP = _parse_voice_map()
_KOKORO_WAV_CACHE = {}
_KOKORO_CACHE_LOCK = threading.Lock()


def _voice_config_for_locale(locale_code):
    """Look up TTS voice config for a locale, with fallback chain."""
    if locale_code in _VOICE_MAP:
        return _VOICE_MAP[locale_code]
    lang = locale_code.split("_")[0]
    for key, val in _VOICE_MAP.items():
        if key.startswith(lang + "_"):
            return val
    if "*" in _VOICE_MAP:
        return _VOICE_MAP["*"]
    return ("espeak", "en", "en")


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
            # Pre-generate Kokoro WAVs in background (thread-safe copy of data)
            self._start_kokoro_precache(language_data)

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
        self._tts_gen = 0
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
        """Speak the selected language name using Kokoro TTS or espeak-ng fallback."""
        # Cancel any pending delayed speak
        if self._speak_timeout_id > 0:
            GLib.source_remove(self._speak_timeout_id)
            self._speak_timeout_id = 0
        # Kill any ongoing TTS process
        if self._espeak_proc and self._espeak_proc.poll() is None:
            self._espeak_proc.terminate()
            self._espeak_proc = None
        self._tts_gen += 1
        selected = selection_model.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION:
            return
        item = selection_model.get_item(selected)
        if not item:
            return
        # Cancel ORCA speech for ALL languages
        self._cancel_orca()
        # Build text to speak
        parts = item.name.split(" - ", 1)
        country = parts[1] if len(parts) > 1 else ""
        native_name = _NATIVE_LANG_NAMES.get(item.code[:2], item.name_orig)
        text = f"{native_name}, {country}" if country else native_name
        # Look up voice config from locale-voice-map.conf
        engine, voice, lang_code = _voice_config_for_locale(item.code)
        if engine == "kokoro" and _HAS_KOKO:
            cache_key = f"{voice}:{lang_code}:{text}"
            with _KOKORO_CACHE_LOCK:
                cached_wav = _KOKORO_WAV_CACHE.get(cache_key)
            if cached_wav and os.path.isfile(cached_wav):
                # Kokoro WAV is cached — play it instantly
                self._speak_timeout_id = GLib.timeout_add(
                    50, self._play_wav, cached_wav
                )
            else:
                # Not cached yet — play espeak immediately (zero latency),
                # and generate Kokoro WAV in background for next visit
                espeak_voice = lang_code if lang_code else item.code.replace("_", "-")
                self._speak_timeout_id = GLib.timeout_add(
                    50, self._do_espeak, espeak_voice, text
                )
                threading.Thread(
                    target=self._kokoro_generate,
                    args=(voice, lang_code, text, cache_key),
                    daemon=True,
                ).start()
        else:
            espeak_voice = lang_code if engine == "kokoro" else voice
            if not espeak_voice:
                espeak_voice = item.code.replace("_", "-")
            self._speak_timeout_id = GLib.timeout_add(
                50, self._do_espeak, espeak_voice, text
            )

    def _do_espeak(self, voice, text):
        """Speak with espeak-ng in native voice."""
        self._speak_timeout_id = 0
        self._cancel_orca()
        try:
            self._espeak_proc = subprocess.Popen(
                ["espeak-ng", "-v", voice, "--", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            logger.debug("espeak-ng not found")
        return GLib.SOURCE_REMOVE

    def _play_wav(self, wav_path):
        """Play a cached WAV file instantly."""
        self._speak_timeout_id = 0
        self._cancel_orca()
        try:
            self._espeak_proc = subprocess.Popen(
                ["paplay", wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        return GLib.SOURCE_REMOVE

    def _kokoro_generate(self, voice, lang_code, text, cache_key):
        """Background: generate WAV with koko and cache it (does not play)."""
        tmpwav = None
        try:
            fd, tmpwav = tempfile.mkstemp(prefix="bw-", suffix=".wav")
            os.close(fd)
            proc = subprocess.run(
                [
                    _KOKO_BIN, "text", text,
                    "-m", _KOKO_MODEL, "-d", _KOKO_VOICES,
                    "--lan", lang_code, "--style", voice, "--force-style",
                    "-o", tmpwav,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            if proc.returncode == 0 and os.path.isfile(tmpwav) and os.path.getsize(tmpwav) > 0:
                with _KOKORO_CACHE_LOCK:
                    _KOKORO_WAV_CACHE[cache_key] = tmpwav
            else:
                if tmpwav:
                    os.unlink(tmpwav)
        except Exception:
            if tmpwav and os.path.isfile(tmpwav) and cache_key not in _KOKORO_WAV_CACHE:
                try:
                    os.unlink(tmpwav)
                except OSError:
                    pass

    def _start_kokoro_precache(self, language_data):
        """Launch background pre-generation of Kokoro WAVs for all supported locales."""
        if not _HAS_KOKO:
            return
        # Build list of (voice, lang_code, text, cache_key) — thread-safe, no GObjects
        tasks = []
        favorites = {"en_US": 0, "pt_BR": 1, "es_ES": 2}
        for item in language_data:
            engine, voice, lang_code = _voice_config_for_locale(item.code)
            if engine != "kokoro":
                continue
            parts = item.name.split(" - ", 1)
            country = parts[1] if len(parts) > 1 else ""
            native_name = _NATIVE_LANG_NAMES.get(item.code[:2], item.name_orig)
            text = f"{native_name}, {country}" if country else native_name
            cache_key = f"{voice}:{lang_code}:{text}"
            priority = favorites.get(item.code, 999)
            tasks.append((priority, voice, lang_code, text, cache_key))
        tasks.sort(key=lambda t: t[0])
        threading.Thread(
            target=self._precache_worker, args=(tasks,), daemon=True
        ).start()

    def _precache_worker(self, tasks):
        """Background: sequentially generate Kokoro WAVs, favorites first."""
        for _, voice, lang_code, text, cache_key in tasks:
            with _KOKORO_CACHE_LOCK:
                if cache_key in _KOKORO_WAV_CACHE:
                    continue
            self._kokoro_generate(voice, lang_code, text, cache_key)

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
