#!/bin/bash
# Wrapper para hyprshot que aplica corrección de color inversa al shader vibrance
# Solo afecta a screenshots guardados (no clipboard)

# Valores inversos a tu shader vibrance.glsl
# SATURATION=1.1 -> inverso = 91 (100/1.1)  
# VIBRANCE=0.6 -> reducimos saturación extra
SATURATION_CORRECTION=88  # Un poco menos de 91 para compensar vibrance también

# Detectar si es clipboard-only
if [[ "$*" == *"--clipboard-only"* ]]; then
    # Clipboard: ejecutar hyprshot normal sin corrección
    exec hyprshot "$@"
fi

# Directorio real de screenshots (Imágenes en español)
SCREENSHOT_DIR="${HYPRSHOT_DIR:-$HOME/Imágenes}"

# Guardar timestamp antes de capturar
BEFORE_TIME=$(date +%s)

# Ejecutar hyprshot
hyprshot "$@"

# Buscar el archivo más reciente creado después de la captura
sleep 0.5
LATEST_FILE=$(find "$SCREENSHOT_DIR" -maxdepth 1 -type f -name "*hyprshot*.png" -newermt "@$BEFORE_TIME" 2>/dev/null | head -1)

if [[ -n "$LATEST_FILE" && -f "$LATEST_FILE" ]]; then
    # Aplicar corrección de color inversa
    magick "$LATEST_FILE" -modulate 100,$SATURATION_CORRECTION,100 -brightness-contrast 0x-2 "$LATEST_FILE"
    notify-send "Screenshot corregido" "Color normalizado: $(basename "$LATEST_FILE")"
else
    notify-send "Screenshot" "No se aplicó corrección (archivo no encontrado)"
fi
