from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

REPOSITORY = Path(__file__).resolve().parents[1]
CALAMARES = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares"
sys.path.insert(0, str(CALAMARES))

from src.infrastructure import file_operations  # noqa: E402
from src.profile import load_profile  # noqa: E402
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
    monkeypatch.setattr(install_service, "write_text_file", lambda *_args: False)
    owner = SimpleNamespace(
        _current_config=SimpleNamespace(sfs_folder=""), system_service=fake_service
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
    monkeypatch.setitem(install_service.CALAMARES_CONFIGS, "unpackfs", output)
    owner = SimpleNamespace(
        _current_config=SimpleNamespace(sfs_folder=""),
        system_service=fake_service,
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


def test_profile_metadata_is_loaded_from_the_materialized_directory(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / "profile.json").write_text(
        json.dumps(
            {
                "id": "xivastudio",
                "display_name": "XivaStudio",
                "netinstall": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CALAMARES_PROFILE_DIRECTORY", str(tmp_path))

    assert load_profile() == {
        "id": "xivastudio",
        "display_name": "XivaStudio",
    }


def test_profile_metadata_falls_back_for_invalid_json(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / "profile.json").write_text("[]", encoding="utf-8")
    monkeypatch.setenv("CALAMARES_PROFILE_DIRECTORY", str(tmp_path))

    assert load_profile() == {
        "id": tmp_path.name,
        "display_name": tmp_path.name,
    }


def test_calamares_branding_uses_current_os_release_substitutions() -> None:
    branding_files = sorted(
        (REPOSITORY / "biglinux-livecd").glob("usr/share/**/branding/*/branding.desc")
    )

    assert len(branding_files) == 4
    expected_product_names = {
        "biglinux": "BigLinux",
        "xivastudio": "XivaStudio",
        "bigcommunity": "BigCommunity",
    }
    for branding_file in branding_files:
        branding = branding_file.read_text(encoding="utf-8")
        assert (
            f"productName: {expected_product_names[branding_file.parent.name]}"
            in branding
        )
        assert 'versionedName: "${PRETTY_NAME}"' in branding
        assert 'shortVersionedName: "' in branding
        assert "@{" not in branding


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
    service = install_service.InstallService(SimpleNamespace())
    called: list[str] = []
    monkeypatch.setattr(service, "_configure_partition_settings", lambda: True)
    monkeypatch.setattr(service, "_configure_unpack_settings", lambda: True)
    monkeypatch.setattr(
        service,
        "_configure_package_settings",
        lambda: called.append("packages") is None,
    )
    config = install_service.InstallationConfig()
    config.packages_to_install = ["new-package"]

    assert service.configure_installation(config)
    assert called == ["packages"]
    assert install_service.TEMP_FILES["start_calamares"].is_file()

    service.cleanup()
    assert install_service.TEMP_FILES["start_calamares"].is_file()
    assert not install_service.TEMP_FILES["wait_install"].exists()


def test_profiles_mount_target_virtual_filesystems() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    mount_files = sorted(profiles.glob("*/modules/mount.conf"))
    assert {path.parents[1].name for path in mount_files} == {
        "bigcommunity",
        "biglinux",
        "xivastudio",
    }

    for mount_file in mount_files:
        config = yaml.safe_load(mount_file.read_text(encoding="utf-8"))
        extra_mounts = {entry["mountPoint"]: entry for entry in config["extraMounts"]}
        assert extra_mounts["/proc"] == {
            "device": "proc",
            "fs": "proc",
            "mountPoint": "/proc",
        }
        assert "/sys" in extra_mounts
        assert "/dev" in extra_mounts
        assert "/run" in extra_mounts
        assert "/run/udev" in extra_mounts
        assert extra_mounts["/sys/firmware/efi/efivars"]["efi"] is True
        assert "mountOptions" in config
        assert "mount" not in config


def test_profiles_hide_navigation_during_installation() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    settings_files = sorted(profiles.glob("*/settings*.conf"))
    assert settings_files

    for settings_file in settings_files:
        settings = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
        assert settings["hide-back-and-next-during-exec"] is True


def test_biglinux_pong_starts_only_when_slideshow_is_activated() -> None:
    pong = (
        REPOSITORY
        / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux"
        / "branding/biglinux/pong.qml"
    ).read_text(encoding="utf-8")

    assert "property bool slideshowActive: false" in pong
    assert "Component.onCompleted: gameArea.pause()" in pong
    assert "function onActivate()" in pong
    assert "gameArea.resetGame()" in pong
    assert "leftScore = 0" in pong
    assert "rightScore = 0" in pong


def test_biglinux_install_navigation_layout() -> None:
    navigation = (
        REPOSITORY
        / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux"
        / "branding/biglinux/calamares-navigation.qml"
    ).read_text(encoding="utf-8")

    assert "readonly property bool finalStep:" in navigation
    assert "ViewManager.currentStepIndex === steps.count - 1" in navigation
    # ListView.count only reports the model rows when a delegate exists.
    assert "delegate: Item {}" in navigation
    # Quit sits on the right whenever it is the only action: last step, and
    # while the installation hides back and next.
    assert "visible: root.actionsOnRight" in navigation
    assert navigation.index("visible: root.actionsOnRight") < navigation.index(
        "text: root.cleanLabel(ViewManager.quitLabel)"
    )
    assert (
        navigation.count("visible: ViewManager.backAndNextVisible && !root.finalStep")
        == 2
    )


def test_biglinux_installation_visual_adjustments() -> None:
    branding = (
        REPOSITORY
        / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux"
        / "branding/biglinux"
    )
    sidebar = (branding / "calamares-sidebar.qml").read_text(encoding="utf-8")
    users = (branding / "usersq.qml").read_text(encoding="utf-8")
    pong = (branding / "pong.qml").read_text(encoding="utf-8")
    stylesheet = (branding / "stylesheet.qss").read_text(encoding="utf-8")

    # The logo only joins the sidebar after the welcome page hands over, and
    # it animates in instead of appearing abruptly.
    assert "property real logoReveal" in sidebar
    assert "Behavior on logoReveal" in sidebar
    assert "RotationAnimator" not in sidebar
    assert "rings/" not in sidebar
    # The sidebar keeps the window color so the title bar never contrasts with
    # it; the steps live on a dark floating panel instead.
    assert "color: palette.window" in sidebar
    assert 'readonly property color panelBackground: "#16273C"' in sidebar
    assert "rings/" not in users
    assert 'text: "BigLinux"' not in pong
    assert "Installing BigLinux" not in pong
    assert "Player %1" not in pong
    assert 'text: "%1 — %2"' in pong

    assert "property real baseBallSpeed: Math.max(6.0, width / 150)" in pong
    assert "property real maxBallSpeed: Math.max(13.0, width / 62)" in pong
    assert "currentSpeed * 1.09" in pong
    assert 'color: "#FFFFFF"' in pong
    assert "font.weight: Font.DemiBold" in pong
    assert "background: Rectangle" in pong

    assert "#mainApp QProgressBar" in stylesheet
    assert "#mainApp QProgressBar::chunk" in stylesheet
    # The progress chunk carries the brand blue instead of the Qt palette.
    assert "background-color: #1976C9" in stylesheet


def test_compatibility_branding_matches_active_biglinux_branding() -> None:
    active = (
        REPOSITORY
        / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux"
        / "branding/biglinux"
    )
    compatibility = REPOSITORY / "biglinux-livecd/usr/share/calamares/branding/biglinux"

    for filename in (
        "branding.desc",
        "calamares-sidebar.qml",
        "logo.svg",
        "pong.qml",
        "stylesheet.qss",
    ):
        assert (compatibility / filename).read_bytes() == (
            active / filename
        ).read_bytes()


def test_all_calamares_profile_configuration_is_valid_yaml() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    configuration_files = sorted(profiles.glob("*/modules/*.conf"))
    configuration_files.extend(sorted(profiles.glob("*/settings*.conf")))
    assert configuration_files

    for configuration_file in configuration_files:
        parsed = yaml.safe_load(configuration_file.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), configuration_file


def test_profiles_ship_complete_mhwd_configuration() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"

    for configuration_file in sorted(profiles.glob("*/modules/mhwdcfg.conf")):
        configuration = yaml.safe_load(configuration_file.read_text(encoding="utf-8"))
        assert configuration == {
            "identifier": {"net": [200, 280], "video": [300]},
            "bus": ["pci", "usb"],
            "driver": "free",
            "local": True,
            "repo": "/opt/pacman-mhwd.conf",
        }


def test_launcher_preserves_mhwd_configuration_and_skips_free_driver_job() -> None:
    launcher = (REPOSITORY / "biglinux-livecd/usr/bin/calamares-biglinux").read_text(
        encoding="utf-8"
    )

    assert "printf '%s\\n' '---' \"driver: $driver\"" not in launcher
    assert 'sed -i "s/^driver:.*/driver: $driver/"' in launcher
    assert "[[ $driver == free ]]" in launcher
    assert "- mhwdcfg[[:space:]]*$" in launcher


def test_profiles_use_supported_password_requirement() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    configuration_files = sorted(profiles.glob("*/modules/users.conf"))
    configuration_files.append(profiles / "biglinux/modules/usersq.conf")

    for configuration_file in configuration_files:
        configuration = yaml.safe_load(configuration_file.read_text(encoding="utf-8"))
        assert configuration["passwordRequirements"] == {"minLength": 1}


def test_profiles_make_luks_generation_explicit() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"

    for configuration_file in sorted(profiles.glob("*/modules/partition.conf")):
        configuration = yaml.safe_load(configuration_file.read_text(encoding="utf-8"))
        assert configuration["luksGeneration"] == "luks2"
        assert "defaultPartitionTableType" not in configuration


def test_custom_jobs_have_mapping_configuration_files() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"

    for profile in ("bigcommunity", "biglinux", "xivastudio"):
        for module in ("grubcfg-fix", "btrfs-fix"):
            configuration_file = profiles / profile / "modules" / f"{module}.conf"
            assert yaml.safe_load(configuration_file.read_text(encoding="utf-8")) == {}


def test_biglinux_qml_modules_use_branding_search_mode() -> None:
    modules = (
        REPOSITORY
        / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux/modules"
    )

    for module in ("finishedq", "summaryq", "usersq", "welcomeq"):
        configuration = yaml.safe_load(
            (modules / f"{module}.conf").read_text(encoding="utf-8")
        )
        assert configuration["qmlSearch"] == "branding"


def test_biglinux_finished_page_animates_on_entrance() -> None:
    branding = (
        REPOSITORY
        / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux"
        / "branding/biglinux"
    )
    finished = (branding / "finishedq.qml").read_text(encoding="utf-8")
    descriptor = (branding / "branding.desc").read_text(encoding="utf-8")

    # The installation work is over here, so the page may animate; what it
    # must not do is spin images the way the old artwork did.
    assert "RotationAnimator" not in finished
    assert "rings/" not in finished
    assert 'property: "reveal"' in finished
    assert "Easing.OutBack" in finished
    assert 'productLogo: "logo.svg"' in descriptor
    assert 'text: root.tr("Restart system")' in finished
    # The primary action paints its own background so the accent survives
    # whichever Qt Quick Controls style the live session provides.
    assert "root.palette.highlight" in finished
    # config.failed is the module's own notifying property; a binding on
    # Global.value() would never re-evaluate after the install finished.
    assert "readonly property bool installationSucceeded: !config.failed" in finished
    assert 'root.tr("Installation interrupted")' in finished


def test_biglinux_unmounts_before_showing_the_finished_page() -> None:
    profile = (
        REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles/biglinux"
    )

    for settings_file in ("settings.conf", "settings-hybrid-fallback.conf"):
        settings = yaml.safe_load((profile / settings_file).read_text(encoding="utf-8"))
        execution = next(
            phase["exec"] for phase in settings["sequence"] if "exec" in phase
        )
        assert execution[-1] == "umount"

    navigation = (profile / "branding/biglinux/calamares-navigation.qml").read_text(
        encoding="utf-8"
    )
    # Global is only bound in module QML, so navigation cannot read it.
    assert "Global" not in navigation


def test_biglinux_tunes_luks_for_the_bootloader() -> None:
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    for profile in (profiles / p for p in ("biglinux", "bigcommunity", "xivastudio")):
        check_luks_tuning(profile)


def test_every_module_instance_in_a_sequence_is_declared() -> None:
    # A "module@instance" step whose instance is not declared does not fail the
    # install: Calamares falls back to the module's stock configuration, and for
    # shellprocess that is the upstream example, which runs a command that does
    # not exist and aborts the install at the very end.
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    for settings_file in sorted(profiles.glob("*/settings*.conf")):
        settings = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
        declared = {instance["id"]: instance for instance in settings.get("instances", [])}
        for phase in settings["sequence"]:
            for steps in phase.values():
                for step in steps:
                    if "@" not in step:
                        continue
                    module, _, instance = step.partition("@")
                    assert instance in declared, f"{settings_file}: {step} has no instance"
                    assert declared[instance]["module"] == module
                    config = settings_file.parent / "modules" / declared[instance]["config"]
                    assert config.is_file(), f"{settings_file}: {config.name} is missing"


def test_navigation_hint_points_at_the_partition_step() -> None:
    # The bar shows the accent warning on the partitioning page, and identifies
    # that page by position: the ViewManager exposes the current index but no
    # module name. So the index in the QML has to match the show sequence.
    profiles = REPOSITORY / "biglinux-livecd/usr/share/biglinux/calamares-profiles"
    navigation = (
        profiles / "biglinux/branding/biglinux/calamares-navigation.qml"
    ).read_text(encoding="utf-8")
    declared = int(
        re.search(r"partitionStepIndex: (\d+)", navigation).group(1)
    )
    for settings_file in sorted(profiles.glob("*/settings*.conf")):
        settings = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
        shown = next(phase["show"] for phase in settings["sequence"] if "show" in phase)
        assert shown.index("partition") == declared, settings_file


def test_partition_template_selects_luks2() -> None:
    # The wizard writes this template over the profile's partition.conf, so the
    # LUKS generation has to be set here too.
    template = yaml.safe_load(
        (CALAMARES / "data/partition.conf").read_text(encoding="utf-8")
    )
    assert template["luksGeneration"] == "luks2"


def check_luks_tuning(profile) -> None:
    partition = yaml.safe_load(
        (profile / "modules/partition.conf").read_text(encoding="utf-8")
    )
    # GRUB 2.14 unlocks LUKS2 with Argon2id, so LUKS1 is no longer required.
    assert partition["luksGeneration"] == "luks2"

    tuning = yaml.safe_load(
        (profile / "modules/luks-pbkdf.conf").read_text(encoding="utf-8")
    )
    # cryptsetup would default to 1 GiB, which costs about four seconds of
    # Argon2id in GRUB before the boot menu shows up.
    assert tuning["pbkdfMemory"] <= 262144

    for settings_file in sorted(profile.glob("settings*.conf")):
        settings = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
        execution = next(
            phase["exec"] for phase in settings["sequence"] if "exec" in phase
        )
        # The keyslot has to be retuned before anything writes to the volume.
        assert execution.index("luks-pbkdf") == execution.index("partition") + 1
        assert execution.index("luks-pbkdf") < execution.index("bootloader")
        # The themed prompt lives in the core image grub-install just wrote.
        assert (
            execution.index("shellprocess@grub_crypt")
            == execution.index("bootloader") + 1
        )

    module = (
        REPOSITORY / "biglinux-livecd/usr/lib/calamares/modules/luks-pbkdf/main.py"
    ).read_text(encoding="utf-8")
    assert "luksConvertKey" in module
    assert '"--pbkdf",\n            "argon2id",' in module
    # Only the volume GRUB unlocks is retuned, and a reused volume without a
    # recorded passphrase must not abort an install that already partitioned.
    assert 'partition.get("mountPoint") in ("/", "/boot")' in module
    assert "leaving its keyslots alone" in module
