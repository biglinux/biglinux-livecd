from __future__ import annotations

import gettext
import re
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


def test_every_launcher_message_is_translated_everywhere(locale_root: Path) -> None:
    """These are the dialogs the installer shows before Calamares starts.

    Nine of them were missing from every catalog at once, because the
    translation pipeline could not see them in the source and dropped them on
    a later run. Nothing noticed until the dialogs came up in English.
    """
    launcher = PACKAGE / "usr/bin/calamares-biglinux"
    declared = re.findall(
        r'^msgid "((?:[^"\\]|\\.)+)"$',
        subprocess.run(
            ["bash", "--dump-po-strings", str(launcher)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout,
        re.M,
    )
    assert len(set(declared)) >= 17

    for catalog_path in sorted(locale_root.glob("*/LC_MESSAGES/biglinux-livecd.mo")):
        language = catalog_path.parent.parent.name
        if language == "en":
            continue
        with catalog_path.open("rb") as catalog_file:
            translation = gettext.GNUTranslations(catalog_file)
        missing = [
            message
            for message in set(declared)
            if translation.gettext(message) == message
        ]
        assert not missing, f"{language}: {missing}"


def test_every_launcher_message_is_extractable() -> None:
    """The pipeline reads shell strings with `bash --dump-po-strings`.

    It sees only bash's own $"..." form, so a message passed to gettext any
    other way is dropped from every catalog on the next run - which is exactly
    what happened to the two failure-dialog messages below.
    """
    launcher = PACKAGE / "usr/bin/calamares-biglinux"
    assert "$(_ " not in launcher.read_text(encoding="utf-8")

    extracted = subprocess.run(
        ["bash", "--dump-po-strings", str(launcher)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for message in INSTALLER_FAILURE_MESSAGES:
        assert f'msgid "{message}"' in extracted, message
