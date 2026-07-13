#!/usr/bin/env python3
"""Detect a likely language for the BigLinux live-session wizard."""

from __future__ import annotations

import json
import os
import queue
import re
import stat
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from babel.core import get_global  # pyright: ignore[reportMissingImports]

SUPPORTED_LOCALES_PATH = Path("/usr/share/biglinux/livecd/assets/localization.json")
WORK_DIRECTORY = Path("/run/biglinux-language-probe")
RESULT_PATH = WORK_DIRECTORY / "suggestion.json"
LIVE_MOUNT = "/run/miso/bootmnt"
GEOIP_URL = "https://geoip.kde.org/v1/ubiquity"
EFI_PARTITION_TYPES = {
    "0xef",
    "c12a7328-f81f-11d2-ba4b-00a0c93ec93b",
}
LOCALE_PATTERN = re.compile(r"^[a-z]{2}_[A-Z]{2}$")
WINDOWS_LOCALE_PATTERN = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
COUNTRY_CODE_XML_PATTERN = re.compile(
    r"<(?:[A-Za-z_][\w.-]*:)?CountryCode(?:\s[^>]*)?>"
    r"\s*([A-Za-z]{2})\s*"
    r"</(?:[A-Za-z_][\w.-]*:)?CountryCode\s*>",
    re.IGNORECASE,
)
MAX_TEXT_BYTES = 4096


@dataclass(frozen=True)
class LanguageSuggestion:
    locale: str
    source: str


@dataclass(frozen=True)
class StorageInventory:
    linux_filesystems: tuple[tuple[str, str], ...]
    efi_partitions: tuple[str, ...]


