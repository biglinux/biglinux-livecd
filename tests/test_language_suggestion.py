from __future__ import annotations

import importlib.util
import json
import stat
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = (
    ROOT / "biglinux-livecd/usr/lib/biglinux-livecd/language_suggestion_probe.py"
)
LIVECD_SOURCE = ROOT / "biglinux-livecd/usr/share/biglinux/livecd"
sys.path.insert(0, str(LIVECD_SOURCE))

spec = importlib.util.spec_from_file_location("language_suggestion_probe", PROBE_PATH)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)

from suggested_locale import language_sort_key, load_suggested_locale  # noqa: E402


def test_locale_parsers_accept_supported_formats_and_reject_noise() -> None:
    configuration = """
# Installed system locale
LC_MESSAGES=en_US.UTF-8
LANG='fr_FR.UTF-8'
MALICIOUS=$(touch /tmp/no)
"""
    assert probe.parse_locale_configuration(configuration) == "fr_FR"
    assert probe.parse_locale_configuration("LANG=../../etc/passwd") is None

    strings = "en-US\nrecovery\nfr-FR\n../../pt-BR\n"
    assert probe.parse_windows_bcd_locales(strings, {"en_US", "fr_FR"}) == "fr_FR"
    assert probe.parse_windows_bcd_locales("en-US\n", {"en_US"}) == "en_US"


@pytest.mark.parametrize(
    ("country", "expected"),
    [("BR", "pt_BR"), ("FR", "fr_FR"), ("BE", "nl_BE")],
)
def test_geoip_country_uses_cldr_language_mapping(country: str, expected: str) -> None:
    supported = ("en_US", "pt_BR", "fr_FR", "nl_BE", "fr_BE")
    assert probe.locale_for_country(country, supported) == expected


def test_geoip_parser_reads_only_a_valid_country_code() -> None:
    response = "<Response><Ip>redacted</Ip><CountryCode>BR</CountryCode></Response>"
    assert probe.parse_geoip_country(response) == "BR"
    assert (
        probe.parse_geoip_country("<Response><CountryCode>BRA</CountryCode></Response>")
        is None
    )
    assert probe.parse_geoip_country("not xml") is None
    assert (
        probe.parse_geoip_country("<!ENTITY x 'BR'><CountryCode>&x;</CountryCode>")
        is None
    )
    assert probe.parse_geoip_country(" " * (probe.MAX_TEXT_BYTES + 1)) is None


def test_storage_inventory_excludes_the_complete_live_device_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "blockdevices": [
            {
                "path": "/dev/sda",
                "type": "disk",
                "children": [{"path": "/dev/sda1", "type": "part", "fstype": "btrfs"}],
            },
            {
                "path": "/dev/sdb",
                "type": "disk",
                "children": [
                    {"path": "/dev/sdb1", "type": "part", "fstype": "iso9660"},
                    {
                        "path": "/dev/sdb2",
                        "type": "part",
                        "fstype": "vfat",
                        "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b",
                    },
                ],
            },
            {
                "path": "/dev/nvme0n1",
                "type": "disk",
                "children": [
                    {"path": "/dev/nvme0n1p2", "type": "part", "fstype": "ext4"},
                    {
                        "path": "/dev/nvme0n1p1",
                        "type": "part",
                        "fstype": "vfat",
                        "parttype": "0xEF",
                    },
                ],
            },
        ]
    }

    def command(argv: list[str], _deadline: float) -> str | None:
        if argv[0].endswith("findmnt"):
            return "/dev/sdb1\n"
        return json.dumps(payload)

    monkeypatch.setattr(probe, "run_text_command", command)
    inventory = probe.storage_inventory(time.monotonic() + 1)
    assert inventory == probe.StorageInventory(
        linux_filesystems=(("/dev/nvme0n1p2", "ext4"), ("/dev/sda1", "btrfs")),
        efi_partitions=("/dev/nvme0n1p1",),
    )


def test_storage_inventory_fails_closed_without_live_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(probe, "run_text_command", lambda _argv, _deadline: None)
    assert probe.storage_inventory(time.monotonic() + 1) is None


def test_btrfs_probe_mounts_at_subvolume_at_without_log_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(probe, "WORK_DIRECTORY", tmp_path)
    monkeypatch.setattr(probe, "is_block_device", lambda _path: True)

    def command(argv: list[str], _deadline: float) -> str | None:
        calls.append(argv)
        if Path(argv[0]).name == "mount":
            mountpoint = Path(argv[-1])
            (mountpoint / "etc").mkdir()
            (mountpoint / "etc/locale.conf").write_text(
                "LANG=pt_BR.UTF-8\n", encoding="utf-8"
            )
        return ""

    monkeypatch.setattr(probe, "run_text_command", command)
    locale = probe.read_linux_locale("/dev/test", "btrfs", 0, time.monotonic() + 1)
    assert locale == "pt_BR"
    assert calls[0][0].endswith("mount")
    assert "ro,rescue=nologreplay,subvol=@" in calls[0]
    assert calls[-1][0].endswith("umount")


