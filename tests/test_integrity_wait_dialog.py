from __future__ import annotations

import importlib.util
from pathlib import Path

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
    assert '"integrity-success-ring"' in source
    assert '"integrity-success-icon"' in source
    assert 'status != "verified"' in source
