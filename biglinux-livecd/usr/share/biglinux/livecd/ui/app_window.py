import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
import importlib
import os
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from accessibility import (
    announce,
    ensure_orca_disabled,
    is_accessibility_enabled,
    set_accessibility_enabled,
    speak,
)
from config import SetupConfig
from gi.repository import Adw, Gdk, GdkPixbuf, GLib, Gtk
from logging_config import get_logger
from services import SystemService
from translations import _, set_language
from ui.language_view import LanguageView

logger = get_logger()

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

# Default logo paths
DEFAULT_LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
DEFAULT_COMM_LOGO_PATH = os.path.join(ASSETS_DIR, "comm-logo.png")


def get_logo_path(system_service: SystemService | None = None):
    """Return the selected profile logo or the BigLinux fallback."""
    if system_service:
        profile_logo = system_service.get_profile_logo_path()
        if profile_logo:
            return profile_logo
    return DEFAULT_LOGO_PATH


def get_comm_logo_path(system_service: SystemService | None = None):
    """Return the selected profile logo or the community fallback."""
    if system_service:
        profile_logo = system_service.get_profile_logo_path()
        if profile_logo:
            return profile_logo
    return DEFAULT_COMM_LOGO_PATH


def load_svg_texture(path, size):
    """Load SVG as Gdk.Texture for better GTK4 scaling."""
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        if pixbuf is None:
            raise GLib.Error("Could not allocate image")
        return Gdk.Texture.new_for_pixbuf(pixbuf)
    except GLib.Error as e:
        logger.error(f"Failed to load SVG {path}: {e}")
        # Create a fallback empty pixbuf and convert to texture
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
        if pixbuf is None:
            raise RuntimeError("Could not allocate fallback image")
        return Gdk.Texture.new_for_pixbuf(pixbuf)


class AppWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AppWindow"

    def __init__(self, system_service: SystemService, **kwargs):
        super().__init__(**kwargs)
        self.system_service = system_service
        self.config = SetupConfig()
        self.completed_steps: set[str] = set()  # Track completed steps
        self._system_updates = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="livecd-system-update"
        )
        self._last_system_update: Future[Any] | None = None
        self._speechd_client: Any | None = None
        self._preload_modules = [
            "ui.keyboard_view",
            "ui.desktop_view",
            "ui.theme_view",
        ]
        self._theme_runtime_states: dict[bool, Any] = {}
        self._pending_view_name: str | None = None
        self._preload_started = False
        self.has_desktop_step = system_service.has_desktop_layout_step()
        self.uses_simple_theme = system_service.uses_simple_theme_selector()
        # Ensure ORCA is not running — user activates it manually via Super+Alt+S
        GLib.timeout_add(500, ensure_orca_disabled)
        self.set_title(_("BigLinux Setup"))
        self.update_property(
            [Gtk.AccessibleProperty.DESCRIPTION],
            [
                _("BigLinux Setup")
                + " — "
                + _("press Super+Alt+S to start the screen reader")
            ],
        )

        # --- Fullscreen wizard window ---
        self.set_decorated(False)
        self.add_css_class("wizard-window")
        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors.get_n_items() > 0:
                monitor = monitors.get_item(0)
                if monitor is not None:
                    geometry = monitor.get_geometry()
                    self.set_default_size(geometry.width, geometry.height)
        self.fullscreen()

        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        css_provider = Gtk.CssProvider()
        css_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "style.css")
        )
        if os.path.exists(css_path):
            css_provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                self.get_display(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        self.set_content(self._build_ui())
        self._update_header_state()

        # Create and add a Gtk.EventControllerKey for global key events (CAPTURE phase
        # so it runs before child widgets like the search entry consume keys)
        key_controller = Gtk.EventControllerKey.new()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_press_event)
        self.add_controller(key_controller)
        self.connect("map", self._schedule_initial_preload)

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root_box.append(self._build_header())
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        content_box.add_css_class("app-content")
        root_box.append(content_box)
        self.stack = Adw.ViewStack()
        self.stack.set_vexpand(True)
        self.stack.connect("notify::visible-child", self._on_view_changed)
        content_box.append(self.stack)
        self._add_language_view()
        self.stack.set_visible_child_name("language")
        GLib.idle_add(self._update_header_state)
        return root_box

    def _build_header(self) -> Gtk.CenterBox:
        header_wrapper = Gtk.CenterBox()
        header_wrapper.add_css_class("app-header")
        header_content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=15,
            margin_top=15,
            margin_bottom=15,
        )
        header_wrapper.set_center_widget(header_content_box)

        if self.has_desktop_step:
            self.steps: list[dict[str, Any]] = [
                {"name": "language", "file": "headerbar-locale.svg"},
                {"name": "keyboard", "file": "headerbar-keyboard.svg"},
                {"name": "desktop", "file": "headerbar-display.svg"},
                {"name": "theme", "file": "headerbar-theme.svg"},
            ]
        else:
            self.steps = [
                {"name": "language", "file": "headerbar-locale.svg"},
                {"name": "keyboard", "file": "headerbar-keyboard.svg"},
                {"name": "theme", "file": "headerbar-theme.svg"},
            ]

        if not self.has_desktop_step:
            self._append_logo(
                header_content_box, get_comm_logo_path(self.system_service)
            )
            self._add_step_button(header_content_box, self.steps[0])
            self._add_step_button(header_content_box, self.steps[1])
            self._add_step_button(header_content_box, self.steps[2])
        else:
            self._add_step_button(header_content_box, self.steps[0])
            self._add_step_button(header_content_box, self.steps[1])
            logo_path = (
                get_comm_logo_path(self.system_service)
                if self.uses_simple_theme
                else get_logo_path(self.system_service)
            )
            self._append_logo(header_content_box, logo_path)
            self._add_step_button(header_content_box, self.steps[2])
            self._add_step_button(header_content_box, self.steps[3])
        return header_wrapper

    @staticmethod
    def _append_logo(box: Gtk.Box, path: str) -> None:
        if not os.path.exists(path):
            return
        logo = Gtk.Image.new_from_file(path)
        logo.set_pixel_size(72)
        logo.set_margin_start(20)
        logo.set_margin_end(20)
        logo.update_property([Gtk.AccessibleProperty.LABEL], [_("BigLinux Logo")])
        box.append(logo)

    def _retranslate_ui(self):  # noqa: C901 - translates heterogeneous lazy pages
        """Updates all visible text in the application to the new language."""
        self.set_title(_("BigLinux Setup"))
        self.update_property(
            [Gtk.AccessibleProperty.DESCRIPTION],
            [
                _("BigLinux Setup")
                + " \u2014 "
                + _("press Super+Alt+S to start the screen reader")
            ],
        )

        # Update step button accessible labels
        for step in self.steps:
            if button := step.get("button"):
                label_fn = self._STEP_LABELS.get(step["name"])
                if label_fn:
                    button.update_property([Gtk.AccessibleProperty.LABEL], [label_fn()])
                    button.set_tooltip_text(label_fn())

        # Iterate through all pages in the stack, even non-visible ones
        pages = self.stack.get_pages()
        for i in range(pages.get_n_items()):  # type: ignore[attr-defined]
            page = pages.get_item(i)  # type: ignore[attr-defined]
            if not isinstance(page, Adw.ViewStackPage):
                continue

            view = page.get_child()
            view_name = page.get_name()

            # Update the title of the stack page
            if view_name == "language":
                page.set_title(_("Language"))
            elif view_name == "keyboard":
                page.set_title(_("Keyboard"))
            elif view_name == "desktop":
                page.set_title(_("Desktop Layout"))
            elif view_name == "theme":
                page.set_title(_("Theme"))
            elif view_name == "simple_theme":
                page.set_title(_("Theme"))

            # Trigger re-translation within the view itself
            if hasattr(view, "_retranslate_ui"):
                view._retranslate_ui()

    def _ensure_view(self, view_name: str, *args) -> bool:
        """Creates and adds a view to the stack if it doesn't exist."""
        if self.stack.get_child_by_name(view_name):
            return True
        if view_name in {"theme", "simple_theme"}:
            simplified_mode = view_name == "simple_theme"
            if simplified_mode not in self._theme_runtime_states:
                return False
        if not self.stack.get_child_by_name(view_name):
            if view_name == "keyboard":
                self._add_keyboard_view(*args)
            elif view_name == "desktop":
                self._add_desktop_view()
            elif view_name == "theme":
                self._add_theme_view()
            elif view_name == "simple_theme":
                self._add_simple_theme_view()
        return self.stack.get_child_by_name(view_name) is not None

    def _schedule_initial_preload(self, *_args) -> None:
        if self._preload_started:
            return
        self._preload_started = True
        GLib.idle_add(self._preload_next_module)

    def _preload_next_module(self) -> bool:
        if not self._preload_modules:
            return GLib.SOURCE_REMOVE
        module_name = self._preload_modules.pop(0)
        importlib.import_module(module_name)
        if module_name == "ui.keyboard_view":
            self._ensure_view("keyboard", "us")
        elif module_name == "ui.theme_view":
            self._start_theme_runtime_detection()
        return bool(self._preload_modules)

    def _start_theme_runtime_detection(self) -> None:
        from ui.theme_view import ThemeRuntimeState

        modes = {self.uses_simple_theme, not self.uses_simple_theme}

        def detect() -> None:
            states = {
                mode: ThemeRuntimeState.detect(self.system_service, mode)
                for mode in modes
            }
            GLib.idle_add(self._store_theme_runtime_states, states)

        threading.Thread(target=detect, daemon=True).start()

    def _store_theme_runtime_states(self, states: dict[bool, Any]) -> bool:
        self._theme_runtime_states.update(states)
        if "language" in self.completed_steps:
            self._preload_following_views()
        if self._pending_view_name and self._ensure_view(self._pending_view_name):
            view_name = self._pending_view_name
            self._pending_view_name = None
            self.stack.set_visible_child_name(view_name)
        return GLib.SOURCE_REMOVE

    def _preload_following_views(self) -> bool:
        if self.has_desktop_step:
            self._ensure_view("desktop")
        theme_name = "simple_theme" if self.uses_simple_theme else "theme"
        self._ensure_view(theme_name)
        for view_name in ("desktop", theme_name):
            view = self.stack.get_child_by_name(view_name)
            if view is not None and hasattr(view, "load_items"):
                view.load_items()
        return GLib.SOURCE_REMOVE

    def _submit_system_update(self, operation: Callable[..., Any], *args: Any) -> None:
        self._last_system_update = self._system_updates.submit(
            self._run_system_update, operation, args
        )

    @staticmethod
    def _run_system_update(
        operation: Callable[..., Any], args: tuple[Any, ...]
    ) -> None:
        try:
            operation(*args)
        except Exception:
            logger.exception("Background live-session update failed")

    def _wait_for_system_updates(self) -> None:
        # Both callers are GTK signal handlers, so this blocks the main loop:
        # the window stops drawing until sudo timedatectl and localectl come
        # back. They are quick, but an unbounded wait on a hung child froze the
        # wizard with no way out, and the settings are not worth that.
        if self._last_system_update is None:
            return
        try:
            self._last_system_update.result(timeout=15)
        except Exception as error:
            logger.warning("A system settings update did not finish: %s", error)

    def _shutdown_background_services(self) -> None:
        if self._speechd_client is not None:
            try:
                self._speechd_client.close()
            except Exception:
                pass
            self._speechd_client = None
        self._system_updates.shutdown(wait=False)

    _STEP_LABELS = {
        "language": lambda: _("Language"),
        "keyboard": lambda: _("Keyboard"),
        "desktop": lambda: _("Desktop Layout"),
        "theme": lambda: _("Theme"),
    }

    def _add_step_button(self, box, step_info):
        button = Gtk.Button()
        button.set_focusable(True)
        path = os.path.join(ASSETS_DIR, step_info["file"])
        texture = load_svg_texture(path, 48)
        img = Gtk.Image.new_from_paintable(texture)
        img.set_pixel_size(64)
        button.set_child(img)
        button.set_size_request(64, 64)
        button.connect("clicked", self._on_step_button_clicked, step_info["name"])
        button.add_css_class("flat")

        # Accessible label and description for screen readers
        label_fn = self._STEP_LABELS.get(step_info["name"])
        if label_fn:
            step_index = next(
                (i for i, s in enumerate(self.steps) if s["name"] == step_info["name"]),
                0,
            )
            total = len(self.steps)
            button.update_property(
                [Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
                [label_fn(), f"{step_index + 1}/{total}"],
            )
            # Visible tooltip so sighted users can identify the icon-only step button.
            button.set_tooltip_text(label_fn())

        try:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
            button.set_cursor(cursor)
        except Exception:
            pass

        step_info["button"] = button
        if step_info["name"] == "language":
            step_info["img"] = img
        box.append(button)

    def _on_view_changed(self, stack, _param):
        GLib.idle_add(self._update_header_state)
        # Announce the new step to screen readers (ORCA)
        view_name = stack.get_visible_child_name()
        GLib.idle_add(lambda n=view_name: self._announce_step(n))

    def _announce_step(self, view_name: str) -> None:
        """Announce step label and position to screen readers."""
        search_name = "theme" if view_name == "simple_theme" else view_name
        try:
            index = next(
                i for i, s in enumerate(self.steps) if s["name"] == search_name
            )
        except StopIteration:
            return
        total = len(self.steps)
        label_fn = self._STEP_LABELS.get(search_name)
        step_label = label_fn() if label_fn else search_name
        msg = f"{step_label} — {index + 1}/{total}"
        announce(self, msg, assertive=True)

    def _on_step_button_clicked(self, button, view_name):
        # Only allow navigation to completed steps
        if view_name in self.completed_steps:
            self.stack.set_visible_child_name(view_name)

    def _update_header_state(self):
        current_view_name = self.stack.get_visible_child_name()

        # Map simple_theme to theme for header state
        if current_view_name == "simple_theme":
            search_name = "theme"
        else:
            search_name = current_view_name or ""

        try:
            current_index = next(
                i for i, s in enumerate(self.steps) if s["name"] == search_name
            )
        except StopIteration:
            current_index = -1

        for i, step in enumerate(self.steps):
            if button := step.get("button"):
                # Remove all state classes
                button.remove_css_class("step-completed")
                button.remove_css_class("step-current")
                button.remove_css_class("step-pending")
                button.remove_css_class("suggested-action")

                step_name = step["name"]

                if step_name in self.completed_steps:
                    # Completed step - clickable and visually active
                    button.add_css_class("step-completed")
                    button.set_sensitive(True)
                    button.update_state([Gtk.AccessibleState.DISABLED], [False])
                elif i == current_index:
                    # Current step - most prominent and enabled for bright appearance
                    button.add_css_class("step-current")
                    button.set_sensitive(True)  # Keep enabled for bright appearance
                    button.update_state([Gtk.AccessibleState.DISABLED], [False])
                else:
                    # Pending step - inactive
                    button.add_css_class("step-pending")
                    button.set_sensitive(False)
                    button.update_state([Gtk.AccessibleState.DISABLED], [True])

    def _add_language_view(self):
        view = LanguageView()
        view.connect("language-selected", self._on_language_selected)
        self.stack.add_titled(view, "language", _("Language"))

    def _on_language_selected(self, view, selection):
        self.config.language = selection
        params = selection.url_params

        # --- DYNAMIC TRANSLATION ---
        # 1. Set the new language for the entire application
        lang_code = params.get("lang")
        set_language(lang_code)

        # 2. Retranslate all existing UI elements
        self._retranslate_ui()
        # --- END DYNAMIC TRANSLATION ---

        locale_code = getattr(selection, "code", lang_code)
        os.environ["LANG"] = f"{locale_code}.UTF-8"

        # Mark language step as completed
        self.completed_steps.add("language")

        if lang_code_full := getattr(selection, "code", None):
            GLib.timeout_add(50, self._update_language_step_icon, lang_code_full)

        keyboard_layout = params.get("keyboard", "us")

        # If a non-English language is chosen with a 'us' keyboard,
        # default to the 'us(intl)' variant to support accented characters.
        if keyboard_layout == "us" and lang_code != "en":
            keyboard_layout = "us(intl)"

        # LAZY LOADING: Ensure keyboard view exists before updating or showing it
        self._ensure_view("keyboard", keyboard_layout)

        from ui.keyboard_view import KeyboardView

        if isinstance(
            keyboard_view := self.stack.get_child_by_name("keyboard"), KeyboardView
        ):
            keyboard_view.update_primary_layout(keyboard_layout)

        if keyboard_layout not in ["us", "latam"]:
            self.stack.set_visible_child_name("keyboard")
            self._submit_system_update(
                self._apply_language_settings,
                params["language"],
                params["timezone"],
                lang_code,
            )
        else:
            # Also skip for us(intl) if the user doesn't need to see the choice
            self._submit_system_update(
                self._apply_language_settings,
                params["language"],
                params["timezone"],
                lang_code,
            )
            if keyboard_layout == "us(intl)":
                self._on_keyboard_selected(None, keyboard_layout)
            else:
                self._on_keyboard_selected(None, keyboard_layout)
        GLib.timeout_add(100, self._preload_following_views)

    def _update_language_step_icon(self, language_code: str) -> bool:
        step = next((s for s in self.steps if s["name"] == "language"), None)
        if not step or not (image := step.get("img")):
            return GLib.SOURCE_REMOVE
        candidate = os.path.join(ASSETS_DIR, f"headerbar-locale-{language_code}.svg")
        path = (
            candidate
            if os.path.exists(candidate)
            else os.path.join(ASSETS_DIR, "headerbar-locale.svg")
        )
        image.set_from_paintable(load_svg_texture(path, 48))
        image.set_pixel_size(48)
        return GLib.SOURCE_REMOVE

    def _apply_language_settings(
        self, language: str, timezone: str, speech_language: str
    ) -> None:
        self.system_service.apply_language_settings(language, timezone)
        self._set_speechd_language(speech_language)

    def _add_keyboard_view(self, primary_layout):
        from ui.keyboard_view import KeyboardView

        view = KeyboardView(primary_layout=primary_layout)
        view.connect("keyboard-selected", self._on_keyboard_selected)
        self.stack.add_titled(view, "keyboard", _("Keyboard"))

    def _on_keyboard_selected(self, view, layout):
        self.config.keyboard_layout = layout

        # Mark keyboard step as completed
        self.completed_steps.add("keyboard")

        if not self.has_desktop_step:
            # Navigate to simple theme view for simplified environments (GNOME/XFCE/Cinnamon)
            if self._ensure_view("simple_theme"):
                self.stack.set_visible_child_name("simple_theme")
            else:
                self._pending_view_name = "simple_theme"
        else:
            # LAZY LOADING: Ensure desktop view exists before showing it
            self._ensure_view("desktop")
            self.stack.set_visible_child_name("desktop")
        self._submit_system_update(self.system_service.apply_keyboard_layout, layout)

    def _add_desktop_view(self):
        from ui.desktop_view import DesktopView

        view = DesktopView(system_service=self.system_service)
        view.connect("desktop-selected", self._on_desktop_selected)
        self.stack.add_titled(view, "desktop", _("Desktop Layout"))

    def _on_desktop_selected(self, view, layout):
        logger.debug(f"AppWindow received desktop-selected signal for: {layout}")
        if layout != "default":
            self.config.desktop_layout = layout
            self._submit_system_update(self.system_service.apply_desktop_layout, layout)

        # Mark desktop step as completed
        self.completed_steps.add("desktop")

        if self.uses_simple_theme:
            # GNOME has a layout step, but still uses the light/dark theme chooser.
            if self._ensure_view("simple_theme"):
                logger.debug("Navigating to simple theme view...")
                self.stack.set_visible_child_name("simple_theme")
            else:
                self._pending_view_name = "simple_theme"
        else:
            # LAZY LOADING: Ensure theme view exists before showing it
            if self._ensure_view("theme"):
                logger.debug("Navigating to theme view...")
                self.stack.set_visible_child_name("theme")
            else:
                self._pending_view_name = "theme"

    def _add_theme_view(self):
        from ui.theme_view import ThemeView

        view = ThemeView(
            system_service=self.system_service,
            runtime_state=self._theme_runtime_states[False],
        )
        view.connect("theme-selected", self._on_theme_selected)
        self.stack.add_titled(view, "theme", _("Theme"))

    def _on_theme_selected(self, view, theme):
        from ui.theme_view import ThemeView

        self._wait_for_system_updates()
        if theme != "default":
            self.config.theme = theme
            self.system_service.apply_theme(theme)

        # Mark theme step as completed
        self.completed_steps.add("theme")

        # Update config with extra options from the theme view
        theme_view = self.stack.get_child_by_name("theme")
        if isinstance(theme_view, ThemeView):
            self.config.enable_jamesdsp = theme_view.is_jamesdsp_enabled()
            self.config.enable_enhanced_contrast = theme_view.is_contrast_enabled()

            # Apply JamesDSP settings immediately when theme is selected
            self.system_service.apply_jamesdsp_settings(self.config.enable_jamesdsp)

        self.system_service.finalize_setup(self.config)
        self._shutdown_background_services()
        self.close()

    def _add_simple_theme_view(self):
        """Creates and adds the simplified theme view for GNOME/XFCE/Cinnamon."""
        from ui.theme_view import ThemeView

        view = ThemeView(
            system_service=self.system_service,
            runtime_state=self._theme_runtime_states[True],
            simplified_mode=True,
        )
        view.connect("theme-selected", self._on_simple_theme_selected)
        self.stack.add_titled(view, "simple_theme", _("Theme"))

    def _on_simple_theme_selected(self, view, theme):
        """Handle theme selection from simplified theme view."""
        from ui.theme_view import ThemeView

        logger.info(f"========== SIMPLE THEME SELECTED: {theme} ==========")

        try:
            self._wait_for_system_updates()
            # Mark theme step as completed
            self.completed_steps.add("theme")
            logger.debug(
                f"Marked theme step as completed. Completed steps: {self.completed_steps}"
            )

            # Save to config
            self.config.simple_theme = theme
            logger.debug(f"Saved theme to config: {theme}")

            # Apply simple theme (light or dark)
            logger.info(f"Applying simple theme: {theme}")
            self.system_service.apply_simple_theme(theme)
            logger.info("Simple theme applied successfully")

            # Get JamesDSP and contrast settings from the theme view
            theme_view = self.stack.get_child_by_name("simple_theme")
            if isinstance(theme_view, ThemeView):
                jamesdsp = theme_view.is_jamesdsp_enabled()
                contrast = theme_view.is_contrast_enabled()
                self.config.enable_jamesdsp = jamesdsp
                self.config.enable_enhanced_contrast = contrast
                logger.info(f"JamesDSP: {jamesdsp}, Enhanced Contrast: {contrast}")

                # Apply JamesDSP settings immediately when theme is selected
                self.system_service.apply_jamesdsp_settings(jamesdsp)
            else:
                logger.warning("Could not get theme_view from stack")

            # Finalize and close
            logger.info("Finalizing setup...")
            self.system_service.finalize_setup(self.config)
            logger.info("Setup finalized. Closing application...")
            self._shutdown_background_services()
            self.close()
            logger.info("Application closed successfully")
        except Exception as e:
            logger.error(f"ERROR in _on_simple_theme_selected: {e}", exc_info=True)

    def _on_key_press_event(self, controller, keyval, keycode, state):
        # Super+Alt+S: enable accessibility (speech via speech-dispatcher + Kokoro)
        # Use keycode 39 (physical 'S' key) so it works on any keyboard layout
        if (
            keycode == 39
            and state & Gdk.ModifierType.SUPER_MASK
            and state & Gdk.ModifierType.ALT_MASK
        ):
            set_accessibility_enabled(True)
            if self.config.language is not None:
                lang_code = self.config.language.url_params.get("lang")
                self._submit_system_update(self._set_speechd_language, lang_code)
            lang_view = self.stack.get_child_by_name("language")
            if isinstance(lang_view, LanguageView):
                lang_view.enable_voice_preview()
            speak(_("Accessibility enabled. Use arrow keys to navigate."))
            return True
        current_view = self.stack.get_visible_child()
        if isinstance(current_view, LanguageView):
            # Type-ahead search must not swallow accelerators. Ctrl+Q carries
            # the same printable keyval as Q, and this controller runs in the
            # capture phase, so the language search was typing a "q" and
            # returning True before the shortcut could reach anything.
            if state & (
                Gdk.ModifierType.CONTROL_MASK
                | Gdk.ModifierType.ALT_MASK
                | Gdk.ModifierType.SUPER_MASK
            ):
                return False
            return current_view.handle_global_key_press(keyval)
        return False

    def _set_speechd_language(self, lang_code: str) -> None:
        """Set speech-dispatcher language so ORCA speaks in the selected language."""
        if not lang_code or not is_accessibility_enabled():
            return
        try:
            import speechd

            if self._speechd_client is None:
                self._speechd_client = speechd.SSIPClient("biglinux-wizard-lang")
            self._speechd_client.set_language(lang_code)
        except Exception:
            pass