def remaining_seconds(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def run_text_command(argv: list[str], deadline: float) -> str | None:
    timeout = remaining_seconds(deadline)
    if timeout <= 0:
        return None
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def normalize_locale(value: str) -> str | None:
    candidate = value.strip().strip("\"'").split(".", 1)[0].replace("-", "_")
    return candidate if LOCALE_PATTERN.fullmatch(candidate) else None


def parse_locale_configuration(content: str) -> str | None:
    assignments: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name in {"LANG", "LC_MESSAGES"}:
            assignments[name] = value
    for name in ("LANG", "LC_MESSAGES"):
        if locale := normalize_locale(assignments.get(name, "")):
            return locale
    return None


def parse_windows_bcd_locales(output: str, supported: set[str]) -> str | None:
    matches: list[str] = []
    for line in output.splitlines():
        tag = line.strip()
        if not WINDOWS_LOCALE_PATTERN.fullmatch(tag):
            continue
        locale = tag.replace("-", "_")
        if locale in supported and locale not in matches:
            matches.append(locale)
    non_english = [locale for locale in matches if locale != "en_US"]
    if non_english:
        return non_english[0]
    return "en_US" if "en_US" in matches else None


def locale_for_country(country: str, supported_order: tuple[str, ...]) -> str | None:
    if not COUNTRY_PATTERN.fullmatch(country):
        return None
    languages = get_global("territory_languages").get(country, {})
    if not languages:
        return None

    def language_rank(entry: tuple[str, dict[str, object]]) -> tuple[int, float]:
        details = entry[1]
        raw_status = details.get("official_status")
        status = raw_status if isinstance(raw_status, str) else None
        if status in {"official", "de_facto_official"}:
            official_rank = 3
        elif status == "official_regional":
            official_rank = 2
        else:
            official_rank = 1
        raw_population = details.get("population_percent")
        population = (
            float(raw_population) if isinstance(raw_population, (int, float)) else 0.0
        )
        return official_rank, population

    language, _details = max(languages.items(), key=language_rank)
    language = language.split("_", 1)[0]
    exact_locale = f"{language}_{country}"
    if exact_locale in supported_order:
        return exact_locale
    return next(
        (locale for locale in supported_order if locale.startswith(f"{language}_")),
        None,
    )


def parse_geoip_country(xml_text: str) -> str | None:
    if len(xml_text.encode("utf-8")) > MAX_TEXT_BYTES:
        return None
    match = COUNTRY_CODE_XML_PATTERN.search(xml_text)
    if match is None:
        return None
    country = match.group(1).upper()
    return country if COUNTRY_PATTERN.fullmatch(country) else None


def load_supported_locales(path: Path = SUPPORTED_LOCALES_PATH) -> tuple[str, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    locales = []
    for entry in payload if isinstance(payload, list) else []:
        code = entry.get("code") if isinstance(entry, dict) else None
        if isinstance(code, str) and LOCALE_PATTERN.fullmatch(code):
            locales.append(code)
    return tuple(dict.fromkeys(locales))


def flatten_devices(devices: list[object]) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    for raw_device in devices:
        if not isinstance(raw_device, dict):
            continue
        device = raw_device
        flattened.append(device)
        children = device.get("children", [])
        if isinstance(children, list):
            flattened.extend(flatten_devices(children))
    return flattened


def parse_storage_inventory(output: str, live_path: str) -> StorageInventory | None:
    try:
        roots = json.loads(output).get("blockdevices", [])
    except (AttributeError, json.JSONDecodeError):
        return None
    if not isinstance(roots, list):
        return None

    linux_filesystems: list[tuple[str, str]] = []
    efi_partitions: list[str] = []
    for raw_root in roots:
        tree = flatten_devices([raw_root])
        tree_paths = {
            os.path.realpath(path)
            for device in tree
            if isinstance((path := device.get("path")), str)
            and path.startswith("/dev/")
        }
        if live_path in tree_paths:
            continue
        for device in tree:
            path = device.get("path")
            if not isinstance(path, str) or not path.startswith("/dev/"):
                continue
            device_type = device.get("type")
            filesystem = str(device.get("fstype") or "").lower()
            if device_type in {"part", "lvm"} and filesystem in {"ext4", "btrfs"}:
                linux_filesystems.append((path, filesystem))
            partition_type = str(device.get("parttype") or "").lower()
            if device_type == "part" and partition_type in EFI_PARTITION_TYPES:
                efi_partitions.append(path)
    return StorageInventory(
        linux_filesystems=tuple(sorted(set(linux_filesystems))),
        efi_partitions=tuple(sorted(set(efi_partitions))),
    )


def storage_inventory(deadline: float) -> StorageInventory | None:
    live_source = run_text_command(
        [
            "/usr/bin/findmnt",
            "--noheadings",
            "--raw",
            "--output",
            "SOURCE",
            "--target",
            LIVE_MOUNT,
        ],
        deadline,
    )
    if not live_source or not live_source.strip().startswith("/dev/"):
        return None
    output = run_text_command(
        [
            "/usr/bin/lsblk",
            "--json",
            "--paths",
            "--output",
            "PATH,TYPE,FSTYPE,PARTTYPE,MOUNTPOINTS",
        ],
        deadline,
    )
    if not output:
        return None
    return parse_storage_inventory(output, os.path.realpath(live_source.strip()))


def is_block_device(path: str) -> bool:
    try:
        return stat.S_ISBLK(os.stat(path, follow_symlinks=True).st_mode)
    except OSError:
        return False


def read_bounded_file_beneath(directory: Path, relative: tuple[str, ...]) -> str | None:
    descriptors: list[int] = []
    try:
        descriptor = os.open(directory, os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
        descriptors.append(descriptor)
        for component in relative[:-1]:
            descriptor = os.open(
                component,
                os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            descriptors.append(descriptor)
        file_descriptor = os.open(
            relative[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=descriptor,
        )
        descriptors.append(file_descriptor)
        file_status = os.fstat(file_descriptor)
        if (
            not stat.S_ISREG(file_status.st_mode)
            or file_status.st_size > MAX_TEXT_BYTES
        ):
            return None
        return os.read(file_descriptor, MAX_TEXT_BYTES + 1).decode("utf-8", "strict")
    except (OSError, UnicodeDecodeError):
        return None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def read_linux_locale(
    device: str, filesystem: str, mount_index: int, deadline: float
) -> str | None:
    if not is_block_device(device):
        return None
    if filesystem == "ext4":
        content = run_text_command(
            ["/usr/bin/debugfs", "-R", "cat /etc/locale.conf", device], deadline
        )
        return parse_locale_configuration(content or "")
    if filesystem != "btrfs":
        return None

    mountpoint = WORK_DIRECTORY / f"btrfs-{mount_index}"
    try:
        mountpoint.mkdir(mode=0o700, exist_ok=False)
    except OSError:
        return None
    mounted = False
    try:
        mounted = (
            run_text_command(
                [
                    "/usr/bin/mount",
                    "-t",
                    "btrfs",
                    "-o",
                    "ro,rescue=nologreplay,subvol=@",
                    "--",
                    device,
                    str(mountpoint),
                ],
                deadline,
            )
            is not None
        )
        if not mounted:
            return None
        content = read_bounded_file_beneath(mountpoint, ("etc", "locale.conf"))
        return parse_locale_configuration(content or "")
    finally:
        if mounted:
            run_text_command(["/usr/bin/umount", "--", str(mountpoint)], deadline)
        try:
            mountpoint.rmdir()
        except OSError:
            pass


def detect_linux(
    supported: set[str], inventory: StorageInventory, deadline: float
) -> LanguageSuggestion | None:
    detected: list[LanguageSuggestion] = []
    for index, (device, filesystem) in enumerate(inventory.linux_filesystems):
        if remaining_seconds(deadline) <= 0:
            break
        locale = read_linux_locale(device, filesystem, index, deadline)
        if locale in supported:
            detected.append(LanguageSuggestion(locale, f"linux-{filesystem}"))
    languages = {entry.locale.split("_", 1)[0] for entry in detected}
    return detected[0] if len(languages) == 1 else None


def detect_windows(
    supported: set[str], inventory: StorageInventory, deadline: float
) -> LanguageSuggestion | None:
    for index, device in enumerate(inventory.efi_partitions):
        if remaining_seconds(deadline) <= 0:
            break
        if not is_block_device(device):
            continue
        bcd_path = WORK_DIRECTORY / f"windows-{index}.bcd"
        try:
            bcd_path.unlink(missing_ok=True)
            copied = run_text_command(
                [
                    "/usr/bin/mcopy",
                    "-n",
                    "-i",
                    device,
                    "::/EFI/Microsoft/Boot/BCD",
                    str(bcd_path),
                ],
                deadline,
            )
            if copied is None or not bcd_path.is_file():
                continue
            strings = run_text_command(
                ["/usr/bin/strings", "-el", str(bcd_path)], deadline
            )
            if locale := parse_windows_bcd_locales(strings or "", supported):
                return LanguageSuggestion(locale, "windows-bcd")
        finally:
            bcd_path.unlink(missing_ok=True)
    return None


def detect_geoip(
    supported_order: tuple[str, ...], deadline: float
) -> LanguageSuggestion | None:
    response = run_text_command(
        [
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--connect-timeout",
            "1",
            "--max-time",
            f"{remaining_seconds(deadline):.3f}",
            "--max-filesize",
            "65536",
            GEOIP_URL,
        ],
        deadline,
    )
    country = parse_geoip_country(response or "")
    locale = locale_for_country(country or "", supported_order)
    return LanguageSuggestion(locale, "geoip") if locale else None


Probe = Callable[[float], LanguageSuggestion | None]


def choose_suggestion(
    linux_probe: Probe,
    windows_probe: Probe,
    geoip_probe: Probe,
    *,
    total_seconds: float = 2.4,
    linux_seconds: float = 1.4,
) -> LanguageSuggestion | None:
    started = time.monotonic()
    total_deadline = started + total_seconds
    geoip_results: queue.Queue[LanguageSuggestion | None] = queue.Queue(maxsize=1)

    def query_geoip() -> None:
        geoip_results.put(geoip_probe(total_deadline))

    threading.Thread(target=query_geoip, daemon=True).start()
    linux_result = linux_probe(min(total_deadline, started + linux_seconds))
    if linux_result:
        return linux_result
    if windows_result := windows_probe(total_deadline):
        return windows_result
    try:
        return geoip_results.get(timeout=remaining_seconds(total_deadline))
    except queue.Empty:
        return None


def publish_suggestion(suggestion: LanguageSuggestion) -> None:
    WORK_DIRECTORY.mkdir(mode=0o755, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".suggestion-", dir=WORK_DIRECTORY
    )
    temporary_path = Path(temporary_name)
    try:
        payload = json.dumps(
            {"locale": suggestion.locale, "source": suggestion.source},
            separators=(",", ":"),
        ).encode("utf-8")
        os.write(descriptor, payload)
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o644)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary_path, RESULT_PATH)
        directory_descriptor = os.open(WORK_DIRECTORY, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    RESULT_PATH.unlink(missing_ok=True)
    supported_order = load_supported_locales()
    if not supported_order:
        return 0
    supported = set(supported_order)
    inventory = StorageInventory((), ())

    def query_linux(deadline: float) -> LanguageSuggestion | None:
        nonlocal inventory
        inventory = storage_inventory(deadline) or StorageInventory((), ())
        return detect_linux(supported, inventory, deadline)

    suggestion = choose_suggestion(
        query_linux,
        lambda deadline: detect_windows(supported, inventory, deadline),
        lambda deadline: detect_geoip(supported_order, deadline),
    )
    if suggestion:
        publish_suggestion(suggestion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
