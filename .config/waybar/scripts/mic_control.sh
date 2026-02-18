#!/bin/bash

# Configuration
APP_NAME="MicVolume"
ICON="󰔊" # Microphone icon

# Get current default source ID and volume
# Using wpctl to get the default source
SOURCE_ID=$(wpctl status | grep -A 5 "Sources:" | grep "*" | awk '{print $2}' | tr -d '.')

if [ -z "$SOURCE_ID" ]; then
    # Fallback: get first available source if none is marked default
    SOURCE_ID=$(wpctl status | grep -A 5 "Sources:" | grep -E "[0-9]+\." | head -n 1 | awk '{print $1}' | tr -d '.')
fi

case $1 in
    up)
        wpctl set-volume "$SOURCE_ID" 5%+
        ;;
    down)
        wpctl set-volume "$SOURCE_ID" 5%-
        ;;
    mute)
        wpctl set-mute "$SOURCE_ID" toggle
        ;;
esac

# Get new volume state
VOLUME=$(wpctl get-volume "$SOURCE_ID" | awk '{print $2}')
# Convert 0.XX to percentage
VOL_PCT=$(echo "$VOLUME * 100" | bc | cut -d'.' -f1)
MUTE_STATE=$(wpctl get-volume "$SOURCE_ID" | grep "MUTED")

if [ -n "$MUTE_STATE" ]; then
    notify-send -a "$APP_NAME" -h string:x-dunst-stack-tag:mic_vol -i "mic-off" "Micrófono Silenciado" -h int:value:0
else
    # Show the bar using Dunst progress capability
    notify-send -a "$APP_NAME" \
                -h string:x-dunst-stack-tag:mic_vol \
                -h int:value:"$VOL_PCT" \
                "$ICON  Micrófono: $VOL_PCT%"
fi
