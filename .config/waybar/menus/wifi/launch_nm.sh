#!/bin/bash

nmcli device wifi rescan > /dev/null 2>&1 &


python3 /home/sh1fter/.config/waybar/menus/wifi/network_manager_custom.py
