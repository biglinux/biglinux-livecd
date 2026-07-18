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
import os
import re
import signal
import sys

# allow-noisy-log: stdout is the documented result channel and stderr reports CLI misuse.
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
def _show_progress(app: DialogApp, args):  # noqa: C901 - GTK callback state machine
    global _exit_code

    win = Adw.Window(
        application=app,
        title=args.title or _("Progress"),
        default_width=args.width or 400,
        default_height=140,
    )
    win.set_deletable(False)

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    win.set_content(box)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER)
    label.update_property([Gtk.AccessibleProperty.LABEL], [plain_text])
    box.append(label)

    bar = Gtk.ProgressBar(show_text=False, hexpand=True)
    bar.update_property([Gtk.AccessibleProperty.LABEL], [plain_text])
    box.append(bar)

    win.update_property([Gtk.AccessibleProperty.LABEL], [args.title or _("Progress")])
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


# ── Integrity wait dialog ───────────────────────────────────────────────────
def _show_integrity_wait(app: DialogApp, args):
    global _exit_code

    provider = Gtk.CssProvider()
    provider.load_from_string(
        """
        .integrity-card {
            padding: 30px;
        }
        .integrity-title {
            font-size: 1.35em;
            font-weight: 700;
        }
        .integrity-description {
            opacity: 0.78;
        }
        .integrity-progress trough,
        .integrity-progress progress {
            min-height: 8px;
            border-radius: 999px;
        }
        .integrity-success-ring {
            min-width: 92px;
            min-height: 92px;
            border: 2px solid #35f58a;
            border-radius: 999px;
            box-shadow: 0 0 20px alpha(#35f58a, 0.68),
                        inset 0 0 12px alpha(#35f58a, 0.30);
        }
        .integrity-success-icon {
            color: #35f58a;
            -gtk-icon-shadow: 0 0 12px alpha(#35f58a, 0.90);
        }
        """
    )
    display = Gdk.Display.get_default()
    if display:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    anchor = Gtk.Window(application=app)
    anchor.set_decorated(False)
    anchor.set_focusable(False)
    anchor.set_opacity(0.0)
    anchor.fullscreen()
    anchor.present()

    win = Adw.Window(
        application=app,
        title=args.title or _("Please wait..."),
        default_width=args.width or 480,
        default_height=args.height or 300,
    )
    win.set_transient_for(anchor)
    win.set_deletable(False)
    win.set_modal(True)
    win.set_resizable(False)
    if startup_id := os.environ.get("DESKTOP_STARTUP_ID"):
        win.set_startup_id(startup_id)

    stack = Gtk.Stack(
        transition_type=Gtk.StackTransitionType.CROSSFADE,
        transition_duration=250,
    )
    win.set_content(stack)

    progress_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.CENTER,
    )
    progress_box.add_css_class("integrity-card")

    progress_icon = Gtk.Image.new_from_icon_name("drive-optical-symbolic")
    progress_icon.set_pixel_size(56)
    progress_icon.set_halign(Gtk.Align.CENTER)
    progress_box.append(progress_icon)

    title = Gtk.Label(
        label=strip_pango_markup(args.title or _("Please wait...")),
        halign=Gtk.Align.CENTER,
    )
    title.add_css_class("integrity-title")
    progress_box.append(title)

    description = Gtk.Label(
        label=strip_pango_markup(args.text or ""),
        wrap=True,
        justify=Gtk.Justification.CENTER,
        halign=Gtk.Align.CENTER,
        max_width_chars=52,
    )
    description.add_css_class("integrity-description")
    progress_box.append(description)

    bar = Gtk.ProgressBar(hexpand=True)
    bar.add_css_class("integrity-progress")
    progress_box.append(bar)
    stack.add_named(progress_box, "progress")

    success_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )
    success_box.add_css_class("integrity-card")

    success_ring = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    success_ring.add_css_class("integrity-success-ring")
    success_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
    success_icon.set_pixel_size(58)
    success_icon.set_halign(Gtk.Align.CENTER)
    success_icon.set_valign(Gtk.Align.CENTER)
    success_icon.add_css_class("integrity-success-icon")
    success_ring.append(success_icon)
    success_box.append(success_ring)

    success_title = Gtk.Label(
        label=strip_pango_markup(args.success_title),
        halign=Gtk.Align.CENTER,
    )
    success_title.add_css_class("integrity-title")
    success_box.append(success_title)

    success_description = Gtk.Label(
        label=strip_pango_markup(args.success_text),
        wrap=True,
        justify=Gtk.Justification.CENTER,
        halign=Gtk.Align.CENTER,
    )
    success_description.add_css_class("integrity-description")
    success_box.append(success_description)
    stack.add_named(success_box, "success")
    stack.set_visible_child_name("progress")

    accessible_wait = ". ".join(
        part for part in (title.get_text(), description.get_text()) if part
    )
    win.update_property([Gtk.AccessibleProperty.LABEL], [accessible_wait])
    announce(win, accessible_wait, assertive=True)

    def pulse():
        bar.pulse()
        return True

    pulse_id = GLib.timeout_add(100, pulse)

    def finish_success():
        app.quit()
        return False

    def show_result(status: str):
        global _exit_code
        GLib.source_remove(pulse_id)
        _exit_code = 0
        if status != "verified":
            app.quit()
            return False

        stack.set_visible_child_name("success")
        win.set_title(args.success_title)
        accessible_success = ". ".join(
            part for part in (args.success_title, args.success_text) if part
        )
        win.update_property([Gtk.AccessibleProperty.LABEL], [accessible_success])
        announce(win, accessible_success, assertive=True)
        GLib.timeout_add(args.success_delay, finish_success)
        return False

    def read_status():
        try:
            status = sys.stdin.readline().strip()
        except Exception:
            status = ""
        GLib.idle_add(show_result, status)

    threading.Thread(target=read_status, daemon=True).start()
    win.present()


