"""The setup wizard has to reach an accessibility bus.

The wizard labels its controls for screen readers, but until this was fixed
none of it reached AT-SPI on a KDE live session, so Orca had nothing to read:

* /etc/xdg/autostart/at-spi-dbus-bus.desktop and orca-autostart.desktop are
  OnlyShowIn=GNOME;Unity;, and the live session exports
  XDG_CURRENT_DESKTOP=KDE, so neither ever runs.
* the Wayland wizard runs on a private session bus (dbus-run-session), while
  org.a11y.Bus.service delegates activation to the user's systemd manager on
  the real bus - so nothing serves org.a11y.Bus where the wizard can see it,
  and GTK disables its bridge for the life of the process.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PACKAGE = REPOSITORY / "biglinux-livecd"
STARTBIGLIVE = PACKAGE / "usr/bin/startbiglive"


def _helpers() -> str:
    source = STARTBIGLIVE.read_text(encoding="utf-8")
    start = source.index("_enable_accessibility() {")
    end = source.index(
        "\n#---------------------------------------"
        "----------------------------------------\n"
        "# Start kwin_wayland",
        start,
    )
    return source[start:end]


def _run(script: str, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(environment)
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=merged,
    )


def test_the_toolkits_are_told_before_the_wizard_starts(tmp_path: Path) -> None:
    log = tmp_path / "settings"

    result = _run(
        f"""
_log() {{ :; }}
gsettings() {{ printf 'gsettings:%s\\n' "$*" >>"$LOG"; }}
{_helpers()}
_enable_accessibility
printf 'GTK_A11Y=%s\\n' "$GTK_A11Y" >>"$LOG"
printf 'QT_ACCESSIBILITY=%s\\n' "$QT_ACCESSIBILITY" >>"$LOG"
printf 'QT_LINUX_ACCESSIBILITY_ALWAYS_ON=%s\\n' \
    "$QT_LINUX_ACCESSIBILITY_ALWAYS_ON" >>"$LOG"
""",
        {"LOG": str(log)},
    )

    assert result.returncode == 0, result.stderr
    settings = log.read_text(encoding="utf-8")
    # GTK4 reads GTK_A11Y once while starting up and never reconsiders.
    assert "GTK_A11Y=atspi" in settings
    assert "QT_ACCESSIBILITY=1" in settings
    assert "QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1" in settings
    assert (
        "gsettings:set org.gnome.desktop.interface toolkit-accessibility true"
        in settings
    )


def test_a_missing_gsettings_does_not_stop_the_session(tmp_path: Path) -> None:
    # Accessibility is worth enabling, never worth failing the boot over.
    result = _run(
        f"""
set -euo pipefail
_log() {{ printf 'log:%s\\n' "$*" >>"$LOG"; }}
gsettings() {{ return 1; }}
{_helpers()}
_enable_accessibility
echo survived
""",
        {"LOG": str(tmp_path / "log")},
    )

    assert result.returncode == 0, result.stderr
    assert "survived" in result.stdout
    assert "Could not enable toolkit-accessibility" in (tmp_path / "log").read_text(
        encoding="utf-8"
    )


def test_the_wizard_bus_serves_the_accessibility_launcher(tmp_path: Path) -> None:
    # The launcher and the compositor have to end up on the same private bus:
    # a launcher on the real bus is exactly the state that left the wizard
    # without an accessibility tree.
    log = tmp_path / "record"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "at-spi-bus-launcher").write_text(
        "#!/bin/bash\n"
        'printf "launcher:%s\\n" "$DBUS_SESSION_BUS_ADDRESS" >>"$RECORD"\n'
        "sleep 5\n",
        encoding="utf-8",
    )
    (binaries / "compositor").write_text(
        "#!/bin/bash\n"
        'printf "compositor:%s\\n" "$DBUS_SESSION_BUS_ADDRESS" >>"$RECORD"\n'
        'printf "args:%s\\n" "$*" >>"$RECORD"\n'
        'printf "forced:%s\\n" "${FORCED_VARIABLE:-unset}" >>"$RECORD"\n',
        encoding="utf-8",
    )
    for binary in binaries.iterdir():
        binary.chmod(0o755)

    result = _run(
        f"""
set -euo pipefail
_log() {{ :; }}
{_helpers()}
# The real helper calls the launcher by absolute path so that D-Bus activation
# cannot hand the job to systemd on the outer bus.
_run_on_wizard_bus() {{
    dbus-run-session -- bash -c '
        at-spi-bus-launcher --launch-immediately &
        exec env "$@"' _ "$@"
}}
_run_on_wizard_bus FORCED_VARIABLE=yes compositor --drm --exit-with-session "wizard"
sleep 1
""",
        {"RECORD": str(log), "PATH": f"{binaries}:{os.environ['PATH']}"},
    )

    assert result.returncode == 0, result.stderr
    record = dict(
        line.split(":", 1) for line in log.read_text(encoding="utf-8").splitlines()
    )
    assert record["launcher"], record
    assert record["launcher"] == record["compositor"], record
    assert record["launcher"] != os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""), record
    assert record["forced"] == "yes", record
    assert "--exit-with-session wizard" in record["args"], record


def test_every_wizard_launch_goes_through_the_accessibility_bus() -> None:
    # Three fallback paths start the compositor (hardware, single GPU, software
    # rendering). A plain dbus-run-session on any of them is a wizard without
    # accessibility on that hardware only, which is the hardest kind to notice.
    source = STARTBIGLIVE.read_text(encoding="utf-8")
    assert "dbus-run-session kwin_wayland" not in source
    assert source.count("_run_on_wizard_bus ") >= 3
