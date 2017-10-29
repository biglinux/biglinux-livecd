/usr/bin/bigbashview -s $(LANG=C xdpyinfo  | grep 'dimensions:' | sed 's|.*dimensions:||g;s| pixels.*||g') /usr/share/bigbashview/bcc/apps/boot-livecd/index.sh.htm
chmod +x /tmp/biglightdm
/tmp/biglightdm
