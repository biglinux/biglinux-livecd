from __future__ import annotations

import ast
import json

LAYOUT_NAMES = (
    "biggnome",
    "desk-ux",
    "hybrid",
    "g-unity",
    "classic",
    "minimal",
)

LAYOUT_DISPLAY_NAMES = {
    "biggnome": "BigGnome",
    "desk-ux": "Desk UX",
    "hybrid": "Hybrid",
    "g-unity": "G-Unity",
    "classic": "Classic",
    "minimal": "Minimal",
}

MONITOR_KEYS = {
    "panel-anchors",
    "panel-element-positions",
    "panel-lengths",
    "panel-positions",
    "panel-sizes",
}

LAYOUT_SWITCHER_HELPER_UUID = "layout-switcher-helper@bigcommunity.org"


def _parse_extension_list(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value.strip())
    except (SyntaxError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [extension for extension in parsed if isinstance(extension, str)]


def normalize_layout_text(text: str) -> str:
    """Keep packaged GNOME layout dumps portable across monitors."""
    output: list[str] = []
    for line in text.splitlines():
        if line.startswith("preferred-monitor-by-connector="):
            output.append("preferred-monitor-by-connector='primary'")
            continue
        if line.startswith("primary-monitor="):
            output.append("primary-monitor=''")
            continue
        if line.startswith("enabled-extensions="):
            extensions = _parse_extension_list(line.partition("=")[2])
            extensions = [
                extension
                for extension in extensions
                if extension != LAYOUT_SWITCHER_HELPER_UUID
            ]
            extensions.insert(0, LAYOUT_SWITCHER_HELPER_UUID)
            output.append(f"enabled-extensions={extensions!r}")
            continue
        if line.startswith("disabled-extensions="):
            extensions = _parse_extension_list(line.partition("=")[2])
            extensions = [
                extension
                for extension in extensions
                if extension != LAYOUT_SWITCHER_HELPER_UUID
            ]
            output.append(f"disabled-extensions={extensions!r}")
            continue
        if "=" not in line:
            output.append(line)
            continue
        key, _, value = line.partition("=")
        if key not in MONITOR_KEYS:
            output.append(line)
            continue
        try:
            per_monitor = json.loads(value.strip().strip("'"))
        except (TypeError, ValueError):
            output.append(line)
            continue
        normalized = {"0": next(iter(per_monitor.values()))} if per_monitor else {}
        serialized = json.dumps(normalized, separators=(",", ":"))
        output.append(f"{key}='{serialized}'")
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(output) + suffix
