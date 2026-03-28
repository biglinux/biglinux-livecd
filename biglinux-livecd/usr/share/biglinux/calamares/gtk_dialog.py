#!/usr/bin/env python3
"""
GTK4/Adwaita dialog utility — drop-in replacement for zenity.
Accessible to ORCA screen reader with proper AT-SPI2 labels.

Usage:
    gtk_dialog.py progress --title TEXT --text TEXT [--pulsate] [--auto-close] [--percentage N]
    gtk_dialog.py question --title TEXT --text TEXT [--ok-label L] [--cancel-label L] [--icon-name I] [--width W]
    gtk_dialog.py error    --title TEXT --text TEXT [--width W]
    gtk_dialog.py info     --title TEXT --text TEXT [--width W]
    gtk_dialog.py list     --title TEXT --text TEXT --column C ... --row V ... [--radiolist] [--print-column N]

Exit codes match zenity: 0 = OK/Yes, 1 = Cancel/No, -1 = Error/Timeout.
"""

import argparse
import gettext
import re
import signal
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

# ── i18n ──────────────────────────────────────────────────────────────────────
gettext.bindtextdomain("biglinux-livecd", "/usr/share/locale")
gettext.textdomain("biglinux-livecd")
_ = gettext.gettext

# ── Accessibility helper ──────────────────────────────────────────────────────
_HAS_ANNOUNCE = hasattr(Gtk.Accessible, "announce")


def announce(widget: Gtk.Accessible, message: str, assertive: bool = False) -> None:
    """Announce a message to screen readers via AT-SPI2."""
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
        except Exception:
            pass


def strip_pango_markup(text: str) -> str:
    """Remove Pango/HTML markup tags to produce plain accessible text."""
    return re.sub(r"<[^>]+>", "", text or "")


# ── Shared application ───────────────────────────────────────────────────────
_exit_code = 1  # default Cancel
_selected_value = ""


class DialogApp(Adw.Application):
    """Single-instance GTK4 application for showing one dialog and quitting."""

    def __init__(self, dialog_func, args):
        super().__init__(
            application_id="com.biglinux.gtk-dialog",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self._dialog_func = dialog_func
        self._args = args
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        self._dialog_func(self, self._args)


# ── Progress dialog ──────────────────────────────────────────────────────────
def _show_progress(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(application=app, title=args.title or _("Progress"),
                     default_width=args.width or 400, default_height=140)
    win.set_deletable(False)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                  margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    win.set_content(box)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER)
    label.update_property(
        [Gtk.AccessibleProperty.LABEL], [plain_text]
    )
    box.append(label)

    bar = Gtk.ProgressBar(show_text=False, hexpand=True)
    bar.update_property(
        [Gtk.AccessibleProperty.LABEL], [plain_text]
    )
    box.append(bar)

    win.update_property(
        [Gtk.AccessibleProperty.LABEL], [args.title or _("Progress")]
    )
    announce(win, plain_text, assertive=True)

    if args.pulsate:
        # Pulse until stdin closes or text changes
        def pulse():
            bar.pulse()
            return True
        pulse_id = GLib.timeout_add(120, pulse)

        def _read_stdin():
            global _exit_code
            try:
                for line in sys.stdin:
                    line = line.strip()
                    if line.startswith("#"):
                        msg = line.lstrip("# ").strip()
                        GLib.idle_add(label.set_text, msg)
                        GLib.idle_add(announce, win, msg)
                    elif line.isdigit():
                        pass  # ignore percentage in pulsate mode
            except Exception:
                pass
            GLib.idle_add(GLib.source_remove, pulse_id)
            _exit_code = 0
            if args.auto_close:
                GLib.idle_add(app.quit)

        threading.Thread(target=_read_stdin, daemon=True).start()
    else:
        initial_pct = args.percentage or 0
        bar.set_fraction(initial_pct / 100.0)

        def _read_stdin():
            global _exit_code
            try:
                for line in sys.stdin:
                    line = line.strip()
                    if line.startswith("#"):
                        msg = line.lstrip("# ").strip()
                        GLib.idle_add(label.set_text, msg)
                        GLib.idle_add(announce, win, msg)
                    elif line.isdigit():
                        pct = min(int(line), 100)
                        GLib.idle_add(bar.set_fraction, pct / 100.0)
            except Exception:
                pass
            _exit_code = 0
            if args.auto_close:
                GLib.idle_add(app.quit)

        threading.Thread(target=_read_stdin, daemon=True).start()

    win.present()


# ── Question dialog ──────────────────────────────────────────────────────────
def _show_question(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(application=app, title=args.title or _("Question"),
                     default_width=args.width or 500, default_height=-1)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                  margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    win.set_content(box)

    icon_name = args.icon_name or "dialog-question"
    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.CENTER)
    box.append(icon)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER,
                      max_width_chars=60, use_markup=False)
    label.update_property(
        [Gtk.AccessibleProperty.LABEL], [plain_text]
    )
    box.append(label)

    btn_box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER, margin_top=8)
    box.append(btn_box)

    cancel_label = args.cancel_label or _("Close")
    ok_label = args.ok_label or _("Continue")

    cancel_btn = Gtk.Button(label=cancel_label)
    cancel_btn.add_css_class("pill")
    cancel_btn.update_property(
        [Gtk.AccessibleProperty.LABEL], [cancel_label]
    )
    btn_box.append(cancel_btn)

    ok_btn = Gtk.Button(label=ok_label)
    ok_btn.add_css_class("suggested-action")
    ok_btn.add_css_class("pill")
    ok_btn.update_property(
        [Gtk.AccessibleProperty.LABEL], [ok_label]
    )
    btn_box.append(ok_btn)

    def _on_ok(_btn):
        global _exit_code
        _exit_code = 0
        app.quit()

    def _on_cancel(_btn):
        global _exit_code
        _exit_code = 1
        app.quit()

    ok_btn.connect("clicked", _on_ok)
    cancel_btn.connect("clicked", _on_cancel)
    win.connect("close-request", lambda _w: (_on_cancel(None), True)[1])

    win.update_property(
        [Gtk.AccessibleProperty.LABEL], [args.title or _("Question")]
    )
    announce(win, plain_text, assertive=True)
    win.present()
    ok_btn.grab_focus()


