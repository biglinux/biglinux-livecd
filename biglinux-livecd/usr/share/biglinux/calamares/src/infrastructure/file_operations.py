"""File operations used by the installer UI."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_json_file(file_path: str | Path) -> Any:
    try:
        with Path(file_path).open(encoding="utf-8") as source:
            return json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("Could not load JSON %s: %s", file_path, error)
        return None


def ensure_directory(directory: str | Path) -> bool:
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except OSError as error:
        logger.error("Could not create directory %s: %s", directory, error)
        return False


def copy_file_safe(source: str | Path, destination: str | Path) -> bool:
    try:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return True
    except OSError as error:
        logger.error("Could not copy %s to %s: %s", source, destination, error)
        return False


def write_text_file(
    content: str, file_path: str | Path, encoding: str = "utf-8"
) -> bool:
    temporary_path = ""
    file_path = Path(file_path)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            delete=False,
        ) as output:
            temporary_path = output.name
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, file_path)
        temporary_path = ""
        directory = os.open(file_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return True
    except (OSError, UnicodeError) as error:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
        logger.error("Could not write %s: %s", file_path, error)
        return False


def read_text_file(file_path: str | Path, encoding: str = "utf-8") -> str | None:
    try:
        return Path(file_path).read_text(encoding=encoding)
    except (OSError, UnicodeError) as error:
        logger.warning("Could not read %s: %s", file_path, error)
        return None


def validate_package_name(package_name: str) -> bool:
    return bool(
        isinstance(package_name, str)
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9@._+-]*", package_name.strip())
    )
