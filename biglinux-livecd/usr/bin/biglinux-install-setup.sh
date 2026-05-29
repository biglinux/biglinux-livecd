#!/bin/bash
#===============================================================================
# Script Name: biglinux-install-setup.sh
# Description: BigLinux Post-Installation Configuration
#              Called by Calamares grubcfg-fix module after installation.
#              Configures GRUB, SDDM session, and migrates live session
#              settings (theme, desktop, JamesDSP, display profile).
# Package:     biglinux-livecd
#
# Usage: biglinux-install-setup.sh <root_mount_point>
#===============================================================================

#-------------------------------------------------------------------------------
# Validate Arguments
#-------------------------------------------------------------------------------
ROOT_MOUNT="$1"
if [[ -z "$ROOT_MOUNT" ]] || [[ ! -d "$ROOT_MOUNT" ]]; then
    echo "Error: Invalid root mount point: $ROOT_MOUNT"
    exit 1
fi

# Define paths relative to root mount point
GRUB_FILE="$ROOT_MOUNT/etc/default/grub"
SDDM_STATE="$ROOT_MOUNT/var/lib/sddm/state.conf"
CONFIG_DIR="$ROOT_MOUNT/etc/big-default-config"

#-------------------------------------------------------------------------------
# Configure GRUB Bootloader
#-------------------------------------------------------------------------------
if [[ -f "$GRUB_FILE" ]]; then
    # Add kernel command line parameters from live session (cleaned)
    sed -i "s|GRUB_CMDLINE_LINUX_DEFAULT='|GRUB_CMDLINE_LINUX_DEFAULT='$(sed 's|BOOT_IMAGE=/boot/vmlinuz-x86_64 ||g;s| driver=nonfree||g;s| driver=free||g;s| rdinit=/vtoy/vtoy||g;s| quiet splash||g' /proc/cmdline) |g" "$GRUB_FILE"

    # Remove live boot specific entries
    sed -i 's|BOOT_IMAGE=/boot/vmlinuz-x86_64||g;s|misobasedir=manjaro misolabel=BIGLINUXLIVE ||g' "$GRUB_FILE"

    # Disable GRUB savedefault and fix duplicate quiet
    sed -i 's|GRUB_SAVEDEFAULT=true|GRUB_SAVEDEFAULT=false|g;s|quiet quiet|quiet|g' "$GRUB_FILE"

    # Add GRUB_EARLY_INITRD_LINUX_STOCK if not present
    if ! grep -q GRUB_EARLY_INITRD_LINUX_STOCK "$GRUB_FILE"; then
        echo "GRUB_EARLY_INITRD_LINUX_STOCK=''" >> "$GRUB_FILE"
    fi

    # Remove duplicate splash parameters
    while [[ "$(grep -o '[^[:space:]]*splash[^[:space:]]*' "$GRUB_FILE" | sed 's/\"//' | wc -w)" -gt "1" ]]; do
        sed -i 's/ splash//' "$GRUB_FILE"
    done

    # Remove duplicate quiet parameters
    while [[ "$(grep -o '[^[:space:]]*quiet[^[:space:]]*' "$GRUB_FILE" | sed 's/\"//' | wc -w)" -gt "1" ]]; do
        sed -i 's/ quiet//' "$GRUB_FILE"
    done
fi

#-------------------------------------------------------------------------------
# Configure SDDM Session (Wayland vs X11)
#-------------------------------------------------------------------------------
mkdir -p "$(dirname "$SDDM_STATE")"
if grep -q wayland /proc/cmdline; then
    echo "[Last]
    Session=/usr/share/wayland-sessions/plasmawayland.desktop" > "$SDDM_STATE"
else
    echo "[Last]
    Session=/usr/share/xsessions/plasma.desktop" > "$SDDM_STATE"
fi

#-------------------------------------------------------------------------------
# Migrate Live Session Configuration to Installed System
#-------------------------------------------------------------------------------
mkdir -p "$CONFIG_DIR"

# Copy theme config if exists
[[ -f "/tmp/big_desktop_theme" ]] && cp -f "/tmp/big_desktop_theme" "$CONFIG_DIR/theme"

# Copy desktop config if exists
[[ -f "/tmp/big_desktop_changed" ]] && cp -f "/tmp/big_desktop_changed" "$CONFIG_DIR/desktop"
[[ -f "/tmp/big_gnome_layout" ]] && cp -f "/tmp/big_gnome_layout" "$CONFIG_DIR/gnome-layout"

# Copy GNOME layout settings if exists
if [[ -f "/tmp/big_gnome_settings" ]]; then
    cp -f "/tmp/big_gnome_settings" "$CONFIG_DIR/gnome-settings"

    mkdir -p "$ROOT_MOUNT/etc/skel/.config/dconf"
    cp -f "/tmp/big_gnome_settings" "$ROOT_MOUNT/etc/skel/.config/dconf/settings.gnome"

    for USER_HOME in "$ROOT_MOUNT"/home/*; do
        [[ -d "$USER_HOME" ]] || continue

        USER_NAME="$(basename "$USER_HOME")"
        USER_SETTINGS_DIR="$USER_HOME/.config/dconf"
        USER_SETTINGS_FILE="$USER_SETTINGS_DIR/settings.gnome"

        mkdir -p "$USER_SETTINGS_DIR"
        cp -f "/tmp/big_gnome_settings" "$USER_SETTINGS_FILE"

        if [[ -f "$ROOT_MOUNT/etc/passwd" ]]; then
            USER_IDS="$(awk -F: -v user="$USER_NAME" '$1 == user { print $3 ":" $4 }' "$ROOT_MOUNT/etc/passwd")"
            if [[ -n "$USER_IDS" ]]; then
                chown "$USER_IDS" "$USER_HOME/.config" "$USER_SETTINGS_DIR" "$USER_SETTINGS_FILE" 2>/dev/null || true
            fi
        fi
    done
fi

# Copy JamesDSP flag if exists
[[ -f "/tmp/big_enable_jamesdsp" ]] && cp -f "/tmp/big_enable_jamesdsp" "$CONFIG_DIR/jamesdsp"

# Copy display profile flag if exists
[[ -f "/tmp/big_improve_display" ]] && cp -f "/tmp/big_improve_display" "$CONFIG_DIR/display-profile"

echo "BigLinux installation setup completed successfully"