# ── Question dialog ──────────────────────────────────────────────────────────
def _show_question(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(
        application=app,
        title=args.title or _("Question"),
        default_width=args.width or 500,
        default_height=-1,
    )

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    win.set_content(box)

    icon_name = args.icon_name or "dialog-question"
    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.CENTER)
    box.append(icon)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(
        label=plain_text,
        wrap=True,
        halign=Gtk.Align.CENTER,
        max_width_chars=60,
        use_markup=False,
    )
    label.update_property([Gtk.AccessibleProperty.LABEL], [plain_text])
    box.append(label)

    btn_box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER, margin_top=8)
    box.append(btn_box)

    cancel_label = args.cancel_label or _("Close")
    ok_label = args.ok_label or _("Continue")

    cancel_btn = Gtk.Button(label=cancel_label)
    cancel_btn.add_css_class("pill")
    cancel_btn.update_property([Gtk.AccessibleProperty.LABEL], [cancel_label])
    btn_box.append(cancel_btn)

    ok_btn = Gtk.Button(label=ok_label)
    ok_btn.add_css_class("suggested-action")
    ok_btn.add_css_class("pill")
    ok_btn.update_property([Gtk.AccessibleProperty.LABEL], [ok_label])
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

    win.update_property([Gtk.AccessibleProperty.LABEL], [args.title or _("Question")])
    announce(win, plain_text, assertive=True)
    win.present()
    ok_btn.grab_focus()


