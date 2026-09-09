"""Validate packaged systemd units against their staged executables."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "biglinux-livecd"


def verify_staged_unit(
    tmp_path: Path,
    unit_name: str,
    installed_executable: str,
    staged_executable: str,
) -> None:
    systemd_analyze = shutil.which("systemd-analyze")
    assert systemd_analyze is not None, "systemd-analyze is required"

    executable = PACKAGE / staged_executable
    assert executable.is_file()

    source = PACKAGE / f"usr/lib/systemd/system/{unit_name}"
    staged = tmp_path / unit_name
    staged.write_text(
        source.read_text(encoding="utf-8").replace(
            installed_executable, str(executable)
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [systemd_analyze, "verify", staged],
        check=True,
        capture_output=True,
        text=True,
    )


def test_livecd_tweaks_unit_is_valid_for_staged_payload(tmp_path: Path) -> None:
    executable = PACKAGE / "usr/bin/livecd-tweaks"
    assert executable.stat().st_mode & 0o111
    verify_staged_unit(
        tmp_path,
        "livecd-tweaks.service",
        "/usr/bin/livecd-tweaks",
        "usr/bin/livecd-tweaks",
    )
    unit = (PACKAGE / "usr/lib/systemd/system/livecd-tweaks.service").read_text(
        encoding="utf-8"
    )
    assert "Before=display-manager.service" in unit
    wanted_unit = (
        PACKAGE / "usr/lib/systemd/system/multi-user.target.wants/livecd-tweaks.service"
    )
    assert wanted_unit.is_symlink()
    assert wanted_unit.readlink() == Path("../livecd-tweaks.service")


def test_language_suggestion_unit_is_valid_for_staged_payload(
    tmp_path: Path,
) -> None:
    verify_staged_unit(
        tmp_path,
        "biglinux-language-suggestion.service",
        "/usr/lib/biglinux-livecd/language_suggestion_probe.py",
        "usr/lib/biglinux-livecd/language_suggestion_probe.py",
    )
    unit = (
        PACKAGE / "usr/lib/systemd/system/biglinux-language-suggestion.service"
    ).read_text(encoding="utf-8")
    assert "Before=display-manager.service" not in unit

    wanted_unit = (
        PACKAGE
        / "usr/lib/systemd/system/graphical.target.wants/biglinux-language-suggestion.service"
    )
    assert wanted_unit.is_symlink()
    assert wanted_unit.readlink() == Path("../biglinux-language-suggestion.service")


def test_integrity_check_starts_at_boot_with_the_lowest_priority(
    tmp_path: Path,
) -> None:
    verify_staged_unit(
        tmp_path,
        "biglinux-integrity-check.service",
        "/usr/bin/biglinux-verify-md5sum",
        "usr/bin/biglinux-verify-md5sum",
    )
    preset = (
        PACKAGE / "usr/lib/systemd/system-preset/50-biglinux-livecd.preset"
    ).read_text(encoding="utf-8")
    assert "enable biglinux-integrity-check.service" in preset
    assert "biglinux-integrity-check.path" not in preset
    assert not (
        PACKAGE
        / "usr/lib/systemd/system/graphical.target.wants/biglinux-integrity-check.path"
    ).exists()
    # Started with the session instead of when the installer asks for the
    # result, so the wait dialog only shows up on media slow enough that the
    # check is still running by then.
    wanted_unit = (
        PACKAGE
        / "usr/lib/systemd/system/graphical.target.wants/biglinux-integrity-check.service"
    )
    assert wanted_unit.is_symlink()
    assert wanted_unit.readlink() == Path("../biglinux-integrity-check.service")
    unit = (
        PACKAGE / "usr/lib/systemd/system/biglinux-integrity-check.service"
    ).read_text(encoding="utf-8")
    assert "WantedBy=graphical.target" in unit
    assert "After=local-fs.target graphical.target" in unit
    assert "Before=" not in unit
    assert "Nice=19" in unit
    assert "CPUSchedulingPolicy=idle" in unit
    assert "CPUWeight=1" in unit
    assert "IOSchedulingClass=idle" in unit
    assert "IOSchedulingPriority=7" in unit
    assert "IOWeight=1" in unit
    assert "ConditionPathExists=/livefs-pkgs.txt" in unit