def test_btrfs_reader_rejects_symlinked_etc(tmp_path: Path) -> None:
    mounted = tmp_path / "mounted"
    outside = tmp_path / "outside"
    mounted.mkdir()
    outside.mkdir()
    (outside / "locale.conf").write_text("LANG=pt_BR.UTF-8\n", encoding="utf-8")
    (mounted / "etc").symlink_to(outside, target_is_directory=True)
    assert probe.read_bounded_file_beneath(mounted, ("etc", "locale.conf")) is None


def test_geoip_starts_with_linux_and_linux_has_priority() -> None:
    geoip_started = threading.Event()

    def geoip(_deadline: float) -> probe.LanguageSuggestion:
        geoip_started.set()
        return probe.LanguageSuggestion("pt_BR", "geoip")

    def linux(_deadline: float) -> probe.LanguageSuggestion:
        assert geoip_started.wait(timeout=0.5)
        return probe.LanguageSuggestion("fr_FR", "linux-btrfs")

    def unexpected_windows(_deadline: float) -> None:
        raise AssertionError("Windows must not run after a Linux result")

    assert probe.choose_suggestion(linux, unexpected_windows, geoip) == (
        probe.LanguageSuggestion("fr_FR", "linux-btrfs")
    )


def test_windows_wins_over_an_already_available_geoip_result() -> None:
    expected = probe.LanguageSuggestion("fr_FR", "windows-bcd")
    result = probe.choose_suggestion(
        lambda _deadline: None,
        lambda _deadline: expected,
        lambda _deadline: probe.LanguageSuggestion("pt_BR", "geoip"),
    )
    assert result == expected


def test_geoip_is_used_when_disk_probes_have_no_result() -> None:
    expected = probe.LanguageSuggestion("pt_BR", "geoip")
    result = probe.choose_suggestion(
        lambda _deadline: None,
        lambda _deadline: None,
        lambda _deadline: expected,
    )
    assert result == expected


def write_suggestion(path: Path, payload: object, mode: int = 0o644) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(mode)


def test_suggestion_reader_accepts_safe_supported_result(tmp_path: Path) -> None:
    result = tmp_path / "suggestion.json"
    write_suggestion(result, {"locale": "fr_FR", "source": "linux-btrfs"})
    assert load_suggested_locale({"fr_FR", "en_US"}, result) == "fr_FR"


def test_suggestion_reader_rejects_writable_symlink_and_unknown_source(
    tmp_path: Path,
) -> None:
    result = tmp_path / "suggestion.json"
    write_suggestion(result, {"locale": "fr_FR", "source": "geoip"}, 0o666)
    assert load_suggested_locale({"fr_FR"}, result) is None

    write_suggestion(result, {"locale": "fr_FR", "source": "guessed"})
    assert load_suggested_locale({"fr_FR"}, result) is None

    write_suggestion(result, {"locale": "fr_FR", "source": ["geoip"]})
    assert load_suggested_locale({"fr_FR"}, result) is None

    target = tmp_path / "target.json"
    write_suggestion(target, {"locale": "fr_FR", "source": "geoip"})
    result.unlink()
    result.symlink_to(target)
    assert load_suggested_locale({"fr_FR"}, result) is None


def test_detected_french_precedes_existing_favorites() -> None:
    locales = ["es_ES", "pt_BR", "fr_FR", "en_US", "de_DE"]
    ordered = sorted(
        locales,
        key=lambda locale: language_sort_key(locale, locale, "fr_FR"),
    )
    assert ordered == ["fr_FR", "en_US", "pt_BR", "es_ES", "de_DE"]


def test_published_result_is_atomic_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(probe, "WORK_DIRECTORY", tmp_path)
    monkeypatch.setattr(probe, "RESULT_PATH", tmp_path / "suggestion.json")
    probe.publish_suggestion(probe.LanguageSuggestion("pt_BR", "geoip"))
    assert json.loads(probe.RESULT_PATH.read_text(encoding="utf-8")) == {
        "locale": "pt_BR",
        "source": "geoip",
    }
    assert stat.S_IMODE(probe.RESULT_PATH.stat().st_mode) == 0o644
    assert list(tmp_path.glob(".suggestion-*")) == []


def test_subprocesses_never_use_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = "ok"

    def run(argv: list[str], **kwargs: object) -> Completed:
        captured.update(kwargs)
        assert argv == ["/usr/bin/example", "$(touch /tmp/no)"]
        return Completed()

    monkeypatch.setattr(probe.subprocess, "run", run)
    assert (
        probe.run_text_command(
            ["/usr/bin/example", "$(touch /tmp/no)"], time.monotonic() + 1
        )
        == "ok"
    )
    assert "shell" not in captured
