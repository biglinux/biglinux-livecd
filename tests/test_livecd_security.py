from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PACKAGE = REPOSITORY / "biglinux-livecd"
KERNEL_OPTIONS = PACKAGE / "usr/lib/biglinux-livecd/kernel-options"
INSTALL_SETUP = PACKAGE / "usr/bin/biglinux-install-setup.sh"
STARTBIGLIVE = PACKAGE / "usr/bin/startbiglive"
LIVE_STATE = PACKAGE / "usr/lib/biglinux-livecd/live-state"
STORAGE_PROBE = PACKAGE / "usr/lib/biglinux-livecd/storage-probe"


def run_bash(
    script: str, *, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    merged_environment = os.environ.copy()
    merged_environment.update(environment)
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=merged_environment,
    )


def make_stub(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.write_text(f"#!/usr/bin/env bash\nset -eu\n{content}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_kernel_arguments_are_exact_allowlisted_and_sanitized(tmp_path: Path) -> None:
    cmdline = tmp_path / "cmdline"
    cmdline.write_text(
        "BOOT_IMAGE=/boot/vmlinuz rw quiet splash driver=nonfree "
        "notsshenable biglinux.bootcmd=$(touch_/tmp/pwn) safe=1 safe=1\n",
        encoding="utf-8",
    )
    result = run_bash(
        """
source "$KERNEL_OPTIONS"
kernel_cmdline_path=$CMDLINE
kernel_has_argument sshenable; printf 'ssh=%s\n' "$?"
printf 'installed=%s\n' "$(installed_kernel_arguments)"
printf 'sanitized=%s\n' "$(sanitize_installed_kernel_arguments 'quiet splash rw sshenable keep=1 keep=1')"
printf 'allowed=%s\n' "$(live_boot_command_path only-calamares)"
live_boot_command_path '$(touch /tmp/pwn)' >/dev/null; printf 'rejected=%s\n' "$?"
""",
        environment={"KERNEL_OPTIONS": str(KERNEL_OPTIONS), "CMDLINE": str(cmdline)},
    )
    assert result.returncode == 0, result.stderr
    assert "ssh=1" in result.stdout
    assert "installed=notsshenable safe=1" in result.stdout
    assert "sanitized=quiet splash keep=1" in result.stdout
    assert "allowed=/usr/bin/only-calamares" in result.stdout
    assert "rejected=1" in result.stdout
    assert not Path("/tmp/pwn").exists()


def test_duplicate_boot_command_is_ambiguous(tmp_path: Path) -> None:
    cmdline = tmp_path / "cmdline"
    cmdline.write_text(
        "biglinux.bootcmd=konsole biglinux.bootcmd=only-calamares\n",
        encoding="utf-8",
    )
    result = run_bash(
        """
source "$KERNEL_OPTIONS"
kernel_cmdline_path=$CMDLINE
kernel_option_value biglinux.bootcmd >/dev/null
printf '%s\n' "$?"
""",
        environment={"KERNEL_OPTIONS": str(KERNEL_OPTIONS), "CMDLINE": str(cmdline)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "2"


def test_grub_update_is_atomic_filtered_and_shell_safe(tmp_path: Path) -> None:
    root = tmp_path / "target"
    grub = root / "etc/default/grub"
    grub.parent.mkdir(parents=True)
    grub.write_text(
        'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash existing=1 '
        'evil=$(touch /tmp/biglinux-livecd-test-pwn)"\n'
        "GRUB_SAVEDEFAULT=true\n",
        encoding="utf-8",
    )
    grub.chmod(0o640)
    cmdline = tmp_path / "cmdline"
    cmdline.write_text(
        "BOOT_IMAGE=/boot/vmlinuz rw driver=nonfree sshenable "
        "biglinux.bootcmd=konsole live=ok live=ok\n",
        encoding="utf-8",
    )
    result = run_bash(
        """
source "$INSTALL_SETUP"
load_kernel_options
root_mount=$TARGET_ROOT
kernel_cmdline_path=$CMDLINE
write_grub_configuration "$GRUB_FILE"
bash -n "$GRUB_FILE"
source "$GRUB_FILE"
""",
        environment={
            "INSTALL_SETUP": str(INSTALL_SETUP),
            "TARGET_ROOT": str(root),
            "CMDLINE": str(cmdline),
            "GRUB_FILE": str(grub),
        },
    )
    assert result.returncode == 0, result.stderr
    content = grub.read_text(encoding="utf-8")
    assert "driver=" not in content
    assert "sshenable" not in content
    assert "biglinux.bootcmd" not in content
    assert content.count("live=ok") == 1
    assert "GRUB_SAVEDEFAULT=false" in content
    assert "GRUB_EARLY_INITRD_LINUX_STOCK=''" in content
    assert r"evil=\$(touch" in content
    assert stat.S_IMODE(grub.stat().st_mode) == 0o640
    assert not (tmp_path / "biglinux-livecd-test-pwn").exists()
    assert not Path("/tmp/biglinux-livecd-test-pwn").exists()


def test_grub_update_rejects_ambiguous_or_symlink_configuration(tmp_path: Path) -> None:
    root = tmp_path / "target"
    grub = root / "etc/default/grub"
    grub.parent.mkdir(parents=True)
    grub.write_text(
        'GRUB_CMDLINE_LINUX_DEFAULT="a=1"\nGRUB_CMDLINE_LINUX_DEFAULT="b=2"\n',
        encoding="utf-8",
    )
    cmdline = tmp_path / "cmdline"
    cmdline.write_text("quiet\n", encoding="utf-8")
    environment = {
        "INSTALL_SETUP": str(INSTALL_SETUP),
        "TARGET_ROOT": str(root),
        "CMDLINE": str(cmdline),
        "GRUB_FILE": str(grub),
    }
    ambiguous = run_bash(
        """
source "$INSTALL_SETUP"
load_kernel_options
root_mount=$TARGET_ROOT
kernel_cmdline_path=$CMDLINE
write_grub_configuration "$GRUB_FILE"
""",
        environment=environment,
    )
    assert ambiguous.returncode != 0

    real_grub = root / "etc/default/grub.real"
    real_grub.write_text('GRUB_CMDLINE_LINUX_DEFAULT="quiet"\n', encoding="utf-8")
    grub.unlink()
    grub.symlink_to(real_grub)
    symlink = run_bash(
        """
source "$INSTALL_SETUP"
load_kernel_options
root_mount=$TARGET_ROOT
kernel_cmdline_path=$CMDLINE
write_grub_configuration "$GRUB_FILE"
""",
        environment=environment,
    )
    assert symlink.returncode != 0


def test_install_setup_accepts_regular_file_with_localized_stat(
    tmp_path: Path,
) -> None:
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    make_stub(
        stubs,
        "stat",
        """
if [[ ${1:-} == -c && ${2:-} == %F ]]; then
    if [[ ${LC_ALL:-} == C ]]; then
        printf '%s\\n' 'regular file'
    else
        printf '%s\\n' 'arquivo comum'
    fi
    exit 0
fi
exec /usr/bin/stat "$@"
""".strip(),
    )
    root = tmp_path / "target"
    destination = root / "etc/big-default-config/theme"
    source = tmp_path / "live-theme"
    root.mkdir()
    source.write_text("dark\n", encoding="utf-8")
    result = run_bash(
        """
source "$INSTALL_SETUP"
root_mount=$TARGET_ROOT
copy_live_config "$SOURCE" "$DESTINATION"
""",
        environment={
            "INSTALL_SETUP": str(INSTALL_SETUP),
            "TARGET_ROOT": str(root),
            "SOURCE": str(source),
            "DESTINATION": str(destination),
            "LC_ALL": "pt_BR.UTF-8",
            "PATH": f"{stubs}:/usr/bin:/bin",
        },
    )
    assert result.returncode == 0, result.stderr
    assert destination.read_text(encoding="utf-8") == "dark\n"


def test_startbiglive_falls_back_when_sddm_runtime_is_unavailable(
    tmp_path: Path,
) -> None:
    source = STARTBIGLIVE.read_text(encoding="utf-8")
    start = source.index("user_id=$(id -u)")
    end = source.index("\n_check_loop_protection()")
    setup = source[start:end]
    result = run_bash(
        f"""
_log() {{ :; }}
{setup}
printf '%s\\n' "$attempt_file"
""",
        environment={"XDG_RUNTIME_DIR": str(tmp_path / "missing-runtime")},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "/tmp/startbiglive-attempts"


def test_startbiglive_passes_wizard_as_single_kwin_session(tmp_path: Path) -> None:
    source = STARTBIGLIVE.read_text(encoding="utf-8")
    start = source.index("_start_kwin_wizard() {")
    end = source.index("\n# Start mutter compositor", start)
    function = source[start:end]
    capture = tmp_path / "kwin-arguments"
    result = run_bash(
        f"""
_log() {{ :; }}
_detect_multi_gpu() {{
    is_multi_gpu=0
    primary_card=
    has_nvidia_proprietary=0
}}
sleep() {{ :; }}
dbus-run-session() {{
    printf '%s\\0' "$@" >"$CAPTURE"
    command sleep 0.2
}}
{function}
_start_kwin_wizard
""",
        environment={"CAPTURE": str(capture)},
    )
    assert result.returncode == 0, result.stderr
    assert capture.read_bytes().split(b"\0")[:-1] == [
        b"kwin_wayland",
        b"--drm",
        b"--no-lockscreen",
        b"--xwayland",
        b"--exit-with-session",
        b"/usr/bin/python /usr/share/biglinux/livecd/main.py",
    ]


def test_installer_prefers_current_gnome_settings_without_following_home_links(
    tmp_path: Path,
) -> None:
    homes = tmp_path / "home"
    homes.mkdir()
    fallback = tmp_path / "state/gnome-settings"
    fallback.parent.mkdir()
    fallback.write_text("fallback", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    unsafe_home = homes / "unsafe"
    unsafe_home.symlink_to(outside, target_is_directory=True)
    safe_settings = homes / "live/.config/dconf/settings.gnome"
    safe_settings.parent.mkdir(parents=True)
    safe_settings.write_text("current", encoding="utf-8")
    result = run_bash(
        """
source "$INSTALL_SETUP"
current_gnome_settings_source "$HOMES" "$FALLBACK"
""",
        environment={
            "INSTALL_SETUP": str(INSTALL_SETUP),
            "HOMES": str(homes),
            "FALLBACK": str(fallback),
        },
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(safe_settings.resolve())


def test_live_state_write_is_atomic_and_rejects_unknown_names(tmp_path: Path) -> None:
    state_directory = tmp_path / "state"
    state_directory.mkdir()
    result = run_bash(
        """
source "$LIVE_STATE"
live_state_directory=$STATE_DIRECTORY
write_live_state language pt_BR
write_live_state unsupported value >/dev/null 2>&1; printf 'unsupported=%s\n' "$?"
""",
        environment={
            "LIVE_STATE": str(LIVE_STATE),
            "STATE_DIRECTORY": str(state_directory),
        },
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "unsupported=1"
    state_file = state_directory / "big_language"
    assert state_file.read_text(encoding="utf-8") == "pt_BR"
    assert stat.S_IMODE(state_file.stat().st_mode) == 0o600
    assert list(state_directory.glob(".language.*")) == []


def test_efi_probe_excludes_the_live_device_tree() -> None:
    result = run_bash(
        """
source "$STORAGE_PROBE"
test_findmnt() { printf '%s\n' /dev/sdb1; }
test_lsblk() {
    case "$*" in
        *PATH,PARTTYPE*)
            printf '%s\n' \
                '/dev/sda1 c12a7328-f81f-11d2-ba4b-00a0c93ec93b' \
                '/dev/sdb2 C12A7328-F81F-11D2-BA4B-00A0C93EC93B' \
                '/dev/sdc1 0xef' \
                '/dev/sda2 0x8300'
            ;;
        */dev/sdb1) printf '%s\n' /dev/sdb1 /dev/sdb ;;
        */dev/sdb2) printf '%s\n' /dev/sdb2 /dev/sdb ;;
        */dev/sda1) printf '%s\n' /dev/sda1 /dev/sda ;;
        */dev/sdc1) printf '%s\n' /dev/sdc1 /dev/sdc ;;
        *) return 1 ;;
    esac
}
findmnt_command=test_findmnt
lsblk_command=test_lsblk
count_non_live_efi_partitions /run/miso/bootmnt
""",
        environment={"STORAGE_PROBE": str(STORAGE_PROBE)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "2"


def test_efi_probe_fails_closed_when_device_ancestry_is_unavailable() -> None:
    result = run_bash(
        """
source "$STORAGE_PROBE"
test_findmnt() { printf '%s\n' /dev/sdb1; }
test_lsblk() { return 1; }
findmnt_command=test_findmnt
lsblk_command=test_lsblk
count_non_live_efi_partitions /run/miso/bootmnt
""",
        environment={"STORAGE_PROBE": str(STORAGE_PROBE)},
    )
    assert result.returncode != 0


def test_livecd_tweaks_requires_marker_and_exact_flags(tmp_path: Path) -> None:
    source = (PACKAGE / "usr/bin/livecd-tweaks").read_text(encoding="utf-8")
    source = source.replace(
        "source /usr/lib/biglinux-livecd/kernel-options",
        'source "$KERNEL_OPTIONS"',
    )
    test_script = tmp_path / "livecd-tweaks"
    test_script.write_text(source, encoding="utf-8")
    log = tmp_path / "calls"
    executable = Path("/usr/bin/true")
    marker = tmp_path / "livefs-pkgs.txt"
    cmdline = tmp_path / "cmdline"
    console = tmp_path / "console"
    environment = {
        "KERNEL_OPTIONS": str(KERNEL_OPTIONS),
        "TEST_SCRIPT": str(test_script),
        "TEST_LOG": str(log),
        "CMDLINE": str(cmdline),
        "MARKER": str(marker),
        "CONSOLE": str(console),
        "EXECUTABLE": str(executable),
    }
    command = """
source "$TEST_SCRIPT"
test_systemctl() { printf 'systemctl:%s\n' "$*" >>"$TEST_LOG"; }
test_mount() { printf 'mount:%s\n' "$*" >>"$TEST_LOG"; }
test_mountpoint() { return 1; }
test_chpasswd() {
    local password
    IFS= read -r password
    printf 'chpasswd:%s\n' "$password" >>"$TEST_LOG"
}
kernel_cmdline_path=$CMDLINE
live_marker=$MARKER
console_path=$CONSOLE
systemctl_bin=test_systemctl
mount_bin=test_mount
mountpoint_bin=test_mountpoint
chpasswd_bin=test_chpasswd
mkinitcpio_path=$EXECUTABLE
mkinitcpio_shim=$EXECUTABLE
main
"""
    cmdline.write_text("notsshenable driver=notfree\n", encoding="utf-8")
    no_marker = run_bash(command, environment=environment)
    assert no_marker.returncode == 0, no_marker.stderr
    assert not log.exists()

    marker.touch()
    cmdline.write_text("driver=free driver=nonfree sshenable\n", encoding="utf-8")
    enabled = run_bash(command, environment=environment)
    assert enabled.returncode == 0, enabled.stderr
    calls = log.read_text(encoding="utf-8")
    assert "systemctl:mask --runtime --now mhwd-live.service" in calls
    assert f"mount:--bind {executable} {executable}" in calls
    assert "chpasswd:biglinux:biglinux" in calls
    assert "systemctl:start sshd.service" in calls
    assert "WARNING: Live SSH enabled" in console.read_text(encoding="utf-8")


def test_privileged_installer_uses_a_minimal_environment() -> None:
    with tempfile.TemporaryDirectory(
        prefix=".test-polkit-", dir=REPOSITORY
    ) as directory:
        test_directory = Path(directory)
        stubs = test_directory / "stubs"
        stubs.mkdir()
        log = test_directory / "sudo-arguments"
        make_stub(stubs, "id", "printf '1000\\n'")
        make_stub(stubs, "gsettings", "printf \"'prefer-dark'\\n\"")
        make_stub(
            stubs,
            "dbus-send",
            "printf '   string \"unix:path=/run/user/1000/at-spi/bus_0\"\\n'",
        )
        make_stub(stubs, "sudo", 'printf "%s\\n" "$@" >"$TEST_LOG"')
        wrapper = PACKAGE / "usr/bin/calamares-biglinux_polkit"
        result = subprocess.run(
            [str(wrapper), "--software-render"],
            check=False,
            capture_output=True,
            text=True,
            env={
                "PATH": f"{stubs}:/usr/bin:/bin",
                "USER": "liveuser",
                "DISPLAY": ":1",
                "LANG": "pt_BR.UTF-8",
                "LANGUAGE": "pt_BR:pt",
                "LC_MESSAGES": "pt_BR.UTF-8",
                "DESKTOP_STARTUP_ID": "cinnamon-launcher_TIME1",
                "XDG_ACTIVATION_TOKEN": "activation-token-1",
                "LD_PRELOAD": "/tmp/evil.so",
                "TEST_LOG": str(log),
            },
        )
        assert result.returncode == 0, result.stderr
        arguments = log.read_text(encoding="utf-8")
    assert "/usr/bin/env\n-i\n" in arguments
    assert "BIGLINUX_LIVE_USER=liveuser" in arguments
    assert "ADW_DEBUG_COLOR_SCHEME=prefer-dark" in arguments
    assert "DISPLAY=:1" in arguments
    assert "LANGUAGE=pt_BR:pt" in arguments
    assert "LC_MESSAGES=pt_BR.UTF-8" in arguments
    assert "DESKTOP_STARTUP_ID=cinnamon-launcher_TIME1" in arguments
    assert "XDG_ACTIVATION_TOKEN=activation-token-1" in arguments
    assert "QT_QUICK_BACKEND=software" in arguments
    assert "LD_PRELOAD" not in arguments
    assert arguments.rstrip().endswith("/usr/bin/calamares-biglinux")


def test_installer_waits_in_one_foreground_flow() -> None:
    launcher = (PACKAGE / "usr/bin/calamares-biglinux").read_text(encoding="utf-8")
    assert "integrity-wait" in launcher
    assert "wait_for_verification |" in launcher
    assert "Verification complete" in launcher
    assert "The files are intact." in launcher
    assert "sleep 600 |" not in launcher
    assert "verification_dialog_pid" not in launcher


def test_packaging_no_longer_replaces_distribution_binaries() -> None:
    tracked_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (
            PACKAGE / "usr/bin/livecd-tweaks",
            PACKAGE / "usr/bin/calamares-biglinux",
            REPOSITORY / "pkgbuild/biglinux-livecd.install",
        )
    )
    assert "calamares-manjaro" not in tracked_text
    assert "mv -f /usr/bin/calamares" not in tracked_text
    assert "cp -f /usr/bin/mhwd-live" not in tracked_text
    assert "cp -f /usr/bin/mkinitcpio" not in tracked_text
    assert not (PACKAGE / "usr/share/libalpm/hooks/99-biglinux-calamares.hook").exists()
    assert not (PACKAGE / "usr/share/libalpm/scripts/calamares-biglinux").exists()
    assert "enable livecd-tweaks.service" in (
        PACKAGE / "usr/lib/systemd/system-preset/50-biglinux-livecd.preset"
    ).read_text(encoding="utf-8")
    assert "enable biglinux-language-suggestion.service" in (
        PACKAGE / "usr/lib/systemd/system-preset/50-biglinux-livecd.preset"
    ).read_text(encoding="utf-8")
    pkgbuild = (REPOSITORY / "pkgbuild/PKGBUILD").read_text(encoding="utf-8")
    assert "for catalog in biglinux-livecd/locale/*.po" in pkgbuild
    assert "msgfmt --check-format" in pkgbuild
