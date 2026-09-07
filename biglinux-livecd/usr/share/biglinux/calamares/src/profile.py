"""Read the profile materialized by the live-session launcher."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_profile() -> dict[str, Any]:
    profile_directory = Path(
        os.environ.get("CALAMARES_PROFILE_DIRECTORY", "/etc/calamares")
    )
    profile_file = profile_directory / "profile.json"
    try:
        data = json.loads(profile_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    profile_id = profile_directory.name or "biglinux"
    display_name = data.get("display_name")
    return {
        "id": data.get("id", profile_id),
        "display_name": display_name if isinstance(display_name, str) else profile_id,
    }