# ── Error dialog ─────────────────────────────────────────────────────────────
def _show_error(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(
        application=app,
        title=args.title or _("Error"),
        default_width=args.width or 500,
        default_height=-1,
    )

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    win.set_content(box)

    icon = Gtk.Image.new_from_icon_name("dialog-error")
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.CENTER)
    box.append(icon)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(
        label=plain_text,
        wrap=True,
        halign=Gtk.Align.CENTER,
        max_width_chars=60,
        use_markup=False,
    )
    label.update_property([Gtk.AccessibleProperty.LABEL], [plain_text])
    box.append(label)

    btn = Gtk.Button(label=_("Close"), halign=Gtk.Align.CENTER)
    btn.add_css_class("pill")
    btn.update_property([Gtk.AccessibleProperty.LABEL], [_("Close")])
    btn.connect("clicked", lambda _b: app.quit())
    box.append(btn)

    _exit_code = 0
    win.update_property([Gtk.AccessibleProperty.LABEL], [args.title or _("Error")])
    announce(win, plain_text, assertive=True)
    win.present()
    btn.grab_focus()


# ── Info dialog ──────────────────────────────────────────────────────────────
def _show_info(app: DialogApp, args):
    global _exit_code

    win = Adw.Window(
        application=app,
        title=args.title or _("Information"),
        default_width=args.width or 500,
        default_height=-1,
    )

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    win.set_content(box)

    icon = Gtk.Image.new_from_icon_name("dialog-information")
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.CENTER)
    box.append(icon)

    plain_text = strip_pango_markup(args.text or "")
    label = Gtk.Label(
        label=plain_text,
        wrap=True,
        halign=Gtk.Align.CENTER,
        max_width_chars=60,
        use_markup=False,
    )
    label.update_property([Gtk.AccessibleProperty.LABEL], [plain_text])
    box.append(label)

    btn = Gtk.Button(label=_("Close"), halign=Gtk.Align.CENTER)
    btn.add_css_class("pill")
    btn.update_property([Gtk.AccessibleProperty.LABEL], [_("Close")])
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
def _group_rows(raw_rows, column_count):
    if column_count <= 0:
        return []
    return [
        chunk
        for offset in range(0, len(raw_rows), column_count)
        if len(chunk := raw_rows[offset : offset + column_count]) == column_count
    ]


def _show_list(app: DialogApp, args):  # noqa: C901 - GTK factory and dialog lifecycle
    global _exit_code, _selected_value

    win = Adw.Window(
        application=app,
        title=args.title or _("Select"),
        default_width=args.width or 480,
        default_height=args.height or 350,
    )

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    win.set_content(box)

    plain_text = strip_pango_markup(args.text or "")
    header_label = Gtk.Label(label=plain_text, wrap=True, halign=Gtk.Align.CENTER)
    header_label.update_property([Gtk.AccessibleProperty.LABEL], [plain_text])
    box.append(header_label)

    columns = args.column or []
    num_cols = len(columns)
    rows = _group_rows(args.row or [], num_cols)

    print_col = (args.print_column or 1) - 1  # 0-indexed
    hide_col = (args.hide_column or 0) - 1

    # Radiolist mode with Adw.ActionRows and check marks
    listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    listbox.add_css_class("boxed-list")

    scrolled = Gtk.ScrolledWindow(vexpand=True)
    scrolled.set_child(listbox)
    box.append(scrolled)

    check_group: list[tuple[Adw.ActionRow, Gtk.CheckButton, str]] = []

    for row_data in rows:
        # Determine display text (skip hidden columns)
        display_parts = []
        for ci, cell in enumerate(row_data):
            if ci != hide_col and not (args.radiolist and ci == 0):
                display_parts.append(cell)
        display_text = " — ".join(display_parts) if display_parts else str(row_data)

        value = row_data[print_col] if print_col < len(row_data) else ""

        action_row = Adw.ActionRow(title=display_text)
        action_row.update_property([Gtk.AccessibleProperty.LABEL], [display_text])

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

    for _row_widget, cb, val in check_group:
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

    win.update_property([Gtk.AccessibleProperty.LABEL], [args.title or _("Select")])
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

    # Integrity wait
    p_integrity = sub.add_parser("integrity-wait", parents=[common])
    p_integrity.add_argument("--success-title", required=True)
    p_integrity.add_argument("--success-text", required=True)
    p_integrity.add_argument("--success-delay", type=int, default=1100)

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
        "integrity-wait": _show_integrity_wait,
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
