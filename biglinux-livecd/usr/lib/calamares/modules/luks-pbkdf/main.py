#!/usr/bin/env python3
"""Lowers the Argon2id cost of the volume GRUB unlocks at boot.

cryptsetup sizes the key derivation for the running machine, up to 1 GiB, which
takes GRUB about four seconds before the boot menu appears. GRUB is the only
consumer that pays this price: every other volume is opened by the initramfs,
where the delay is hidden by the rest of the boot.
"""

import subprocess

import libcalamares


def pretty_name():
    return "Adjusting the encryption for the bootloader"


def root_device():
    """The LUKS container GRUB has to unlock, with its passphrase.

    Only the volume holding /boot matters here, and the passphrase is recorded
    per partition, not at the top of the global storage.
    """
    for partition in libcalamares.globalstorage.value("partitions") or []:
        if not partition.get("luksMapperName") or not partition.get("device"):
            continue
        if partition.get("mountPoint") in ("/", "/boot"):
            return partition["device"], partition.get("luksPassphrase") or ""
    return None, ""


def retune(device, passphrase, memory, iterations):
    """Rewrite the keyslot with a cost GRUB can afford. Never fatal."""
    is_luks2 = subprocess.run(
        ["cryptsetup", "isLuks", "--type", "luks2", device], check=False
    )
    if is_luks2.returncode != 0:
        return True

    completed = subprocess.run(
        [
            "cryptsetup",
            "luksConvertKey",
            "--batch-mode",
            "--pbkdf",
            "argon2id",
            "--pbkdf-memory",
            str(memory),
            "--pbkdf-force-iterations",
            str(iterations),
            device,
        ],
        input=passphrase.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        libcalamares.utils.warning(
            "cryptsetup could not retune {}: {}".format(
                device, completed.stderr.decode("utf-8", "replace").strip()
            )
        )
    return True


def run():
    device, passphrase = root_device()
    if device is None:
        return None

    if not passphrase:
        # The volume was unlocked by the user rather than created here. Aborting
        # now would leave a partitioned disk behind, so the install goes on,
        # leaving its keyslots alone and its boot a few seconds slower.
        libcalamares.utils.warning(
            "no passphrase recorded for {}, leaving its keyslots alone".format(device)
        )
        return None

    retune(
        device,
        passphrase,
        libcalamares.job.configuration.get("pbkdfMemory", 262144),
        libcalamares.job.configuration.get("pbkdfIterations", 4),
    )
    return None
