#!/bin/bash
#===============================================================================
# Script Name: biglinux-install-setup.sh
# Description: BigLinux Post-Installation Configuration
#              Called by Calamares grubcfg-fix module after installation.
#              Configures GRUB, display manager session, and migrates live
#              session settings (theme, desktop, JamesDSP, display profile).
# Package:     biglinux-livecd
#
# Supported Desktop Environments:
#   - KDE Plasma (SDDM)
#   - GNOME (GDM)
#   - Cinnamon (LightDM)
#   - XFCE (LightDM)
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
CONFIG_DIR="$ROOT_MOUNT/etc/big-default-config"

#-------------------------------------------------------------------------------
# Detect Desktop Environment
#-------------------------------------------------------------------------------
detect_desktop_environment() {
    if [[ -e "$ROOT_MOUNT/usr/bin/startplasma-x11" ]] || [[ -e "$ROOT_MOUNT/usr/share/xsessions/plasma.desktop" ]]; then
        echo "plasma"
    elif [[ -e "$ROOT_MOUNT/usr/bin/gnome-session" ]] || [[ -e "$ROOT_MOUNT/usr/bin/startgnome-community" ]]; then
        echo "gnome"
    elif [[ -e "$ROOT_MOUNT/usr/bin/cinnamon-session" ]] || [[ -e "$ROOT_MOUNT/usr/bin/startcinnamon-community" ]]; then
        echo "cinnamon"
    elif [[ -e "$ROOT_MOUNT/usr/bin/startxfce4" ]] || [[ -e "$ROOT_MOUNT/usr/bin/startxfce-community" ]]; then
        echo "xfce"
    else
        echo "unknown"
    fi
}

DESKTOP_ENV=$(detect_desktop_environment)
echo "Detected desktop environment: $DESKTOP_ENV"

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
# Configure Display Manager Session
# Sets the default session based on desktop environment and session type
#-------------------------------------------------------------------------------
configure_display_manager_session() {
    local is_wayland=false
    grep -q wayland /proc/cmdline && is_wayland=true

    case "$DESKTOP_ENV" in
        plasma)
            # KDE Plasma uses SDDM
            local sddm_state="$ROOT_MOUNT/var/lib/sddm/state.conf"
            mkdir -p "$(dirname "$sddm_state")"
            if $is_wayland; then
                echo "[Last]
Session=/usr/share/wayland-sessions/plasmawayland.desktop" > "$sddm_state"
            else
                echo "[Last]
Session=/usr/share/xsessions/plasma.desktop" > "$sddm_state"
            fi
            echo "Configured SDDM for Plasma ($($is_wayland && echo 'Wayland' || echo 'X11'))"
            ;;

        gnome)
            # GNOME uses GDM
            local gdm_custom="$ROOT_MOUNT/etc/gdm/custom.conf"
            mkdir -p "$(dirname "$gdm_custom")"
            if $is_wayland; then
                # Enable Wayland for GDM
                cat > "$gdm_custom" << 'EOF'
[daemon]
WaylandEnable=true
DefaultSession=gnome.desktop

[security]

[xdmcp]

[chooser]

[debug]
EOF
            else
                # Force X11 for GDM
                cat > "$gdm_custom" << 'EOF'
[daemon]
WaylandEnable=false
DefaultSession=gnome-xorg.desktop

[security]

[xdmcp]

[chooser]

[debug]
EOF
            fi
            echo "Configured GDM for GNOME ($($is_wayland && echo 'Wayland' || echo 'X11'))"
            ;;

        cinnamon)
            # Cinnamon uses LightDM (X11 only)
            local lightdm_conf="$ROOT_MOUNT/etc/lightdm/lightdm.conf.d/50-biglinux.conf"
            mkdir -p "$(dirname "$lightdm_conf")"
            cat > "$lightdm_conf" << 'EOF'
[Seat:*]
user-session=cinnamon
EOF
            echo "Configured LightDM for Cinnamon"
            ;;

        xfce)
            # XFCE uses LightDM (X11 only)
            local lightdm_conf="$ROOT_MOUNT/etc/lightdm/lightdm.conf.d/50-biglinux.conf"
            mkdir -p "$(dirname "$lightdm_conf")"
            cat > "$lightdm_conf" << 'EOF'
[Seat:*]
user-session=xfce
EOF
            echo "Configured LightDM for XFCE"
            ;;

        *)
            echo "Warning: Unknown desktop environment, skipping display manager configuration"
            ;;
    esac
}

configure_display_manager_session

#-------------------------------------------------------------------------------
# Migrate Live Session Configuration to Installed System
#-------------------------------------------------------------------------------
mkdir -p "$CONFIG_DIR"

# KDE Plasma specific configs
if [[ "$DESKTOP_ENV" == "plasma" ]]; then
    # Copy theme config if exists (KDE themes like Breeze, etc)
    [[ -f "/tmp/big_desktop_theme" ]] && cp -f "/tmp/big_desktop_theme" "$CONFIG_DIR/theme"

    # Copy desktop layout config if exists (KDE panel layouts)
    [[ -f "/tmp/big_desktop_changed" ]] && cp -f "/tmp/big_desktop_changed" "$CONFIG_DIR/desktop"
fi

# GNOME/Cinnamon/XFCE specific configs (simplified theme: light/dark)
if [[ "$DESKTOP_ENV" == "gnome" ]] || [[ "$DESKTOP_ENV" == "cinnamon" ]] || [[ "$DESKTOP_ENV" == "xfce" ]]; then
    # Copy simple theme selection (light/dark)
    [[ -f "/tmp/big_simple_theme" ]] && cp -f "/tmp/big_simple_theme" "$CONFIG_DIR/simple-theme"
fi

# Common configs for all desktop environments
# Copy JamesDSP flag if exists
[[ -f "/tmp/big_enable_jamesdsp" ]] && cp -f "/tmp/big_enable_jamesdsp" "$CONFIG_DIR/jamesdsp"

# Copy display profile/ICC flag if exists
[[ -f "/tmp/big_improve_display" ]] && cp -f "/tmp/big_improve_display" "$CONFIG_DIR/display-profile"

echo "BigLinux installation setup completed successfully for $DESKTOP_ENV"
