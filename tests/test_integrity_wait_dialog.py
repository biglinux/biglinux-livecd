from __future__ import annotations

import importlib.util
from pathlib import Path

import cairo
import pytest

ROOT = Path(__file__).resolve().parents[1]
DIALOG_PATH = ROOT / "biglinux-livecd/usr/share/biglinux/calamares/gtk_dialog.py"


def load_dialog_module():
    spec = importlib.util.spec_from_file_location("gtk_dialog_test", DIALOG_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_integrity_wait_arguments_and_visual_contract() -> None:
    dialog = load_dialog_module()
    args = dialog.build_parser().parse_args(
        [
            "integrity-wait",
            "--title=Please wait...",
            "--text=Checking media",
            "--success-title=Verification complete",
            "--success-text=The files are intact.",
        ]
    )
    assert args.dialog_type == "integrity-wait"
    assert args.success_delay == 1100

    source = DIALOG_PATH.read_text(encoding="utf-8")
    assert "win.set_modal(True)" in source
    assert 'win.add_css_class("integrity-window")' in source
    assert "background-color: alpha(@theme_bg_color, 0.97)" in source
    assert '"integrity-success-ring"' in source
    assert "success_badge = Gtk.DrawingArea(" in source
    assert "success_badge.set_draw_func(_draw_integrity_success_check)" in source
    assert 'status != "verified"' in source


def test_integrity_success_check_is_pixel_centered() -> None:
    dialog = load_dialog_module()
    size = 92
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    context = cairo.Context(surface)

    dialog._draw_integrity_success_check(None, context, size, size)
    surface.flush()

    data = surface.get_data()
    stride = surface.get_stride()
    opaque_pixels = [
        (x, y) for y in range(size) for x in range(size) if data[y * stride + x * 4 + 3]
    ]
    left = min(x for x, _y in opaque_pixels)
    right = max(x for x, _y in opaque_pixels)
    top = min(y for _x, y in opaque_pixels)
    bottom = max(y for _x, y in opaque_pixels)

    assert (left + right) / 2 == pytest.approx(size / 2, abs=0.5)
    assert (top + bottom) / 2 == pytest.approx(size / 2, abs=0.5)
