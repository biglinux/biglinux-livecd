from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
LIBRARY = REPOSITORY / "biglinux-livecd/usr/share/biglinux/livecd"
sys.path.insert(0, str(LIBRARY))

import services  # noqa: E402


def _catalog() -> str:
    return json.dumps(
        [
            {"id": "biggnome", "display_name": "BigGnome"},
            {"id": "g-unity", "display_name": "G-Unity"},
        ]
    )


def test_gnome_layout_uses_layout_switcher_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = services.SystemService()
    service.gnome_app_settings_file = str(
        tmp_path / ".config/big-appearance/settings.json"
    )
    service.desktop_state_file = str(tmp_path / "big_desktop_changed")
    service.gnome_layout_state_file = str(tmp_path / "big_gnome_layout")
    service.gnome_settings_state_file = str(tmp_path / "big_gnome_settings")
    service.gnome_app_settings_state_file = str(tmp_path / "big_gnome_app_settings")
    settings_file = tmp_path / ".config/dconf/settings.gnome"
    monkeypatch.setattr(
        services, "settings_file_path", lambda desktop: str(settings_file)
    )

    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[-1] == "--catalog":
            return True, _catalog()
        return True, json.dumps(
            {
                "layout": "biggnome",
                "display_name": "BigGnome",
                "settings_gnome": "[org/gnome/shell]\nenabled-extensions=['layout-switcher-helper@communitybig.org']\n",
                "app_settings": {"active_layout": "BigGnome"},
            }
        )

    monkeypatch.setattr(service, "_run_command", run)
    service.apply_gnome_desktop_layout("biggnome")

    assert settings_file.read_text(encoding="utf-8").startswith("[org/gnome/shell]")
    app_settings = json.loads(
        Path(service.gnome_app_settings_file).read_text(encoding="utf-8")
    )
    assert app_settings == {"active_layout": "BigGnome"}
    assert calls[0][0] == [service.gnome_layout_exporter, "--catalog"]
    assert calls[1][0] == [
        service.gnome_layout_exporter,
        "biggnome",
        "--manifest",
    ]


def test_invalid_export_does_not_replace_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = services.SystemService()
    service.gnome_app_settings_file = str(
        tmp_path / ".config/big-appearance/settings.json"
    )
    settings_file = tmp_path / ".config/dconf/settings.gnome"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text("original\n", encoding="utf-8")
    monkeypatch.setattr(
        services, "settings_file_path", lambda desktop: str(settings_file)
    )

    responses = iter([(True, _catalog()), (True, "{}")])
    monkeypatch.setattr(
        service, "_run_command", lambda command, **kwargs: next(responses)
    )
    service.apply_gnome_desktop_layout("biggnome")

    assert settings_file.read_text(encoding="utf-8") == "original\n"