# ── Error dialog ─────────────────────────────────────────────────────────────
def _show_error(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(application=app, title=args.title or _("Error"),
                     default_width=args.width or 500, default_height=-1)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                  margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    win.set_content(box)

    icon = Gtk.Image.new_from_icon_name("dialog-error")
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.CENTER)
    box.append(icon)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER,
                      max_width_chars=60, use_markup=False)
    label.update_property(
        [Gtk.AccessibleProperty.LABEL], [plain_text]
    )
    box.append(label)

    btn = Gtk.Button(label=_("Close"), halign=Gtk.Align.CENTER)
    btn.add_css_class("pill")
    btn.update_property(
        [Gtk.AccessibleProperty.LABEL], [_("Close")]
    )
    btn.connect("clicked", lambda _b: app.quit())
    box.append(btn)

    _exit_code = 0
    win.update_property(
        [Gtk.AccessibleProperty.LABEL], [args.title or _("Error")]
    )
    announce(win, plain_text, assertive=True)
    win.present()
    btn.grab_focus()


# ── Info dialog ──────────────────────────────────────────────────────────────
def _show_info(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(application=app, title=args.title or _("Information"),
                     default_width=args.width or 500, default_height=-1)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                  margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    win.set_content(box)

    icon = Gtk.Image.new_from_icon_name("dialog-information")
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.CENTER)
    box.append(icon)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER,
                      max_width_chars=60, use_markup=False)
    label.update_property(
        [Gtk.AccessibleProperty.LABEL], [plain_text]
    )
    box.append(label)

    btn = Gtk.Button(label=_("Close"), halign=Gtk.Align.CENTER)
    btn.add_css_class("pill")
    btn.update_property(
        [Gtk.AccessibleProperty.LABEL], [_("Close")]
    )
    btn.connect("clicked", lambda _b: app.quit())
    box.append(btn)

    _exit_code = 0
    win.update_property(
        [Gtk.AccessibleProperty.LABEL], [args.title or _("Information")]
    )
    announce(win, plain_text)
    win.present()
    btn.grab_focus()


