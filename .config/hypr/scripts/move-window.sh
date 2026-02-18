#!/bin/bash
# Script para mover ventanas en Hyprland
# Si la ventana es flotante, la convierte a tiled antes de moverla

direction=$1

# Obtener información de la ventana activa
active_window=$(hyprctl activewindow -j)
is_floating=$(echo "$active_window" | jq -r '.floating')

# Si la ventana está flotando, primero la hacemos tiled
if [ "$is_floating" = "true" ]; then
    hyprctl dispatch togglefloating
fi

# Mover la ventana en la dirección especificada
hyprctl dispatch movewindow "$direction"
