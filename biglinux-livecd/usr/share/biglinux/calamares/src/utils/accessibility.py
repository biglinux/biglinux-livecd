"""Accessibility utilities for ORCA screen reader support (AT-SPI2).

Provides helper functions used across the Calamares pre-installer
to label widgets, announce page changes, and start ORCA if needed.
"""

import logging
import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

logger = logging.getLogger(__name__)

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


def set_label(widget: Gtk.Accessible, label: str) -> None:
    """Set the accessible LABEL property on a widget."""
    if widget and label:
        try:
            widget.update_property(
                [Gtk.AccessibleProperty.LABEL], [label]
            )
        except Exception as e:
            logger.debug(f"set_label() failed: {e}")


def set_description(widget: Gtk.Accessible, description: str) -> None:
    """Set the accessible DESCRIPTION property on a widget."""
    if widget and description:
        try:
            widget.update_property(
                [Gtk.AccessibleProperty.DESCRIPTION], [description]
            )
        except Exception as e:
            logger.debug(f"set_description() failed: {e}")


def set_labelled_by(widget: Gtk.Accessible, label_widget: Gtk.Accessible) -> None:
    """Set LABELLED_BY relation so screen readers associate a widget with its label."""
    if widget and label_widget:
        try:
            widget.update_relation(
                [Gtk.AccessibleRelation.LABELLED_BY], [label_widget]
            )
        except Exception as e:
            logger.debug(f"set_labelled_by() failed: {e}")


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
