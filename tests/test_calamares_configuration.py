from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

REPOSITORY = Path(__file__).resolve().parents[1]
CALAMARES = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares"
sys.path.insert(0, str(CALAMARES))

from src.infrastructure import file_operations  # noqa: E402
from src.services import install_service, system_service  # noqa: E402


def test_atomic_text_write_preserves_old_file_on_replace_failure(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "settings.conf"
    target.write_text("old\n", encoding="utf-8")

    def fail_replace(_source, _target) -> None:
        raise OSError("simulated full filesystem")

    monkeypatch.setattr(file_operations.os, "replace", fail_replace)
    assert not file_operations.write_text_file("new\n", target)
    assert target.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob(".settings.conf.*")) == []


def test_unpack_configuration_propagates_write_failure(monkeypatch) -> None:
    fake_service = SimpleNamespace(get_sfs_folder=lambda: "manjaro")
    monkeypatch.setattr("src.services.get_system_service", lambda: fake_service)
    monkeypatch.setattr(install_service, "write_text_file", lambda *_args: False)
    owner = SimpleNamespace(
        _current_config=SimpleNamespace(custom_desktop=False, sfs_folder="")
    )
    assert not install_service.InstallService._configure_unpack_settings(owner)


def test_ext4_configuration_rejects_read_failure(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "partition-template.conf"
    source.write_text('defaultFileSystemType:  "btrfs"\n', encoding="utf-8")
    output = tmp_path / "partition.conf"
    monkeypatch.setattr(install_service, "PARTITION_CONF_FILE", source)
    monkeypatch.setitem(install_service.CALAMARES_CONFIGS, "partition", output)
    monkeypatch.setattr(install_service, "read_text_file", lambda *_args: None)
    owner = SimpleNamespace(
        _current_config=SimpleNamespace(filesystem_type="ext4"),
        logger=SimpleNamespace(debug=lambda *_args: None, error=lambda *_args: None),
    )
    assert not install_service.InstallService._configure_partition_settings(owner)


def test_unpack_configuration_is_valid_yaml(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "unpackfs.conf"
    fake_service = SimpleNamespace(get_sfs_folder=lambda: "manjaro")
    monkeypatch.setattr("src.services.get_system_service", lambda: fake_service)
    monkeypatch.setitem(install_service.CALAMARES_CONFIGS, "unpackfs", output)
    owner = SimpleNamespace(
        _current_config=SimpleNamespace(custom_desktop=False, sfs_folder=""),
        logger=SimpleNamespace(debug=lambda *_args: None, error=lambda *_args: None),
    )
    assert install_service.InstallService._configure_unpack_settings(owner)
    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    sources = [entry["source"] for entry in parsed["unpack"]]
    assert sources == [
        "/run/miso/bootmnt/manjaro/x86_64/rootfs.sfs",
        "/run/miso/bootmnt/manjaro/x86_64/desktopfs.sfs",
    ]


def test_system_service_uses_canonical_image_detector(
    monkeypatch, tmp_path: Path
) -> None:
    image_directory = tmp_path / "alpha/x86_64"
    monkeypatch.setattr(system_service, "detect_iso_mount", lambda: image_directory)
    owner = SimpleNamespace(logger=SimpleNamespace(warning=lambda *_args: None))
    assert system_service.SystemService._detect_sfs_folder(owner) == "alpha"


def test_main_settings_yaml_variants() -> None:
    for netinstall, minimal, custom_desktop in (
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
    ):
        config = SimpleNamespace(
            enable_xivastudio_netinstall=netinstall,
            packages_to_remove=[],
            packages_to_install=[],
            use_minimal=minimal,
            custom_desktop=custom_desktop,
            login_manager="sddm.service" if custom_desktop else "",
        )
        owner = SimpleNamespace(_current_config=config)
        owner._execution_sequence = (
            install_service.InstallService._execution_sequence.__get__(owner)
        )
        parsed = yaml.safe_load(
            install_service.InstallService._main_settings_text(owner)
        )
        shown = parsed["sequence"][0]["show"]
        executed = parsed["sequence"][1]["exec"]
        assert ("netinstall@xivastudio" in shown) is netinstall
        assert ("packages" in executed) is (netinstall or minimal)
        assert ("shellprocess@displaymanager_biglinux" in executed) is custom_desktop
        assert executed.count("partition") == 1


def test_packages_configuration_yaml_and_invalid_name(
    monkeypatch, tmp_path: Path
) -> None:
    output = tmp_path / "packages.conf"
    monkeypatch.setitem(install_service.CALAMARES_CONFIGS, "packages", output)
    config = SimpleNamespace(
        packages_to_remove=["old-package"], packages_to_install=["new-package"]
    )
    owner = SimpleNamespace(
        _current_config=config,
        logger=SimpleNamespace(debug=lambda *_args: None, error=lambda *_args: None),
    )
    assert install_service.InstallService._configure_package_settings(owner)
    operations = yaml.safe_load(output.read_text(encoding="utf-8"))["operations"]
    assert operations == [
        {"remove": ["old-package"]},
        {"install": ["new-package"]},
    ]
    config.packages_to_install = ['bad"\nname']
    assert not install_service.InstallService._configure_package_settings(owner)
    config.packages_to_install = ["--cascade"]
    assert not install_service.InstallService._configure_package_settings(owner)


def test_install_only_journey_generates_packages_configuration(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(
        install_service.TEMP_FILES, "wait_install", tmp_path / "wait_install"
    )
    monkeypatch.setitem(
        install_service.TEMP_FILES, "start_calamares", tmp_path / "start_calamares"
    )
    service = install_service.InstallService()
    called: list[str] = []
    monkeypatch.setattr(service, "_configure_partition_settings", lambda: True)
    monkeypatch.setattr(service, "_configure_unpack_settings", lambda: True)
    monkeypatch.setattr(
        service,
        "_configure_package_settings",
        lambda: called.append("packages") is None,
    )
    monkeypatch.setattr(service, "_configure_main_settings", lambda: True)
    monkeypatch.setattr(service, "_configure_shell_processes", lambda: True)
    config = install_service.InstallationConfig()
    config.packages_to_install = ["new-package"]

    assert service.configure_installation(config)
    assert called == ["packages"]
    assert install_service.TEMP_FILES["start_calamares"].is_file()
