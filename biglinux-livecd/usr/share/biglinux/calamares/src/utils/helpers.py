"""
Helper functions and utilities for BigLinux Calamares Configuration Tool
"""

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


logger = logging.getLogger(__name__)


def load_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load and parse a JSON file safely

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary with parsed JSON data or None if failed
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"JSON file not found: {file_path}")
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.debug(f"Successfully loaded JSON file: {file_path}")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return None

    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        return None


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
    """
    Save data to a JSON file safely

    Args:
        data: Dictionary to save as JSON
        file_path: Path where to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)

        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=file_path.parent, delete=False
        ) as temp_file:
            json.dump(data, temp_file, indent=2, ensure_ascii=False)
            temp_path = temp_file.name

        # Move temp file to final location
        shutil.move(temp_path, file_path)

        logger.debug(f"Successfully saved JSON file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        return False


def ensure_directory(directory: Union[str, Path]) -> bool:
    """
    Ensure a directory exists, create if necessary

    Args:
        directory: Path to the directory

    Returns:
        True if directory exists or was created successfully
    """
    try:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return True

    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        return False


def file_exists(file_path: Union[str, Path]) -> bool:
    """
    Check if a file exists and is readable

    Args:
        file_path: Path to the file

    Returns:
        True if file exists and is readable
    """
    try:
        file_path = Path(file_path)
        return (
            file_path.exists() and file_path.is_file() and os.access(file_path, os.R_OK)
        )

    except Exception:
        return False


def copy_file_safe(source: Union[str, Path], destination: Union[str, Path]) -> bool:
    """
    Copy a file safely with error handling

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        True if copy was successful
    """
    try:
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            logger.error(f"Source file does not exist: {source}")
            return False

        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source, destination)
        logger.debug(f"Successfully copied {source} to {destination}")
        return True

    except Exception as e:
        logger.error(f"Failed to copy {source} to {destination}: {e}")
        return False


def write_text_file(
    content: str, file_path: Union[str, Path], encoding: str = "utf-8"
) -> bool:
    """
    Write text content to a file safely

    Args:
        content: Text content to write
        file_path: Path where to save the file
        encoding: File encoding (default: utf-8)

    Returns:
        True if successful
    """
    try:
        file_path = Path(file_path)

        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)

        logger.debug(f"Successfully wrote text file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to write text file {file_path}: {e}")
        return False


def read_text_file(
    file_path: Union[str, Path], encoding: str = "utf-8"
) -> Optional[str]:
    """
    Read text content from a file safely

    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        File content as string or None if failed
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"Text file not found: {file_path}")
            return None

        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        logger.debug(f"Successfully read text file: {file_path}")
        return content

    except Exception as e:
        logger.error(f"Failed to read text file {file_path}: {e}")
        return None


def parse_package_list(text: str) -> List[str]:
    """
    Parse a package list from text (space or newline separated)

    Args:
        text: Text containing package names

    Returns:
        List of package names
    """
    if not text:
        return []

    # Split by both spaces and newlines, filter empty strings
    packages = []
    for line in text.split("\n"):
        for pkg in line.split():
            pkg = pkg.strip()
            if pkg:
                packages.append(pkg)

    return packages


def format_package_list(packages: List[str], separator: str = "\n") -> str:
    """
    Format a list of packages as text

    Args:
        packages: List of package names
        separator: Separator between packages (default: newline)

    Returns:
        Formatted package list as string
    """
    return separator.join(packages)


def human_readable_size(size_bytes: int) -> str:
    """
    Convert bytes to human readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Human readable size string
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def cleanup_temp_files(file_paths: List[Union[str, Path]]) -> None:
    """
    Clean up temporary files safely

    Args:
        file_paths: List of file paths to remove
    """
    for file_path in file_paths:
        try:
            file_path = Path(file_path)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temp file: {file_path}")

        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


def validate_package_name(package_name: str) -> bool:
    """
    Validate if a package name is valid

    Args:
        package_name: Package name to validate

    Returns:
        True if package name is valid
    """
    if not package_name or not isinstance(package_name, str):
        return False

    # Basic validation: alphanumeric, dashes, dots, underscores
    import re

    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9\-\._]*$"
    return bool(re.match(pattern, package_name.strip()))


def get_file_modification_time(file_path: Union[str, Path]) -> Optional[float]:
    """
    Get file modification time

    Args:
        file_path: Path to the file

    Returns:
        Modification time as timestamp or None if failed
    """
    try:
        file_path = Path(file_path)
        if file_path.exists():
            return file_path.stat().st_mtime
        return None

    except Exception as e:
        logger.error(f"Failed to get modification time for {file_path}: {e}")
        return None


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to specified length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
