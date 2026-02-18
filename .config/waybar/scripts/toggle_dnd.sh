#!/bin/bash


swaync-client -d


if swaync-client -D | grep -q "true"; then
    echo "󰂛"
else
    echo "󰂚"
fi
