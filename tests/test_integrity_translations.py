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

INSTALLER_FAILURE_MESSAGES = (
    "Installation failed",
    "The installation failed. The local error log was saved in your home folder.",
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


def test_installed_catalogs_include_installer_failure_messages() -> None:
    catalogs = sorted(LOCALE_ROOT.glob("*/LC_MESSAGES/biglinux-livecd.mo"))
    assert catalogs
    for catalog_path in catalogs:
        with catalog_path.open("rb") as catalog_file:
            translation = gettext.GNUTranslations(catalog_file)
        language = catalog_path.parent.parent.name
        missing = []
        for message in INSTALLER_FAILURE_MESSAGES:
            translated = translation.gettext(message)
            if not translated or (translated == message and language != "en"):
                missing.append(message)
        assert not missing, f"{catalog_path.parent.parent.name}: {missing}"


def test_portuguese_installer_failure_translation() -> None:
    translation = gettext.translation(
        "biglinux-livecd",
        localedir=LOCALE_ROOT,
        languages=["pt_BR"],
    )

    assert translation.gettext("Installation failed") == "Falha na instalação"
    assert translation.gettext(
        "The installation failed. The local error log was saved in your home folder."
    ) == "A instalação falhou. O log de erro local foi salvo na sua pasta pessoal."


def test_installer_launcher_translates_failure_dialog() -> None:
    launcher = (PACKAGE / "usr/bin/calamares-biglinux").read_text(encoding="utf-8")

    assert '--title="$(_ \"Installation failed\")"' in launcher
    assert (
        '--text="$(_ \"The installation failed. The local error log was saved in your home folder.\")"'
        in launcher
    )
