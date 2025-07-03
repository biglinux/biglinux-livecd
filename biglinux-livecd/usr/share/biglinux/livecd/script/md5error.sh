#!/bin/bash
##################################
#  Author1: Bruno Goncalves (www.biglinux.com.br) 
#  Author2: Rafael Ruscher (rruscher@gmail.com)  
#  Date:    2022/08/19
#  
#  Description: Control Center to help usage of BigLinux 
#  
# Licensed by GPL V2 or greater
##################################


if [[ -e /tmp/big_language ]]; then
    export LANGUAGE=$(</tmp/big_language).UTF-8
    export LANG=$(</tmp/big_language).UTF-8
fi

#Translation
export TEXTDOMAINDIR="/usr/share/locale"
export TEXTDOMAIN=biglinux-livecd


TITLE=$"Error: Integrity Check Failed"
ICON_NAME="dialog-error"
HEADING=$"Oops!"
BODY=$"The integrity check failed. It is necessary to download the system again or use another USB drive."
EXPLANATION=$"<b>Why?</b> Think of the installation file as a precise digital package. This error means the package was damaged during download, or the USB drive itself is faulty and is damaging the file."
ERROR_CODE="ERROR: checksum fail"
BUTTON_TEXT=$"Close"


TEXT_CONTENT="<span size='28000' weight='bold' foreground='#d32f2f'>⚠ $HEADING</span>\n\n"
TEXT_CONTENT+="<span size='14000' >$BODY</span>\n\n"
TEXT_CONTENT+="<span size='12000' style='italic' >$EXPLANATION</span>\n\n"
TEXT_CONTENT+="<span font_family='monospace'"
TEXT_CONTENT+="foreground='#c62828'"
TEXT_CONTENT+="size='14000'> 🔍 $ERROR_CODE </span>"

# --- Modern YAD Dialog with Enhanced Design ---
WAYLAND_DISPLAY= yad --title="$TITLE" \
    --window-icon="$ICON_NAME" \
    --width=640 \
    --borders=20 \
    --center \
    --on-top \
    --text="$TEXT_CONTENT" \
    --text-width=40 \
    --text-align=center \
    --button="$BUTTON_TEXT!gtk-close:0"
