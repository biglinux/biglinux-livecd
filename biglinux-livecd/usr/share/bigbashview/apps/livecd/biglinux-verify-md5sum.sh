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

export LANGUAGE=$(cat /tmp/big_language).UTF-8
export LANG=$(cat /tmp/big_language).UTF-8

#Translation
export TEXTDOMAINDIR="/usr/share/locale"
export TEXTDOMAIN=biglinux-livecd

File="/tmp/checksum_biglinux.html"
FileVerified="/tmp/checksum_biglinux_ok.html"

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

    rm -f $File

    md5sum --status -c desktopfs.md5
    if [ "$?" != "0" ] ; then
        ./md5error.sh
        exit
    fi

    md5sum --status -c livefs.md5
    if [ "$?" != "0" ] ; then
        ./md5error.sh
        exit
    fi

    md5sum --status -c mhwdfs.md5
    if [ "$?" != "0" ] ; then
        ./md5error.sh
        exit
    fi

    md5sum --status -c rootfs.md5
    if [ "$?" != "0" ] ; then
        ./md5error.sh
        exit
    fi
fi

echo 1 > $FileVerified
