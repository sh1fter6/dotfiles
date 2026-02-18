#!/bin/bash

(
  bluetoothctl scan on
) &
SCAN_PID=$!


python3 /home/sh1fter/.config/waybar/menus/bluetooth/bluetooth_menu.py


kill $SCAN_PID 2>/dev/null
bluetoothctl scan off 2>/dev/null
