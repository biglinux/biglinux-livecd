from __future__ import annotations

import gettext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "biglinux-livecd"
LOCALE_ROOT = PACKAGE / "usr/share/locale"

INTEGRITY_MESSAGES = (
    "Please wait...",
    "Checking the integrity of the download and storage device...",
    "Checking system integrity",
    "Checking for download or USB drive errors, this may take a few minutes...",
    "Verification progress",
    "Checking the file: {filename}",
    "Verification failed",
    "The live media could not be verified. Download the system again or use another USB drive.",
    "Verification complete",
    "The files are intact.",
    "Verification canceled",
    "The integrity check was not completed.",
)


def test_installed_catalogs_include_integrity_screen_messages() -> None:
    catalogs = sorted(LOCALE_ROOT.glob("*/LC_MESSAGES/biglinux-livecd.mo"))
    assert catalogs
    for catalog_path in catalogs:
        with catalog_path.open("rb") as catalog_file:
            translation = gettext.GNUTranslations(catalog_file)
        missing = [
            message
            for message in INTEGRITY_MESSAGES
            if message not in translation._catalog  # noqa: SLF001
        ]
        assert not missing, f"{catalog_path.parent.parent.name}: {missing}"
