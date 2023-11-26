#!/usr/bin/env bash

# Check the session type and move to the appropriate directory
if [ "$XDG_SESSION_TYPE" = "x11" ]; then
  /usr/bin/bigbashview -s $(LANG=C xdpyinfo  | grep 'dimensions:' | sed 's|.*dimensions:||g;s| pixels.*||g') /usr/share/bigbashview/bcc/apps/boot-livecd/index.sh.htm
  chmod +x /tmp/biglightdm
  /tmp/biglightdm
elif [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    /usr/bin/bigbashview -w fullscreen /usr/share/bigbashview/bcc/apps/boot-livecd/index.sh.htm
    chmod +x /tmp/biglightdm
    /tmp/biglightdm
fi
