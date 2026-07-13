"""Read and apply the boot-time language suggestion."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path

SUGGESTION_PATH = Path("/run/biglinux-language-probe/suggestion.json")
MAX_SUGGESTION_BYTES = 4096
LOCALE_PATTERN = re.compile(r"^[a-z]{2}_[A-Z]{2}$")
SOURCES = {"linux-ext4", "linux-btrfs", "windows-bcd", "geoip"}
FAVORITE_LOCALES = ("en_US", "pt_BR", "es_ES")


def load_suggested_locale(
    supported_locales: set[str], path: Path = SUGGESTION_PATH
) -> str | None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        file_status = os.fstat(descriptor)
        if (
            not stat.S_ISREG(file_status.st_mode)
            or file_status.st_mode & 0o022
            or file_status.st_size > MAX_SUGGESTION_BYTES
        ):
            return None
        content = os.read(descriptor, MAX_SUGGESTION_BYTES + 1)
        if len(content) > MAX_SUGGESTION_BYTES:
            return None
        payload = json.loads(content.decode("utf-8", "strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(payload, dict):
        return None
    locale = payload.get("locale")
    source = payload.get("source")
    if (
        not isinstance(locale, str)
        or not LOCALE_PATTERN.fullmatch(locale)
        or locale not in supported_locales
        or not isinstance(source, str)
        or source not in SOURCES
    ):
        return None
    return locale


def language_sort_key(
    code: str, display_name: str, suggested_locale: str | None
) -> tuple[int, int, str]:
    if code == suggested_locale:
        return 0, 0, ""
    try:
        return 1, FAVORITE_LOCALES.index(code), ""
    except ValueError:
        return 2, 0, display_name.casefold()
