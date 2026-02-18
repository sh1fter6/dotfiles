#!/bin/bash


if swaync-client -D | grep -q "true"; then
    echo "󰂛"
else
    echo "󰂚"
fi
