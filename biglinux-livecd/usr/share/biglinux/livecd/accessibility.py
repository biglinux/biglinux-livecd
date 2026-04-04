"""Accessibility utilities for ORCA screen reader support (AT-SPI2)."""

import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from logging_config import get_logger

logger = get_logger()

_HAS_ANNOUNCE = hasattr(Gtk.Accessible, "announce")


def announce(widget: Gtk.Accessible, message: str, assertive: bool = False) -> None:
    """
    Announce a message to screen readers (ORCA) via AT-SPI2.
    Uses Gtk.Accessible.announce() on GTK 4.14+.
    """
    if not message or not widget:
        return
    if _HAS_ANNOUNCE:
        try:
            priority = (
                Gtk.AccessibleAnnouncementPriority.HIGH
                if assertive
                else Gtk.AccessibleAnnouncementPriority.MEDIUM
            )
            widget.announce(message, priority)
        except Exception as e:
            logger.debug(f"announce() failed: {e}")
    else:
        logger.debug(f"a11y: {message}")


def start_orca() -> bool:
    """Start ORCA screen reader if not already running."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "orca"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("ORCA is already running")
            return True
        subprocess.Popen(
            ["orca"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Started ORCA screen reader")
        return True
    except FileNotFoundError:
        logger.warning("ORCA not found on this system")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Timeout checking for ORCA process")
        return False


def ensure_orca_disabled() -> None:
    """Kill any running ORCA and disable GNOME auto-start of screen reader."""
    subprocess.Popen(
        ["pkill", "-x", "orca"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.Popen(
        ["gsettings", "set", "org.gnome.desktop.a11y.applications",
         "screen-reader-enabled", "false"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info("Ensured ORCA is disabled at startup")
