#!/usr/bin/env python3
"""
BigLinux Calamares Configuration Tool
Main entry point for the GTK4 application
"""

import gettext
import logging
import sys

import gi

# Ensure we're using the correct GTK version
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk
from src.app import CalamaresApp


def setup_logging():
    """Configure logging for the application"""
    handlers = [logging.StreamHandler(sys.stdout)]

    # Try to add file handler, but don't fail if can't create log file
    try:
        handlers.append(logging.FileHandler("/tmp/calamares-config.log", mode="a"))
    except PermissionError:
        # Note: Using stderr since logger is not yet available during bootstrap
        sys.stderr.write("Warning: Could not create log file, using console only\n")
    except Exception as e:
        sys.stderr.write(f"Warning: Log file error: {e}\n")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def setup_translations():
    """Setup gettext translations"""
    try:
        # Set up translations (unified with biglinux-livecd)
        gettext.bindtextdomain("biglinux-livecd", "/usr/share/locale")
        gettext.textdomain("biglinux-livecd")
        gettext.install("biglinux-livecd")

        # Also bind for Gtk
        import locale

        locale.setlocale(locale.LC_ALL, "")

    except Exception as e:
        logging.warning(f"Failed to setup translations: {e}")
        # Fallback to English
        import builtins

        builtins.__dict__["_"] = lambda x: x

def load_custom_css():
    """Load custom CSS for application-wide styling."""
    css_provider = Gtk.CssProvider()
    # The CSS rule to make the window background slightly transparent.
    # This creates a "frosted glass" effect on desktops that support it.
    css_data = b"""
    window.background {
        background-color: alpha(@theme_bg_color, 0.97);
    }
    """
    css_provider.load_from_data(css_data)

    display = Gdk.Display.get_default()
    if display:
        Gtk.StyleContext.add_provider_for_display(
            display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def setup_icon_theme():
    """Set the preferred icon theme to bigicons-papient for better icon coverage."""
    display = Gdk.Display.get_default()
    if display:
        icon_theme = Gtk.IconTheme.get_for_display(display)
        # Add bigicons-papient as the primary search path for icons
        # This ensures that app icons from this theme are prioritized
        icon_theme.add_search_path("/usr/share/icons/bigicons-papient/48x48/apps")
        icon_theme.add_search_path("/usr/share/icons/bigicons-papient/scalable/apps")
        icon_theme.add_search_path("/usr/share/icons/bigicons-papient/22x22/panel")
        icon_theme.add_search_path("/usr/share/icons/bigicons-papient/16x16/panel")
        # Also add the dark variant as fallback
        icon_theme.add_search_path("/usr/share/icons/bigicons-papient-dark/48x48/apps")
        icon_theme.add_search_path("/usr/share/icons/bigicons-papient-dark/scalable/apps")
        logging.getLogger(__name__).info("Icon theme search paths configured for bigicons-papient")


def main():
    """Main application entry point"""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting BigLinux Calamares Configuration Tool")

        # Setup translations
        setup_translations()

        # Initialize Adwaita
        Adw.init()

        # Load custom application styling for effects like transparency.
        load_custom_css()

        # Configure icon theme to use bigicons-papient for better coverage
        setup_icon_theme()

        # Create and run the application
        app = CalamaresApp()
        exit_code = app.run(sys.argv)

        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
