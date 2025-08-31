#!/bin/bash
xset -dpms     # disable DPMS (energy saving)
xset s off     # disable screen saver
xset s noblank # disable blanking
unclutter -idle 30 -root & # hide mouse cursor after 30 seconds of inactivity
xrandr -o left # rotate screen to the left
DISPLAY=:0 xinput set-prop "WaveShare WS170120" --type=float "Coordinate Transformation Matrix" 0 -1 1 1 0 0 0 0 1 # flip display vertically so touch coordinates are correct for rotated display
chromium-browser --force-device-scale-factor=1 --noerrdialogs --disable-infobars --no-memcheck --kiosk file:///home/jim/kiosk_loader.html # start Chromium in kiosk mode