from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path

MAX_CONFIG_BYTES = 1024 * 1024


def _resolved_parent_within_home(filepath: str) -> tuple[Path, Path]:
    home = Path.home().resolve(strict=True)
    target = Path(filepath)
    if not target.is_absolute():
        raise OSError("user configuration path must be absolute")
    target.parent.mkdir(parents=True, exist_ok=True)
    parent = target.parent.resolve(strict=True)
    if not parent.is_relative_to(home):
        raise OSError("user configuration path escapes the home directory")
    return parent, target


def write_text(filepath: str, content: str) -> None:
    parent, target = _resolved_parent_within_home(filepath)
    temporary_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=parent,
            prefix=f".{target.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, target)
        temporary_path = ""
        directory_descriptor = os.open(
            parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
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


def _read_optional_regular_text(filepath: str) -> str:
    try:
        descriptor = os.open(
            filepath,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
    except FileNotFoundError:
        return ""
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError("user configuration source is not a regular file")
        if file_stat.st_size > MAX_CONFIG_BYTES:
            raise OSError("user configuration exceeds its size limit")
        with os.fdopen(descriptor, "r", encoding="utf-8") as config_file:
            descriptor = -1
            content = config_file.read(MAX_CONFIG_BYTES + 1)
            if len(content.encode("utf-8")) > MAX_CONFIG_BYTES:
                raise OSError("user configuration grew beyond its size limit")
            return content
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def update_ini_text(  # noqa: C901 - single-pass parser preserves comments and ordering
    text: str, section: str, settings: Mapping[str, str]
) -> str:
    output: list[str] = []
    is_target_section = False
    found_section = False
    updated_keys: set[str] = set()

    def append_missing() -> None:
        for key, value in settings.items():
            if key not in updated_keys:
                output.append(f"{key}={value}\n")
                updated_keys.add(key)

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if is_target_section:
                append_missing()
            is_target_section = stripped[1:-1] == section
            found_section = found_section or is_target_section
            output.append(line)
        elif is_target_section and "=" in stripped and not stripped.startswith("#"):
            key = stripped.partition("=")[0].strip()
            if key in settings:
                if key not in updated_keys:
                    output.append(f"{key}={settings[key]}\n")
                    updated_keys.add(key)
                continue
            output.append(line)
        else:
            output.append(line)
    if is_target_section:
        append_missing()
    elif not found_section:
        if output and output[-1].strip():
            output.append("\n")
        output.append(f"[{section}]\n")
        append_missing()
    return "".join(output)


def update_ini_file(filepath: str, section: str, settings: Mapping[str, str]) -> None:
    current = _read_optional_regular_text(filepath)
    write_text(filepath, update_ini_text(current, section, settings))
