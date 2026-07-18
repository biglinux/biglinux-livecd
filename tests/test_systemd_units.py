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


def test_language_suggestion_unit_is_valid_for_staged_payload(
    tmp_path: Path,
) -> None:
    verify_staged_unit(
        tmp_path,
        "biglinux-language-suggestion.service",
        "/usr/lib/biglinux-livecd/language_suggestion_probe.py",
        "usr/lib/biglinux-livecd/language_suggestion_probe.py",
    )


def test_integrity_check_unit_is_valid_and_enabled(tmp_path: Path) -> None:
    verify_staged_unit(
        tmp_path,
        "biglinux-integrity-check.service",
        "/usr/bin/biglinux-verify-md5sum",
        "usr/bin/biglinux-verify-md5sum",
    )
    preset = PACKAGE / "usr/lib/systemd/system-preset/50-biglinux-livecd.preset"
    assert (
        "enable biglinux-integrity-check.service"
        in preset.read_text(encoding="utf-8").splitlines()
    )
    wanted_unit = (
        PACKAGE
        / "usr/lib/systemd/system/graphical.target.wants/biglinux-integrity-check.service"
    )
    assert wanted_unit.is_symlink()
    assert wanted_unit.readlink() == Path("../biglinux-integrity-check.service")
