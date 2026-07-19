from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
LIBRARY = REPOSITORY / "biglinux-livecd/usr/lib/biglinux-livecd"
sys.path.insert(0, str(LIBRARY))

from integrity import (  # noqa: E402
    VerificationStatus,
    acquire_lock,
    clear_state,
    detect_iso_mount,
    state_is_verified,
    verify_iso,
    write_state,
)


def add_checksum_pair(directory: Path, name: str, content: bytes) -> None:
    image = directory / name
    image.write_bytes(content)
    digest = hashlib.md5(content, usedforsecurity=False).hexdigest()
    (directory / name.replace(".sfs", ".md5")).write_text(
        f"{digest}  {name}\n", encoding="ascii"
    )


def test_verify_iso_accepts_matching_expected_files(tmp_path: Path) -> None:
    add_checksum_pair(tmp_path, "rootfs.sfs", b"root filesystem image")
    progress: list[tuple[int, str]] = []
    outcome = verify_iso(
        tmp_path,
        progress=lambda percentage, filename: progress.append((percentage, filename)),
    )
    assert outcome.status is VerificationStatus.SUCCESS
    assert progress == [(80, "rootfs.sfs")]


def test_verify_iso_rejects_missing_or_mismatched_media(tmp_path: Path) -> None:
    assert verify_iso(tmp_path).reason == "no checksum manifests found"

    (tmp_path / "rootfs.sfs").write_bytes(b"image")
    incomplete = verify_iso(tmp_path)
    assert incomplete.status is VerificationStatus.FAILED
    assert incomplete.reason == "incomplete checksum pair: rootfs.sfs"

    (tmp_path / "rootfs.md5").write_text(f"{'0' * 32}  rootfs.sfs\n", encoding="ascii")
    mismatch = verify_iso(tmp_path)
    assert mismatch.status is VerificationStatus.FAILED
    assert mismatch.reason == "checksum mismatch: rootfs.sfs"

    image = tmp_path / "rootfs.sfs"
    manifest = tmp_path / "rootfs.md5"
    image.unlink()
    manifest.unlink()
    add_checksum_pair(tmp_path, "desktopfs.sfs", b"desktop image")
    missing_root = verify_iso(tmp_path)
    assert missing_root.status is VerificationStatus.FAILED
    assert missing_root.reason == "required checksum pair missing: rootfs.sfs"


def test_verify_iso_rejects_manifest_path_or_symlink(tmp_path: Path) -> None:
    image = tmp_path / "rootfs.sfs"
    image.write_bytes(b"image")
    digest = hashlib.md5(b"image", usedforsecurity=False).hexdigest()
    manifest = tmp_path / "rootfs.md5"
    manifest.write_text(f"{digest}  ../../etc/shadow\n", encoding="ascii")
    unexpected = verify_iso(tmp_path)
    assert unexpected.status is VerificationStatus.FAILED
    assert "unexpected file" in unexpected.reason

    manifest.unlink()
    real_manifest = tmp_path / "real.md5"
    real_manifest.write_text(f"{digest}  rootfs.sfs\n", encoding="ascii")
    manifest.symlink_to(real_manifest)
    symlink = verify_iso(tmp_path)
    assert symlink.status is VerificationStatus.FAILED
    assert "Too many levels of symbolic links" in symlink.reason


def test_verify_iso_honors_cancellation_between_chunks(tmp_path: Path) -> None:
    add_checksum_pair(tmp_path, "rootfs.sfs", b"x" * (5 * 1024 * 1024))
    outcome = verify_iso(tmp_path, is_cancelled=lambda: True)
    assert outcome.status is VerificationStatus.CANCELLED


def test_detect_iso_mount_stays_below_live_root(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    image_directory = live_root / "manjaro/x86_64"
    image_directory.mkdir(parents=True)
    (image_directory / "rootfs.sfs").touch()
    assert detect_iso_mount(live_root) == image_directory

    (image_directory / "rootfs.sfs").unlink()
    image_directory.rmdir()
    (live_root / "manjaro").rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x86_64").mkdir()
    (live_root / "escape").symlink_to(outside, target_is_directory=True)
    assert detect_iso_mount(live_root) is None


def test_detect_iso_mount_uses_one_deterministic_priority(tmp_path: Path) -> None:
    live_root = tmp_path / "live"
    (live_root / "zeta/x86_64").mkdir(parents=True)
    (live_root / "alpha/x86_64").mkdir(parents=True)
    (live_root / "zeta/x86_64/rootfs.sfs").touch()
    (live_root / "alpha/x86_64/rootfs.sfs").touch()
    assert detect_iso_mount(live_root) == live_root / "alpha/x86_64"
    (live_root / "manjaro/x86_64").mkdir(parents=True)
    (live_root / "manjaro/x86_64/rootfs.sfs").touch()
    assert detect_iso_mount(live_root) == live_root / "manjaro/x86_64"

    (live_root / 'bad"name/x86_64').mkdir(parents=True)
    (live_root / 'bad"name/x86_64/rootfs.sfs').touch()
    (live_root / "manjaro/x86_64/rootfs.sfs").unlink()
    assert detect_iso_mount(live_root) == live_root / "alpha/x86_64"


def test_integrity_state_is_atomic_exact_and_locked(tmp_path: Path) -> None:
    state_directory = tmp_path / "state"
    state_directory.mkdir()
    write_state("verified", state_directory)
    marker = state_directory / "verified"
    assert state_is_verified(state_directory)
    assert marker.read_text(encoding="ascii") == "verified\n"
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    assert list(state_directory.glob(".verified.*")) == []

    marker.write_text("forged\n", encoding="ascii")
    assert not state_is_verified(state_directory)
    clear_state(state_directory)
    assert not marker.exists()

    first_lock = acquire_lock(state_directory)
    assert first_lock is not None
    assert acquire_lock(state_directory) is None
    os.close(first_lock)
    second_lock = acquire_lock(state_directory)
    assert second_lock is not None
    os.close(second_lock)
