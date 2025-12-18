import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, GdkPixbuf, GLib, Gdk
from translations import _, set_language
from config import SetupConfig
from services import SystemService
from ui.language_view import LanguageView
from ui.keyboard_view import KeyboardView
from ui.desktop_view import DesktopView
from ui.theme_view import ThemeView
from logging_config import get_logger
import os

logger = get_logger()

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

# Default BigLinux logo paths
DEFAULT_LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
DEFAULT_COMM_LOGO_PATH = os.path.join(ASSETS_DIR, "comm-logo.png")


def get_logo_path(system_service: SystemService = None):
    """
    Returns the appropriate logo path for the current distribution.
    XivaStudio custom logos take precedence if they exist.
    """
    if system_service:
        xiva_logo = system_service.get_xivastudio_logo_path()
        if xiva_logo:
            return xiva_logo
    # Fallback to default BigLinux logo
    return DEFAULT_LOGO_PATH


def get_comm_logo_path(system_service: SystemService = None):
    """
    Returns the appropriate simplified/community logo path.
    XivaStudio custom logos take precedence if they exist.
    """
    if system_service:
        xiva_logo = system_service.get_xivastudio_logo_path()
        if xiva_logo:
            return xiva_logo
    # Fallback to default BigLinux comm logo
    return DEFAULT_COMM_LOGO_PATH


def load_svg_pixbuf(path, size):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
    except GLib.Error as e:
        logger.error(f"Failed to load SVG {path}: {e}")
        return GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)


class AppWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AppWindow"

    def __init__(self, system_service: SystemService, **kwargs):
        super().__init__(**kwargs)
        self.system_service = system_service
        self.config = SetupConfig()
        self.completed_steps = set()  # Track completed steps
        self.is_simplified_env = system_service.is_simplified_environment()
        self.set_title(_("BigLinux Setup"))

        # --- Fullscreen for Xorg without compositor ---
        # This approach makes the window undecorated and sized to the monitor.
        # It's more reliable in environments without a full-featured window manager.
        self.set_decorated(False)
        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors.get_n_items() > 0:
                # Use the first monitor as the target
                monitor = monitors.get_item(0)
                geometry = monitor.get_geometry()
                self.set_default_size(geometry.width, geometry.height)
            else:
                # Fallback to the standard method if we can't get monitor info
                self.fullscreen()
        else:
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

        # Create and add a Gtk.EventControllerKey for global key events
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._on_key_press_event)
        self.add_controller(key_controller)

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # --- Header Area (Full-Width Wrapper) ---
        header_wrapper = Gtk.CenterBox()
        header_wrapper.add_css_class("app-header")
        root_box.append(header_wrapper)

        # --- Centered Header Content ---
        header_content_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=15,
            margin_top=15,
            margin_bottom=15,
        )
        header_wrapper.set_center_widget(header_content_box)

        # Define steps based on environment
        if self.is_simplified_env:
            self.steps = [
                {"name": "language", "file": "headerbar-locale.svg"},
                {"name": "keyboard", "file": "headerbar-keyboard.svg"},
            ]
        else:
            self.steps = [
                {"name": "language", "file": "headerbar-locale.svg"},
                {"name": "keyboard", "file": "headerbar-keyboard.svg"},
                {"name": "desktop", "file": "headerbar-display.svg"},
                {"name": "theme", "file": "headerbar-theme.svg"},
            ]

        # Build header layout based on environment
        if self.is_simplified_env:
            # Simplified layout: [Language] [comm-logo.png] [Keyboard]
            self._add_step_button(header_content_box, self.steps[0])

            # Use comm-logo.png for simplified environments (XivaStudio override if exists)
            logo_path = get_comm_logo_path(self.system_service)
            if os.path.exists(logo_path):
                logo = Gtk.Image.new_from_file(logo_path)
                logo.set_pixel_size(72)
                logo.set_margin_start(20)
                logo.set_margin_end(20)
                header_content_box.append(logo)
            
            self._add_step_button(header_content_box, self.steps[1])
        else:
            # Full layout: [Language] [Keyboard] [logo.png] [Desktop] [Theme]
            self._add_step_button(header_content_box, self.steps[0])
            self._add_step_button(header_content_box, self.steps[1])

            # Use main logo (XivaStudio override if exists)
            logo_path = get_logo_path(self.system_service)
            if os.path.exists(logo_path):
                logo = Gtk.Image.new_from_file(logo_path)
                logo.set_pixel_size(72)
                logo.set_margin_start(20)
                logo.set_margin_end(20)
                header_content_box.append(logo)

            self._add_step_button(header_content_box, self.steps[2])
            self._add_step_button(header_content_box, self.steps[3])

        # --- Content Area ---
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        content_box.add_css_class("app-content")
        root_box.append(content_box)

        self.stack = Adw.ViewStack()
        self.stack.set_vexpand(True)
        self.stack.connect("notify::visible-child", self._on_view_changed)
        content_box.append(self.stack)

        # --- LAZY LOADING: Only create the first view initially ---
        self._add_language_view()

        # Set initial view and update header state
        self.stack.set_visible_child_name("language")
        GLib.idle_add(self._update_header_state)

        return root_box

    def _retranslate_ui(self):
        """Updates all visible text in the application to the new language."""
        self.set_title(_("BigLinux Setup"))

        # Iterate through all pages in the stack, even non-visible ones
        pages = self.stack.get_pages()
        for i in range(pages.get_n_items()):
            page = pages.get_item(i)
            if not page:
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

            # Trigger re-translation within the view itself
            if hasattr(view, "_retranslate_ui"):
                view._retranslate_ui()

    def _ensure_view(self, view_name: str, *args):
        """Creates and adds a view to the stack if it doesn't exist."""
        if not self.stack.get_child_by_name(view_name):
            if view_name == "keyboard":
                self._add_keyboard_view(*args)
            elif view_name == "desktop":
                self._add_desktop_view()
            elif view_name == "theme":
                self._add_theme_view()

    def _add_step_button(self, box, step_info):
        button = Gtk.Button()
        button.set_focusable(False)
        path = os.path.join(ASSETS_DIR, step_info["file"])
        pixbuf = load_svg_pixbuf(path, 32)
        img = Gtk.Image.new_from_pixbuf(pixbuf)
        button.set_child(img)
        button.set_size_request(48, 48)
        button.connect("clicked", self._on_step_button_clicked, step_info["name"])
        button.add_css_class("flat")

        try:
            cursor = Gdk.Cursor.new_from_name("pointer", None)
            button.set_cursor(cursor)
        except Exception:
            pass

        step_info["button"] = button
        if step_info["name"] == "language":
            step_info["img"] = img
        box.append(button)

    def _on_view_changed(self, stack, param):
        GLib.idle_add(self._update_header_state)

    def _on_step_button_clicked(self, button, view_name):
        # Only allow navigation to completed steps
        if view_name in self.completed_steps:
            self.stack.set_visible_child_name(view_name)

    def _update_header_state(self):
        current_view_name = self.stack.get_visible_child_name()
        try:
            current_index = next(
                i for i, s in enumerate(self.steps) if s["name"] == current_view_name
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
                elif i == current_index:
                    # Current step - most prominent and enabled for bright appearance
                    button.add_css_class("step-current")
                    button.set_sensitive(True)  # Keep enabled for bright appearance
                else:
                    # Pending step - inactive
                    button.add_css_class("step-pending")
                    button.set_sensitive(False)

    def _add_language_view(self):
        view = LanguageView()
        view.connect("language-selected", self._on_language_selected)
        self.stack.add_titled(view, "language", _("Language"))

    def _on_language_selected(self, view, selection):
        self.config.language = selection
        params = selection.url_params
        self.system_service.apply_language_settings(
            params["language"], params["timezone"]
        )

        # --- DYNAMIC TRANSLATION ---
        # 1. Set the new language for the entire application
        lang_code = params.get("lang")
        set_language(lang_code)

        # 2. Retranslate all existing UI elements
        self._retranslate_ui()
        # --- END DYNAMIC TRANSLATION ---

        # Mark language step as completed
        self.completed_steps.add("language")

        if lang_code_full := getattr(selection, "code", None):
            if step := next((s for s in self.steps if s["name"] == "language"), None):
                if img := step.get("img"):
                    candidate = os.path.join(
                        ASSETS_DIR, f"headerbar-locale-{lang_code_full}.svg"
                    )
                    path = (
                        candidate
                        if os.path.exists(candidate)
                        else os.path.join(ASSETS_DIR, "headerbar-locale.svg")
                    )
                    pixbuf = load_svg_pixbuf(path, 32)
                    img.set_from_pixbuf(pixbuf)

        keyboard_layout = params.get("keyboard", "us")

        # If a non-English language is chosen with a 'us' keyboard,
        # default to the 'us(intl)' variant to support accented characters.
        if keyboard_layout == "us" and lang_code != "en":
            keyboard_layout = "us(intl)"

        # LAZY LOADING: Ensure keyboard view exists before updating or showing it
        self._ensure_view("keyboard", keyboard_layout)

        if keyboard_view := self.stack.get_child_by_name("keyboard"):
            keyboard_view.update_primary_layout(keyboard_layout)

        if keyboard_layout not in ["us", "latam"]:
            self.stack.set_visible_child_name("keyboard")
        else:
            # Also skip for us(intl) if the user doesn't need to see the choice
            if keyboard_layout == "us(intl)":
                 self._on_keyboard_selected(None, keyboard_layout)
            else:
                 self._on_keyboard_selected(None, keyboard_layout)


    def _add_keyboard_view(self, primary_layout):
        view = KeyboardView(primary_layout=primary_layout)
        view.connect("keyboard-selected", self._on_keyboard_selected)
        self.stack.add_titled(view, "keyboard", _("Keyboard"))

    def _on_keyboard_selected(self, view, layout):
        self.config.keyboard_layout = layout
        self.system_service.apply_keyboard_layout(layout)

        # Mark keyboard step as completed
        self.completed_steps.add("keyboard")

        if self.is_simplified_env:
            # Skip desktop and theme for simplified environments (GNOME/XFCE/Cinnamon)
            self.system_service.finalize_setup(self.config)
            self.close()
        else:
            # LAZY LOADING: Ensure desktop view exists before showing it
            self._ensure_view("desktop")
            self.stack.set_visible_child_name("desktop")

    def _add_desktop_view(self):
        view = DesktopView(system_service=self.system_service)
        view.connect("desktop-selected", self._on_desktop_selected)
        self.stack.add_titled(view, "desktop", _("Desktop Layout"))

    def _on_desktop_selected(self, view, layout):
        logger.debug(f"AppWindow received desktop-selected signal for: {layout}")
        if layout != "default":
            self.config.desktop_layout = layout
            self.system_service.apply_desktop_layout(layout)

        # Mark desktop step as completed
        self.completed_steps.add("desktop")

        # LAZY LOADING: Ensure theme view exists before showing it
        self._ensure_view("theme")
        logger.debug("Navigating to theme view...")
        self.stack.set_visible_child_name("theme")

    def _add_theme_view(self):
        view = ThemeView(system_service=self.system_service)
        view.connect("theme-selected", self._on_theme_selected)
        self.stack.add_titled(view, "theme", _("Theme"))

    def _on_theme_selected(self, view, theme):
        if theme != "default":
            self.config.theme = theme
            self.system_service.apply_theme(theme)

        # Mark theme step as completed
        self.completed_steps.add("theme")

        # Update config with extra options from the theme view
        theme_view = self.stack.get_child_by_name("theme")
        if theme_view:
            self.config.enable_jamesdsp = theme_view.is_jamesdsp_enabled()
            self.config.enable_enhanced_contrast = theme_view.is_contrast_enabled()

        self.system_service.finalize_setup(self.config)
        self.close()

    def _on_key_press_event(self, controller, keyval, keycode, state):
        current_view = self.stack.get_visible_child()
        if isinstance(current_view, LanguageView):
            return current_view.handle_global_key_press(keyval)
        return False
