#!/bin/bash

# Script to handle smart app focus/launch
# Usage: focus_or_launch.sh <class> <command>

CLASS=$1
COMMAND=$2

# Check if application is already running
# We use hyprctl to check for the window class
WINDOW_INFO=$(hyprctl clients -j | jq -r ".[] | select(.class == \"$CLASS\")")

if [ -n "$WINDOW_INFO" ]; then
    # App is running, get its workspace and switch to it
    TARGET_WS=$(echo "$WINDOW_INFO" | jq -r '.workspace.id')
    echo "App $CLASS found on workspace $TARGET_WS. Switching..." >> /tmp/focus_debug.log
    hyprctl dispatch workspace "$TARGET_WS"
    hyprctl dispatch focuswindow class:"$CLASS"
else
    # App is not running, find the first empty workspace
    echo "App $CLASS not running. Finding empty workspace..." >> /tmp/focus_debug.log
    ACTIVE_WORKSPACES=$(hyprctl workspaces -j | jq -r '.[].id' | sort -n)
    
    TARGET_WS=1
    while echo "$ACTIVE_WORKSPACES" | grep -q "^$TARGET_WS$"; do
        TARGET_WS=$((TARGET_WS + 1))
    done
    
    echo "Launching $COMMAND on workspace $TARGET_WS" >> /tmp/focus_debug.log
    hyprctl dispatch exec "[workspace $TARGET_WS] $COMMAND"
fi
