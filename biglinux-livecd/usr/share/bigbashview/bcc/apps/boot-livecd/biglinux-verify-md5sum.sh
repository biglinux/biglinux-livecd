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
Error=$"Erro."
MessageFinish=$"O sistema passou no teste de integridade."

if [ ! -e $FileVerified ]; then

    rm -f $File
    cd /run/miso/bootmnt/manjaro/x86_64/
    #cd /home/biglinux/x86_64/

    Message=$"Verificando a integridade do sistema:"
    
    echo '<script>$( function() {$( "#progressbar").progressbar({value: 15});} );$( function() {$("#textprogress").text("'$Message' 15%");} );$(".ui-widget-header").css("background", "#2196f3");</script>' > $File
    md5sum --status -c desktopfs.md5

    if [ "$?" != "0" ] ; then
        echo '<script>$( function() {$( "#progressbar").progressbar({value: 100});} );$( function() {$("#textprogress").text("'$Error'");} );$(".ui-widget-header").css("background", "red"); </script>' > $File
        ./erro.sh
        exit
    fi

    echo '<script>$( function() {$( "#progressbar").progressbar({value: 35});} );$( function() {$("#textprogress").text("'$Message' 35%");} );$(".ui-widget-header").css("background", "#2196f3");</script>' > $File
    md5sum --status -c livefs.md5
    if [ "$?" != "0" ] ; then
        echo '<script>$( function() {$( "#progressbar").progressbar({value: 100});} );$( function() {$("#textprogress").text("'$Error'");} );$(".ui-widget-header").css("background", "red"); </script>' > $File
        ./erro.sh
        exit
    fi

    echo '<script>$( function() {$( "#progressbar").progressbar({value: 50});} );$( function() {$("#textprogress").text("'$Message' 50%");} );$(".ui-widget-header").css("background", "#2196f3");</script>' > $File
    md5sum --status -c mhwdfs.md5
    if [ "$?" != "0" ] ; then
        echo '<script>$( function() {$( "#progressbar").progressbar({value: 100});} );$( function() {$("#textprogress").text("'$Error'");} );$(".ui-widget-header").css("background", "red"); </script>' > $File
        ./erro.sh
        exit
    fi

    echo '<script>$( function() {$( "#progressbar").progressbar({value: 75});} );$( function() {$("#textprogress").text("'$Message' 75%");} );$(".ui-widget-header").css("background", "#2196f3");</script>' > $File
    md5sum --status -c rootfs.md5
    if [ "$?" != "0" ] ; then
        echo '<script>$( function() {$( "#progressbar").progressbar({value: 100});} );$( function() {$("#textprogress").text("'$Error'");} );$(".ui-widget-header").css("background", "red"); </script>' > $File
        ./erro.sh
        exit
    fi
    
    echo '<script>$( function() {$( "#progressbar").progressbar({value: 90});} );$( function() {$("#textprogress").text("'$Message' 90%");} );$(".ui-widget-header").css("background", "#2196f3");</script>' > $File
    sleep 2  
fi

echo '<script>
$( function() {$( "#progressbar").progressbar({value: 100});} );
$( function() {$("#textprogress").text("'$MessageFinish'");} );
$(".ui-widget-header").css("background", "#2196f3");
</script>' > $File    

echo 1 > $FileVerified
