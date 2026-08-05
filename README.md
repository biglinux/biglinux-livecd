# biglinux-livecd

BigLinux live-session setup and Calamares installer integration.

This package is what runs between powering on the live media and having an
installed system: it starts the live desktop, offers a wizard to pick language,
keyboard and appearance before that desktop appears, and carries those choices
into the installation performed by Calamares.

## What the package provides

**Live session bootstrap.** `startbiglive` prepares the display manager and the
monitor layout, runs the setup wizard and then hands over to the desktop
session. `livecd-tweaks` applies the tweaks a live session needs before the user
arrives, including the ones requested through kernel arguments.

**Setup wizard** (`/usr/share/biglinux/livecd`, GTK4 and libadwaita). Choices are
written to `/tmp` under the names listed in `usr/lib/biglinux-livecd/live-state`,
which is the single place that maps a setting to its file. Calamares copies them
into `/etc/big-default-config` so the installed system starts as the live session
was left.

**Installer integration.** `calamares-biglinux` is the wrapper that launches
Calamares with the right profile and environment, and
`/usr/share/biglinux/calamares` is the GTK wizard that collects the installation
options before it starts.

**Calamares profiles** for the three products built from this base — `biglinux`,
`bigcommunity` and `xivastudio` — each with its own `settings.conf`, module
configuration and branding.

**Calamares modules** under `usr/lib/calamares/modules`:

| Module | Purpose |
|---|---|
| `btrfs-fix` | Applies the Btrfs layout and mount options the installed system expects |
| `grubcfg-fix` | Adjusts the generated GRUB configuration |
| `luks-pbkdf` | Lowers the Argon2id cost of the volume GRUB unlocks, so the passphrase prompt answers quickly |

## Live profiles

The active profile is named in `/etc/biglinux-livecd/profile`, which must be a
regular root-owned file. `resolve-profile` reads it and returns the profile
directory, preferring `/etc/biglinux-livecd/calamares-profiles` over the ones
shipped in `/usr/share/biglinux/calamares-profiles`, so an image can override a
profile without replacing this package. Without the marker the profile is
`biglinux`.

## Kernel arguments

Recognised on the live media's boot line:

| Argument | Effect |
|---|---|
| `biglinux.bootcmd=<command>` | Skips the normal flow. Accepts `only-calamares`, `boot-in-plasma`, `only-konsole`, `calamares_polkit`, `konsole`, `urxvt` and `startplasma-x11` |
| `driver=nonfree` | Installs the runtime mkinitcpio shim for proprietary drivers |
| `driver=free` | Disables proprietary driver detection |
| `wayland` | Starts the session under Wayland |
| `sshenable` | Enables the live SSH server for recovery |

These arguments are dropped from the command line written to the installed
system, so a choice made to get through the live session is not inherited.

### sshenable

Useful when a machine cannot be operated locally — a failing boot, or a display
that does not come up. It sets a temporary password on the existing UID 1000
user, whose name is read from `/etc/passwd` and is usually `biglinux`, and adds a
runtime drop-in to `sshd_config` allowing password authentication for that user
only. The password is `big`, `PermitRootLogin` stays `no`, and no account is
created or otherwise modified.

```bash
ssh <live-user>@<live-address>
```

The password is public, so this is for a trusted local network and never for a
machine reachable from the Internet. Everything is in effect only while the live
session runs: reboot without the argument and nothing remains, and nothing is
written to the installed system.

## Repository layout

```
biglinux-livecd/         files installed on the system, mirroring their paths
  locale/                gettext catalogs, compiled at package time
  usr/bin/               live session entry points and installer wrappers
  usr/lib/biglinux-livecd/   shared shell helpers: kernel-options, live-state
  usr/lib/calamares/modules/ Calamares job modules
  usr/share/biglinux/livecd/     setup wizard
  usr/share/biglinux/calamares/  installer wizard
  usr/share/biglinux/calamares-profiles/  per-product Calamares profiles
  usr/share/calamares/branding/  QML branding for the installer
pkgbuild/                PKGBUILD and install scriptlet
tests/                   test suite
```

## Development

Requires an Arch or Manjaro based system, Python 3.11 or newer, and GTK4 with
libadwaita.

```bash
python -m pytest tests/      # test suite
ruff check                   # lint
ruff format                  # formatter used by this project
```

The test suite is the quality gate. Besides covering behaviour, it type-checks
the Calamares modules and the two wizards by running `mypy` against each entry
point in the isolation Calamares itself uses — a plugin is loaded as a standalone
module named `main`, so checking them together reports false duplicates. Adding a
module means adding it to the list in `tests/test_mypy_plugins.py`; a test fails
if an entry point is left out.

Shell scripts are checked with `shellcheck` and `shfmt -d`, syntax-checked with
the interpreter each one declares — most are `bash`, a few are POSIX `sh`.

Building the package:

```bash
cd pkgbuild
makepkg -si
```

`makepkg` builds from the published git repository, not from the working tree.
To try local changes, copy them into a live session or install the built package
over an existing one.

## Translations

Sources are the `.po` files in `biglinux-livecd/locale`, compiled by the PKGBUILD
into `/usr/share/locale`. `msgfmt --check-format` runs during the build, so a
catalog whose placeholders do not match its source fails the package rather than
the running program.

## License

GPL-3.0-only, with CC0-1.0 material. See [LICENSE](LICENSE).
