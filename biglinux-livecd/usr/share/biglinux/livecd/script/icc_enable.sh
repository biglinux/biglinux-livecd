#!/bin/bash

jaq -i 'map(
  if .data then
    .data |= map(
      if has("edidHash") then
        .iccProfilePath = "/usr/share/color/icc/colord/ECI-RGBv1.icc"
        | .colorProfileSource = "ICC"
      else
        .
      end
    )
  else
    .
  end
)' ~/.config/kwinoutputconfig.json