# ── List / Radio list dialog ─────────────────────────────────────────────────
def _show_list(app: DialogApp, args):
    global _exit_code, _selected_value

    win = Adw.Window(application=app, title=args.title or _("Select"),
                     default_width=args.width or 480, default_height=args.height or 350)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                  margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    win.set_content(box)

    plain_text = strip_pango_markup(args.text or "")
    header_label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER)
    header_label.update_property(
        [Gtk.AccessibleProperty.LABEL], [plain_text]
    )
    box.append(header_label)

    # Parse rows/columns
    columns = args.column or []
    num_cols = len(columns)
    raw_rows = args.row or []

    # Build row groups
    rows = []
    for i in range(0, len(raw_rows), num_cols):
        chunk = raw_rows[i:i + num_cols]
        if len(chunk) == num_cols:
            rows.append(chunk)

    print_col = (args.print_column or 1) - 1  # 0-indexed
    hide_col = (args.hide_column or 0) - 1

    # Radiolist mode with Adw.ActionRows and check marks
    listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    listbox.add_css_class("boxed-list")

    scrolled = Gtk.ScrolledWindow(vexpand=True)
    scrolled.set_child(listbox)
    box.append(scrolled)

    check_group = []  # List of (row_widget, Gtk.CheckButton, value)

    for row_data in rows:
        # Determine display text (skip hidden columns)
        display_parts = []
        for ci, cell in enumerate(row_data):
            if ci != hide_col and not (args.radiolist and ci == 0):
                display_parts.append(cell)
        display_text = " — ".join(display_parts) if display_parts else str(row_data)

        value = row_data[print_col] if print_col < len(row_data) else ""

        action_row = Adw.ActionRow(title=display_text)
        action_row.update_property(
            [Gtk.AccessibleProperty.LABEL], [display_text]
        )

        check_btn = Gtk.CheckButton()
        check_btn.set_halign(Gtk.Align.CENTER)
        check_btn.set_valign(Gtk.Align.CENTER)

        # Link radio buttons together
        if args.radiolist and check_group:
            check_btn.set_group(check_group[0][1])

        # Pre-select the first "TRUE" row
        if args.radiolist and len(row_data) > 0 and row_data[0].upper() == "TRUE":
            check_btn.set_active(True)
            _selected_value = value

        action_row.add_prefix(check_btn)
        action_row.set_activatable_widget(check_btn)
        listbox.append(action_row)
        check_group.append((action_row, check_btn, value))

    def _on_check_toggled(btn, val):
        global _selected_value
        if btn.get_active():
            _selected_value = val

    for _, cb, val in check_group:
        cb.connect("toggled", _on_check_toggled, val)

    btn_box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
    box.append(btn_box)

    cancel_btn = Gtk.Button(label=_("Close"))
    cancel_btn.add_css_class("pill")
    btn_box.append(cancel_btn)

    ok_btn = Gtk.Button(label=_("OK"))
    ok_btn.add_css_class("suggested-action")
    ok_btn.add_css_class("pill")
    btn_box.append(ok_btn)

    def _on_ok(_b):
        global _exit_code
        _exit_code = 0
        app.quit()

    def _on_cancel(_b):
        global _exit_code
        _exit_code = 1
        app.quit()

    ok_btn.connect("clicked", _on_ok)
    cancel_btn.connect("clicked", _on_cancel)

    win.update_property(
        [Gtk.AccessibleProperty.LABEL], [args.title or _("Select")]
    )
    announce(win, plain_text)
    win.present()


# ── Argument parser ──────────────────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(description="GTK4/Adw dialog utility")
    sub = parser.add_subparsers(dest="dialog_type", required=True)

    # Common arguments for all dialog types
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--title", default="")
    common.add_argument("--text", default="")
    common.add_argument("--width", type=int, default=0)
    common.add_argument("--height", type=int, default=0)
    common.add_argument("--icon-name", default="")
    common.add_argument("--attach", default="")  # ignored, compatibility

    # Progress
    p_prog = sub.add_parser("progress", parents=[common])
    p_prog.add_argument("--pulsate", action="store_true")
    p_prog.add_argument("--auto-close", action="store_true")
    p_prog.add_argument("--no-cancel", action="store_true")
    p_prog.add_argument("--percentage", type=int, default=0)

    # Question
    p_q = sub.add_parser("question", parents=[common])
    p_q.add_argument("--ok-label", default="")
    p_q.add_argument("--cancel-label", default="")

    # Error
    sub.add_parser("error", parents=[common])

    # Info
    sub.add_parser("info", parents=[common])

    # List
    p_list = sub.add_parser("list", parents=[common])
    p_list.add_argument("--column", action="append", default=[])
    p_list.add_argument("--row", action="append", default=[])
    p_list.add_argument("--radiolist", action="store_true")
    p_list.add_argument("--hide-column", type=int, default=0)
    p_list.add_argument("--print-column", type=int, default=1)

    return parser


def main():
    global _exit_code, _selected_value

    # Handle SIGINT gracefully
    signal.signal(signal.SIGINT, lambda *_: sys.exit(1))

    Adw.init()

    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "progress": _show_progress,
        "question": _show_question,
        "error": _show_error,
        "info": _show_info,
        "list": _show_list,
    }

    func = dispatch.get(args.dialog_type)
    if not func:
        print(f"Unknown dialog type: {args.dialog_type}", file=sys.stderr)
        sys.exit(1)

    app = DialogApp(func, args)
    app.run([])

    # Print selected value for list dialogs
    if args.dialog_type == "list" and _exit_code == 0 and _selected_value:
        print(_selected_value)

    sys.exit(_exit_code)


if __name__ == "__main__":
    main()
