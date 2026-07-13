from __future__ import annotations

import fcntl
import hashlib
import os
import re
import stat
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import BinaryIO

ISO_ROOT = Path("/run/miso/bootmnt")
STATE_DIRECTORY = Path("/run/biglinux-live/integrity")
CHECKSUM_FILES = (
    ("desktopfs.md5", "desktopfs.sfs", 10),
    ("livefs.md5", "livefs.sfs", 50),
    ("mhwdfs.md5", "mhwdfs.sfs", 60),
    ("rootfs.md5", "rootfs.sfs", 80),
)
REQUIRED_IMAGE = "rootfs.sfs"
_MANIFEST_PATTERN = re.compile(r"^([0-9a-fA-F]{32})[ \t]+\*?([^/\x00]+)$")
_IMAGE_TREE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_MAX_MANIFEST_BYTES = 1024
_READ_CHUNK_BYTES = 4 * 1024 * 1024


class VerificationStatus(Enum):
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class VerificationOutcome:
    status: VerificationStatus
    reason: str


def _is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def _is_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def detect_iso_mount(iso_root: Path = ISO_ROOT) -> Path | None:
    """Return a non-symlink x86_64 image directory below the live mount."""
    if not _is_directory(iso_root):
        return None
    root = iso_root.resolve(strict=True)
    candidates = [root / "manjaro" / "x86_64"]
    candidates.extend(
        entry / "x86_64"
        for entry in sorted(root.iterdir(), key=lambda path: path.name)
        if entry.name not in {"boot", "efi", "manjaro"}
        and _IMAGE_TREE_PATTERN.fullmatch(entry.name)
        and _is_directory(entry)
    )
    for candidate in candidates:
        if not _is_directory(candidate) or not _is_regular_file(
            candidate / REQUIRED_IMAGE
        ):
            continue
        resolved = candidate.resolve(strict=True)
        if resolved.is_relative_to(root):
            return resolved
    return None


def _open_regular(path: Path) -> tuple[int, os.stat_result]:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    file_stat = os.fstat(descriptor)
    if not stat.S_ISREG(file_stat.st_mode):
        os.close(descriptor)
        raise ValueError(f"not a regular file: {path.name}")
    return descriptor, file_stat


def _read_manifest(path: Path, expected_filename: str) -> str:
    descriptor, file_stat = _open_regular(path)
    try:
        if file_stat.st_size > _MAX_MANIFEST_BYTES:
            raise ValueError(f"checksum manifest is too large: {path.name}")
        with os.fdopen(descriptor, "rb") as manifest_file:
            descriptor = -1
            content = manifest_file.read(_MAX_MANIFEST_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        lines = [line for line in content.decode("ascii").splitlines() if line]
    except UnicodeDecodeError as error:
        raise ValueError(f"checksum manifest is not ASCII: {path.name}") from error
    if len(lines) != 1:
        raise ValueError(f"checksum manifest must contain one entry: {path.name}")
    match = _MANIFEST_PATTERN.fullmatch(lines[0])
    if match is None or match.group(2) != expected_filename:
        raise ValueError(f"checksum manifest names an unexpected file: {path.name}")
    return match.group(1).lower()


def _hash_file(
    image_file: BinaryIO,
    is_cancelled: Callable[[], bool],
) -> str | None:
    digest = hashlib.md5(usedforsecurity=False)
    while chunk := image_file.read(_READ_CHUNK_BYTES):
        if is_cancelled():
            return None
        digest.update(chunk)
    return digest.hexdigest()


def verify_iso(
    mount_directory: Path | None = None,
    *,
    is_cancelled: Callable[[], bool] = lambda: False,
    progress: Callable[[int, str], None] = lambda _percent, _filename: None,
) -> VerificationOutcome:
    mount = mount_directory or detect_iso_mount()
    if mount is None:
        return VerificationOutcome(VerificationStatus.FAILED, "live media not found")
    checked_files = 0
    checked_images: set[str] = set()
    for manifest_name, image_name, percentage in CHECKSUM_FILES:
        manifest = mount / manifest_name
        image = mount / image_name
        manifest_exists = manifest.exists() or manifest.is_symlink()
        image_exists = image.exists() or image.is_symlink()
        if not manifest_exists and not image_exists:
            continue
        if not manifest_exists or not image_exists:
            return VerificationOutcome(
                VerificationStatus.FAILED,
                f"incomplete checksum pair: {image_name}",
            )
        progress(percentage, image_name)
        try:
            expected_digest = _read_manifest(manifest, image_name)
            image_descriptor, _image_stat = _open_regular(image)
            with os.fdopen(image_descriptor, "rb") as image_file:
                actual_digest = _hash_file(image_file, is_cancelled)
        except (OSError, ValueError) as error:
            return VerificationOutcome(VerificationStatus.FAILED, str(error))
        if actual_digest is None:
            return VerificationOutcome(
                VerificationStatus.CANCELLED, "verification cancelled"
            )
        if actual_digest != expected_digest:
            return VerificationOutcome(
                VerificationStatus.FAILED,
                f"checksum mismatch: {image_name}",
            )
        checked_files += 1
        checked_images.add(image_name)
    if checked_files == 0:
        return VerificationOutcome(
            VerificationStatus.FAILED,
            "no checksum manifests found",
        )
    if REQUIRED_IMAGE not in checked_images:
        return VerificationOutcome(
            VerificationStatus.FAILED,
            f"required checksum pair missing: {REQUIRED_IMAGE}",
        )
    return VerificationOutcome(VerificationStatus.SUCCESS, "verified")


def _require_state_directory(state_directory: Path) -> None:
    directory_stat = state_directory.lstat()
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise OSError(f"unsafe integrity state directory: {state_directory}")


def clear_state(state_directory: Path = STATE_DIRECTORY) -> None:
    _require_state_directory(state_directory)
    for name in ("verified", "failed"):
        try:
            (state_directory / name).unlink()
        except FileNotFoundError:
            pass


def write_state(name: str, state_directory: Path = STATE_DIRECTORY) -> None:
    if name not in {"verified", "failed"}:
        raise ValueError(f"unsupported integrity state: {name}")
    _require_state_directory(state_directory)
    temporary_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="ascii",
            dir=state_directory,
            prefix=f".{name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(f"{name}\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, state_directory / name)
        temporary_path = ""
        directory_descriptor = os.open(
            state_directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def state_is_verified(state_directory: Path = STATE_DIRECTORY) -> bool:
    marker = state_directory / "verified"
    if not _is_regular_file(marker):
        return False
    try:
        return marker.read_text(encoding="ascii") == "verified\n"
    except (OSError, UnicodeDecodeError):
        return False


def acquire_lock(state_directory: Path = STATE_DIRECTORY) -> int | None:
    _require_state_directory(state_directory)
    descriptor = os.open(
        state_directory / "verification.lock",
        os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor
