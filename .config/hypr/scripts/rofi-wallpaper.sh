#!/bin/bash
wall_dir="$HOME/Pictures/Wallpapers"
selected=$(find "$wall_dir" -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.jpeg" -o -iname "*.webp" \) -exec basename {} \; | sort | wofi --dmenu --prompt "Fondo de Pantalla")
if [ -n "$selected" ]; then
    full_path="$wall_dir/$selected"
    wallust run -s "$full_path"
fi
