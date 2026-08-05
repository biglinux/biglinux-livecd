from __future__ import annotations

import gettext
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "biglinux-livecd"
CATALOG_SOURCES = PACKAGE / "locale"
DOMAIN = "biglinux-livecd"


@pytest.fixture(scope="session")
def locale_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compile the .po sources the way the PKGBUILD does.

    The compiled catalogs used to be committed purely so these tests could
    read them, which left a second copy of every translation in the tree for
    the .po files to drift away from.
    """
    if not shutil.which("msgfmt"):
        pytest.skip("gettext is not installed")

    root = tmp_path_factory.mktemp("locale")
    sources = sorted(CATALOG_SOURCES.glob("*.po"))
    assert sources
    for source in sources:
        destination = root / source.stem / "LC_MESSAGES"
        destination.mkdir(parents=True)
        subprocess.run(
            ["msgfmt", "-c", str(source), "-o", str(destination / f"{DOMAIN}.mo")],
            check=True,
        )
    return root


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


def test_installed_catalogs_include_integrity_screen_messages(
    locale_root: Path,
) -> None:
    catalogs = sorted(locale_root.glob("*/LC_MESSAGES/biglinux-livecd.mo"))
    assert catalogs
    for catalog_path in catalogs:
        with catalog_path.open("rb") as catalog_file:
            translation = gettext.GNUTranslations(catalog_file)
        language = catalog_path.parent.parent.name
        missing = []
        for message in INTEGRITY_MESSAGES:
            translated = translation.gettext(message)
            # An entry present but empty translates to the source text, which
            # a membership test on the catalog would have accepted.
            if not translated or (translated == message and language != "en"):
                missing.append(message)
        assert not missing, f"{language}: {missing}"


def test_installed_catalogs_include_installer_failure_messages(
    locale_root: Path,
) -> None:
    catalogs = sorted(locale_root.glob("*/LC_MESSAGES/biglinux-livecd.mo"))
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


def test_portuguese_installer_failure_translation(locale_root: Path) -> None:
    translation = gettext.translation(
        "biglinux-livecd",
        localedir=locale_root,
        languages=["pt_BR"],
    )

    assert translation.gettext("Installation failed") == "Falha na instalação"
    assert (
        translation.gettext(
            "The installation failed. The local error log was saved in your home folder."
        )
        == "A instalação falhou. O log de erro local foi salvo na sua pasta pessoal."
    )


def test_installer_launcher_translates_failure_dialog() -> None:
    launcher = (PACKAGE / "usr/bin/calamares-biglinux").read_text(encoding="utf-8")

    assert '--title="$(_ "Installation failed")"' in launcher
    assert (
        '--text="$(_ "The installation failed. The local error log was saved in your home folder.")"'
        in launcher
    )
