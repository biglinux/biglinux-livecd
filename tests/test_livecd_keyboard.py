from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PACKAGE = REPOSITORY / "biglinux-livecd"
LIVECD_SRC = PACKAGE / "usr/share/biglinux/livecd"
STARTBIGLIVE = PACKAGE / "usr/bin/startbiglive"
sys.path.insert(0, str(LIVECD_SRC))

from services import SystemService  # noqa: E402


def run_bash(
    script: str, *, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    merged_environment = os.environ.copy()
    merged_environment.update(environment)
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=merged_environment,
    )


def test_wizard_writes_complete_plasma_keyboard_config(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    service = SystemService()
    commands: list[tuple[list[str], dict[str, object]]] = []
    state: dict[str, str] = {}

    def record_live_state(filepath: str, content: str) -> bool:
        state[filepath] = content
        return True

    monkeypatch.setattr(service, "get_desktop_environment", lambda: "other")
    monkeypatch.setattr(service, "_write_live_state_file", record_live_state)
    monkeypatch.setattr(
        service,
        "_run_command",
        lambda command, **kwargs: commands.append((command.copy(), kwargs))
        or (True, ""),
    )

    service.apply_keyboard_layout("us(intl)")

    kxkbrc = (tmp_path / ".config/kxkbrc").read_text(encoding="utf-8")
    assert state["/tmp/big_keyboard"] == "us(intl)"
    assert "LayoutList=us\n" in kxkbrc
    assert "VariantList=intl\n" in kxkbrc
    assert "Use=true\n" in kxkbrc
    assert commands[1][0] == [
        "localectl",
        "set-x11-keymap",
        "us",
        "pc105",
        "intl",
        "terminate:ctrl_alt_bksp",
    ]


def test_startbiglive_applies_saved_keyboard_layout(tmp_path: Path) -> None:
    source = STARTBIGLIVE.read_text(encoding="utf-8")
    helpers_start = source.index("_valid_xkb_layout() {")
    helpers_end = source.index(
        "\n#-------------------------------------------------------------------------------\n# Anti-loop",
        helpers_start,
    )
    helpers = source[helpers_start:helpers_end]
    block_start = source.index(
        "#-------------------------------------------------------------------------------\n# Apply keyboard layout"
    )
    block_end = source.index(
        "\n#-------------------------------------------------------------------------------\n# Create user directories", block_start
    )
    block = source[block_start:block_end]
    state_file = tmp_path / "big_keyboard"
    command_log = tmp_path / "commands"
    home = tmp_path / "home"
    home.mkdir()
    state_file.write_text("us(intl)", encoding="utf-8")

    result = run_bash(
        f"""
_log() {{ :; }}
live_state_path() {{ printf '%s\\n' "$STATE_FILE"; }}
setxkbmap() {{ printf 'setxkbmap:%s\\n' "$*" >>"$COMMAND_LOG"; }}
sudo() {{ printf 'sudo:%s\\n' "$*" >>"$COMMAND_LOG"; }}
{helpers}
{block}
""",
        environment={
            "STATE_FILE": str(state_file),
            "COMMAND_LOG": str(command_log),
            "HOME": str(home),
        },
    )

    assert result.returncode == 0, result.stderr
    kxkbrc = (home / ".config/kxkbrc").read_text(encoding="utf-8")
    commands = command_log.read_text(encoding="utf-8")
    assert "setxkbmap:us -variant intl\n" in commands
    assert (
        "sudo:-n localectl set-x11-keymap us pc105 intl terminate:ctrl_alt_bksp\n"
        in commands
    )
    assert "LayoutList=us\n" in kxkbrc
    assert "VariantList=intl\n" in kxkbrc
