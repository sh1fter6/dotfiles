#!/bin/bash

# Ultra-fast OSD Script using shell + awk (no Python overhead)
# Usage: osd.sh [vol|mic|br] [up|down|mute]

TYPE=$1
ACTION=$2
APP_NAME="SystemOSD"
TAG="osd_notification"

case $TYPE in
    vol)
        TARGET="@DEFAULT_AUDIO_SINK@"
        ICON="󰕾"
        [ "$ACTION" == "up" ] && wpctl set-volume "$TARGET" 5%+
        [ "$ACTION" == "down" ] && wpctl set-volume "$TARGET" 5%-
        [ "$ACTION" == "mute" ] && wpctl set-mute "$TARGET" toggle
        
        INFO=$(wpctl get-volume "$TARGET")
        # Extract only the first numeric value found to avoid multi-line issues
        PCT=$(echo "$INFO" | grep -oP "[\d.]+" | head -n 1 | awk '{print int($1 * 100)}')
        [ -n "$(echo "$INFO" | grep "MUTED")" ] && { ICON="󰝟"; TITLE="Silenciado"; PCT=0; } || TITLE="Volumen: $PCT%"
        ;;
        
    mic)
        TARGET="@DEFAULT_AUDIO_SOURCE@"
        ICON="󰔊"
        [ "$ACTION" == "up" ] && wpctl set-volume "$TARGET" 5%+
        [ "$ACTION" == "down" ] && wpctl set-volume "$TARGET" 5%-
        [ "$ACTION" == "mute" ] && wpctl set-mute "$TARGET" toggle
        
        INFO=$(wpctl get-volume "$TARGET")
        PCT=$(echo "$INFO" | grep -oP "[\d.]+" | head -n 1 | awk '{print int($1 * 100)}')
        [ -n "$(echo "$INFO" | grep "MUTED")" ] && { ICON="󰍭"; TITLE="Mudo"; PCT=0; } || TITLE="Micro: $PCT%"
        ;;
        
    br)
        ICON="󰃠"
        [ "$ACTION" == "up" ] && brightnessctl set 5%+ > /dev/null
        [ "$ACTION" == "down" ] && brightnessctl set 5%- > /dev/null
        
        PCT=$(brightnessctl -m | cut -d, -f4 | tr -d '%')
        TITLE="Brillo: $PCT%"
        ;;
esac

# Ensure PCT is a valid number
[[ ! "$PCT" =~ ^[0-9]+$ ]] && PCT=0

# Clear any previous notification stuck in memory with this tag
dunstctl close-all

# Send fresh notification
notify-send -a "$APP_NAME" \
            -h string:x-dunst-stack-tag:"$TAG" \
            -h int:value:"$PCT" \
            "$ICON  $TITLE"
