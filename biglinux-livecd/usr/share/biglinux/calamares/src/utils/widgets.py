# src/utils/widgets.py

"""
Reusable GTK4/Adwaita widget factory functions for BigLinux Calamares.
These utilities provide consistent UI components across different pages.
"""

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw


def create_option_card(
    icon_name: str,
    title: str,
    description: str,
    button_text: str,
    button_style: str,
    callback,
    description2: str = None,
    card_width: int = 280,
    card_height: int = 320
) -> Gtk.Box:
    """
    Factory function to create a styled option card widget.
    
    Used for main menu options with icon, title, description, and action button.
    
    Args:
        icon_name: GTK icon name for the card header
        title: Card title text
        description: Main description text (supports wrapping)
        button_text: Text for the action button
        button_style: CSS class for button style (e.g., "suggested-action", "destructive-action")
        callback: Function to call when button is clicked
        description2: Optional secondary description text
        card_width: Minimum card width in pixels (default: 280)
        card_height: Minimum card height in pixels (default: 320)
    
    Returns:
        Gtk.Box containing the complete card widget with action_button attribute
    """
    card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    card_box.set_size_request(card_width, card_height)
    card_box.set_valign(Gtk.Align.CENTER)
    card_box.set_halign(Gtk.Align.CENTER)

    card_bin = Adw.Bin()
    card_bin.add_css_class("card")
    card_box.append(card_bin)

    content_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.FILL,
        hexpand=True,
        vexpand=True,
        margin_top=24, margin_bottom=24, margin_start=24, margin_end=24
    )
    card_bin.set_child(content_box)

    # Icon
    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.set_pixel_size(64)
    icon.add_css_class("option-icon")
    content_box.append(icon)

    # Title
    title_label = Gtk.Label(label=title, halign=Gtk.Align.CENTER)
    title_label.add_css_class("title-2")
    content_box.append(title_label)

    # Description box
    desc_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=4,
        vexpand=True,
        valign=Gtk.Align.CENTER
    )
    content_box.append(desc_box)
    
    desc_label = Gtk.Label(
        label=description,
        wrap=True,
        justify=Gtk.Justification.CENTER,
        halign=Gtk.Align.CENTER,
        max_width_chars=35
    )
    desc_label.add_css_class("body")
    desc_box.append(desc_label)

    if description2:
        desc2_label = Gtk.Label(
            label=description2,
            wrap=True,
            justify=Gtk.Justification.CENTER,
            halign=Gtk.Align.CENTER,
            max_width_chars=35
        )
        desc2_label.add_css_class("body")
        desc_box.append(desc2_label)

    # Action button
    button = Gtk.Button(
        label=button_text,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.END
    )
    button.add_css_class(button_style)
    button.add_css_class("pill")
    button.connect("clicked", callback)
    content_box.append(button)
    
    # Store button for later access if needed
    card_box.action_button = button
    
    return card_box
