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

if [[ $(pgrep -c biglinux-verify) > 1 ]]; then
    exit
fi

if [[ -e /tmp/big_language ]]; then
    export LANGUAGE=$(</tmp/big_language).UTF-8
    export LANG=$(</tmp/big_language).UTF-8
fi

#Translation
export TEXTDOMAINDIR="/usr/share/locale"
export TEXTDOMAIN=biglinux-livecd

FileVerified="/tmp/checksum_biglinux_ok.html"
ScriptFolder="${0%/*}"

if [ ! -e $FileVerified ]; then

    ###### Detecting folder with files
    # Try with manjaro folder
    if [[ -e /run/miso/bootmnt/manjaro/x86_64/ ]]; then
        cd /run/miso/bootmnt/manjaro/x86_64/
    
    # Try with folder same as HOSTNAME
    elif [[ -e /run/miso/bootmnt/$HOSTNAME/x86_64/ ]]; then
        cd /run/miso/bootmnt/$HOSTNAME/x86_64/
    
    # Try folder removing efi and boot folder
    elif [[ -e $(ls -d1 /run/miso/bootmnt/*/ | grep -ve '/efi/' -ve '/boot/') ]]; then
        cd $(ls -d1 /run/miso/bootmnt/*/ | grep -ve '/efi/' -ve '/boot/')
    fi
    ######

    md5sum --status -c desktopfs.md5
    if [ "$?" != "0" ] ; then
        cd "$ScriptFolder"
        ./md5error.sh
        exit
    fi

    md5sum --status -c livefs.md5
    if [ "$?" != "0" ] ; then
        cd "$ScriptFolder"
        ./md5error.sh
        exit
    fi

    md5sum --status -c mhwdfs.md5
    if [ "$?" != "0" ] ; then
        cd "$ScriptFolder"
        ./md5error.sh
        exit
    fi

    md5sum --status -c rootfs.md5
    if [ "$?" != "0" ] ; then
        cd "$ScriptFolder"
        ./md5error.sh
        exit
    fi
fi

echo 1 > $FileVerified
