from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
LIBRARY = REPOSITORY / "biglinux-livecd/usr/share/biglinux/livecd"
sys.path.insert(0, str(LIBRARY))

from desktop_theme import (  # noqa: E402
    GNOME_DTP_UUID,
    GNOME_KIWI_UUID,
    GNOME_LIGHT_STYLE_UUID,
    GNOME_USER_THEME_UUID,
    _desktop_changes,
    apply_packaged_theme,
    apply_simple_theme,
    update_settings_text,
)
from gnome_layout import normalize_layout_text  # noqa: E402
from user_config import update_ini_file, update_ini_text, write_text  # noqa: E402


class FakeThemeHost:
    def __init__(self, theme_list_script: Path) -> None:
        self.test_mode = False
        self.theme_list_script = str(theme_list_script)
        self.theme_apply_script = "/usr/bin/apply-theme"
        self.theme_state_file = "/run/biglinux-live/desktop-theme"
        self.commands: list[list[str]] = []
        self.states: list[tuple[str, str]] = []
        self.gtk_settings: list[tuple[bool, str]] = []

    def _run_command(
        self,
        command: list[str],
        *,
        as_root: bool = False,
        read_only: bool = False,
        wait_for_completion: bool = False,
    ) -> tuple[bool, str]:
        del as_root, wait_for_completion
        self.commands.append(command)
        if read_only:
            return True, "breeze\nnight\n"
        return True, ""

    def _write_live_state_file(self, filepath: str, content: str) -> bool:
        self.states.append((filepath, content))
        return True

    def _write_user_config_file(self, filepath: str, content: str) -> bool:
        write_text(filepath, content)
        return True

    def _apply_gtk_settings_ini(self, dark: bool, icon_theme: str) -> None:
        self.gtk_settings.append((dark, icon_theme))

    def get_desktop_environment(self) -> str:
        return "XFCE"

    def _ensure_gnome_settings_file(self) -> None:
        raise AssertionError("GNOME setup must not run for XFCE")

    def _sync_gnome_settings_tmp(self) -> None:
        raise AssertionError("GNOME sync must not run for XFCE")

    def _stamp_gnome_input_sources(self, settings_file: str) -> None:
        raise AssertionError(
            f"GNOME input sources must not run for XFCE: {settings_file}"
        )


def test_settings_text_updates_keys_once_and_preserves_other_sections() -> None:
    original = "[one]\nkey=old\nkey=duplicate\nkeep=yes\n\n[two]\nvalue=2\n"
    updated = update_settings_text(
        original,
        {"one": {"key": "new", "added": "value"}, "three": {"last": "3"}},
    )
    assert updated.count("key=new") == 1
    assert "key=duplicate" not in updated
    assert "keep=yes" in updated
    assert "[two]\nvalue=2" in updated
    assert updated.endswith("[three]\nlast=3\n")


def test_packaged_theme_is_allowlisted_before_execution(tmp_path: Path) -> None:
    theme_list = tmp_path / "list-themes"
    theme_list.write_text("fixture", encoding="utf-8")
    host = FakeThemeHost(theme_list)
    assert not apply_packaged_theme(host, "../../evil")
    assert host.states == []
    assert host.commands == [[str(theme_list)]]

    assert apply_packaged_theme(host, "night")
    assert host.states == [(host.theme_state_file, "night")]
    assert host.commands[-1] == [host.theme_apply_script, "night"]


def test_simple_theme_rejects_unknown_value_and_applies_xfce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    theme_list = tmp_path / "list-themes"
    theme_list.write_text("fixture", encoding="utf-8")
    settings = tmp_path / ".config/dconf/settings.xfce"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        "[org/gnome/desktop/interface]\ncolor-scheme='default'\n",
        encoding="utf-8",
    )
    host = FakeThemeHost(theme_list)
    assert not apply_simple_theme(host, "sepia")
    assert apply_simple_theme(host, "dark")
    assert "color-scheme='prefer-dark'" in settings.read_text(encoding="utf-8")
    assert host.gtk_settings == [(True, "bigicons-papient-dark")]
    assert any(command[0] == "xfconf-query" for command in host.commands)


def test_user_config_writes_atomically_inside_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    target = home / ".config/app/settings.ini"
    write_text(str(target), "value\n")
    assert target.read_text(encoding="utf-8") == "value\n"
    assert list(target.parent.glob(".settings.ini.*")) == []

    outside = tmp_path / "outside"
    outside.mkdir()
    link = home / ".config/escape"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError, match="escapes"):
        write_text(str(link / "state"), "unsafe")


def test_ini_update_handles_missing_file_and_rejects_fifo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".config/gtk-4.0/settings.ini"
    update_ini_file(str(target), "Settings", {"theme": "dark"})
    assert target.read_text(encoding="utf-8") == "[Settings]\ntheme=dark\n"
    assert (
        update_ini_text(
            "[Settings]\ntheme=light\ntheme=duplicate\n",
            "Settings",
            {"theme": "dark"},
        )
        == "[Settings]\ntheme=dark\n"
    )

    fifo = tmp_path / ".config/fifo"
    os.mkfifo(fifo)
    with pytest.raises(OSError, match="regular file"):
        update_ini_file(str(fifo), "Settings", {"theme": "dark"})


def test_gnome_layout_normalization_is_monitor_independent() -> None:
    source = (
        "preferred-monitor-by-connector='HDMI-1'\n"
        "primary-monitor='HDMI-1'\n"
        'panel-sizes=\'{"HDMI-1":48,"DP-1":32}\'\n'
        "enabled-extensions=['dash-to-dock@micxgx.gmail.com']\n"
        "unrelated='kept'\n"
    )
    normalized = normalize_layout_text(source)
    assert "preferred-monitor-by-connector='primary'" in normalized
    assert "primary-monitor=''" in normalized
    assert "panel-sizes='{\"0\":48}'" in normalized
    assert normalized.count("layout-switcher-helper@bigcommunity.org") == 1
    assert "unrelated='kept'" in normalized


@pytest.mark.parametrize(
    ("extensions", "expected_enabled", "has_user_theme"),
    [
        (["dash-to-dock@micxgx.gmail.com"], GNOME_USER_THEME_UUID, True),
        ([GNOME_DTP_UUID], GNOME_LIGHT_STYLE_UUID, True),
        ([GNOME_KIWI_UUID], "", False),
    ],
)
def test_gnome_light_theme_respects_layout_shell_contract(
    tmp_path: Path,
    extensions: list[str],
    expected_enabled: str,
    has_user_theme: bool,
) -> None:
    settings = tmp_path / "settings.gnome"
    settings.write_text(
        "[org/gnome/shell]\n"
        f"enabled-extensions={extensions!r}\n"
        "disabled-extensions=[]\n",
        encoding="utf-8",
    )
    changes = _desktop_changes("GNOME", str(settings), dark=False)
    shell_changes = changes.get("org/gnome/shell", {})
    if expected_enabled:
        assert expected_enabled in shell_changes["enabled-extensions"]
    else:
        assert shell_changes == {}
    assert ("org/gnome/shell/extensions/user-theme" in changes) is has_user_theme
