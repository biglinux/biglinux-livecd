<div align="center">

# 🚀 BigLinux LiveCD

**The Ultimate Live Environment & Installer for BigLinux**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg?style=for-the-badge)](LICENSE)
[![Arch Linux](https://img.shields.io/badge/BigLinux-1793D1?style=for-the-badge&logo=biglinux&logoColor=white)](https://www.biglinux.com.br/)
[![GTK4](https://img.shields.io/badge/GTK4-Libadwaita-4A86CF?style=for-the-badge&logo=gtk&logoColor=white)](https://gtk.org/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Supported Variants](#-supported-variants)
- [Boot Commands](#-custom-boot-commands-grub)
- [Development](#-development)
- [License](#-license)

---

## 📋 Overview

The **biglinux-livecd** package serves as the backbone of the BigLinux live experience. It orchestrates everything from the initial boot sequence to the final installation on the user's machine.

Upon booting, users are welcomed by a polished setup wizard (built with GTK4/Libadwaita) that allows for immediate personalization of the live session—settings that are seamlessly preserved after installation.

---

## 🚀 Key Features

- **Intuitive Setup Wizard**: Configure language, keyboard, and theme before you even reach the desktop.
- **Seamless Migration**: All settings chosen in the live environment are automatically carried over to the installed system.
- **Smart Hardware Detection**: Automatically enables enhancements like **JamesDSP** for audio and ICC profiles for displays.
- **Unified Installer**: Includes `calamares-biglinux`, a customized version of the Calamares installer tailored for BigLinux.

---

## 🏗️ Architecture

The configuration flow ensures a smooth transition from live media to permanent installation:

```mermaid
graph TD
    A[Live Boot] --> B[biglinux-livecd wizard]
    B --> C{User Config}
    C -->|Atomic writes| D["/tmp/big_* state"]
    D --> E[Calamares Installer]
    E -->|Copies| F["/etc/big-default-config/"]
    F --> G[First System Boot]
    G --> H[User Session Applied]
```

### Configuration Storage

The wizard writes state files to `/tmp` during the live session. On install,
`biglinux-install-setup.sh` copies them into `/etc/big-default-config/`, renaming
each one. A missing file means "not selected": `copy_live_config` skips it.

| Live session | Installed system | Description |
|---|---|---|
| `/tmp/big_language` | applied directly | System locale (for example, `pt_BR`) |
| `/tmp/big_keyboard` | `kxkbrc`, `fcitx5/` | Keyboard model and layout |
| `/tmp/big_desktop_theme` | `theme` | Selected visual theme |
| `/tmp/big_desktop_changed` | `desktop` | Desktop layout preset |
| `/tmp/big_gnome_layout` | `gnome-layout` | GNOME layout preset |
| `/tmp/big_gnome_settings` | `gnome-settings` | GNOME dconf settings |
| `/tmp/big_enable_jamesdsp` | `jamesdsp` | Audio enhancement state |
| `/tmp/big_improve_display` | `display-profile` | ICC colour profile state |

`/run/biglinux-live/` is a different directory, used only by the Calamares and
integrity helpers — not for the wizard's choices.

See [LIVE-STATE.md](LIVE-STATE.md) for the complete producer, consumer, safety,
and lifecycle contract.

---

## 📁 Project Structure

This repository is organized to separate the live session logic from the installer components:

```tree
biglinux-livecd/
├── pkgbuild/                 # Arch Linux packaging files
├── locale/                   # Translations (.po files)
└── biglinux-livecd/usr/
    ├── bin/
    │   ├── startbiglive      # Main entry point for live session
    │   └── calamares-biglinux # Installer wrapper script
    ├── share/biglinux/
    │   ├── livecd/           # Setup Wizard Source (Python/GTK4)
    │   └── calamares/        # Installer UI Source
    └── lib/calamares/        # Custom Calamares modules
```

---

## 🎯 Supported Variants

BigLinux supports multiple desktop environments, automatically detected by the live system:

| Variant | Detection Trigger |
|---------|-------------------|
| **BigLinux (KDE)** | Default fallback |
| **XivaStudio (KDE)** | Default fallback |
| **Community GNOME** | `/usr/bin/startgnome-community` |
| **Community Cinnamon** | `/usr/bin/startcinnamon-community` |
| **Community XFCE** | `/usr/bin/startxfce-community` |

---

## 🔧 Custom Boot Commands (GRUB)

For advanced users and debugging, you can bypass the standard flow using the `biglinux.bootcmd` kernel parameter.

**Example:**
```bash
linux /vmlinuz-linux ... biglinux.bootcmd=only-calamares
```

| Command | Action |
|---------|--------|
| `boot-in-plasma` | Skip wizard, go straight to desktop |
| `only-calamares` | Launch installer directly (minimal mode) |
| `only-konsole` | Launch terminal only (rescue mode) |

---

## 🛠️ Development

### Prerequisites

- Arch Linux or Manjaro based system
- `makepkg` toolchain
- Python 3.12+ and GTK4 development libraries

### Build & Install

```bash
cd pkgbuild
makepkg -si
```

### Testing the UI

Run the setup wizard in a windowed mode for rapid iteration:

```bash
# Preview via Broadway (Web)
gtk4-broadwayd :5 &
GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 python3 /usr/share/biglinux/livecd/main.py
# Open http://localhost:8085
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the **GPL-3.0 License**. See [LICENSE](LICENSE) for more information.

---

<div align="center">

**Made with 💚 by the BigLinux Team**

[Website](https://biglinux.com.br)

</div>
