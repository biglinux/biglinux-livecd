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

TITLE=$"Erro: Falha na verificação de integridade"
HEADING="Oops!"
BODY=$"Integrity check failed, it is necessary to download the system again or use another USB drive."
ERROR_CODE="ERROR: checksum fail"
BUTTON_TEXT=$"Close"

WAYLAND_DISPLAY= yad --title="$TITLE" \
    --window-icon=dialog-error \
    --image=icon-crash.svg \
    --text-align=left \
    --width=650 \
    --on-top \
    --margins=180 \
    --button="$BUTTON_TEXT:1" \
    --text="<span size='xx-large' weight='bold'>${HEADING}</span>\n\n${BODY}\n\n<tt>${ERROR_CODE}</tt>"
