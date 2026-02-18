#!/bin/bash

wall_dir="$HOME/Pictures/Wallpapers"
cache_dir="$HOME/.cache/rofi-wall-thumbs"
rofi_theme="$HOME/.config/rofi/artbook.rasi"

# Si cambias el tipo aquí, asegúrate de actualizar la línea larga de abajo también si quieres usar la variable
transition_type="grow"

if [ ! -d "$cache_dir" ]; then
    mkdir -p "$cache_dir"
fi

if [ -z "$(ls -A "$wall_dir")" ]; then
    notify-send "Error" "La carpeta $wall_dir está vacía."
    exit 1
fi

gen_rofi_list() {
    find "$wall_dir" -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.jpeg" -o -iname "*.webp" \) | sort | while read -r img; do
        filename=$(basename "$img")
        name_no_ext="${filename%.*}"
        thumb_name="${name_no_ext}_thumb.jpg"
        thumb_path="$cache_dir/$thumb_name"

        if [ ! -f "$thumb_path" ]; then
            convert "$img" -resize x750 -gravity Center -crop 500x750+0+0 +repage "$thumb_path"
        fi

        echo -en "${name_no_ext}\0icon\x1f${thumb_path}\n"
    done
}

if [[ -z "$1" ]]; then
    selected_name=$(gen_rofi_list | rofi -dmenu -theme "$rofi_theme" -p "Wallpapers" -i)
    
    if [[ -z "$selected_name" ]]; then
        exit 0
    fi
    
    full_path=$(find "$wall_dir" -type f -name "$selected_name.*" | head -n 1)
else
    full_path="$1"
fi

if [ -f "$full_path" ]; then
    swww img "$full_path" --transition-type any --transition-pos 0.8,0.9 --transition-duration 0.3 --transition-step 2 --transition-fps 60

    ln -sf "$full_path" ~/.config/hypr/current_wallpaper
    ~/.cargo/bin/wallust run -s "$full_path"
    pkill swayosd-server
    swayosd-server &
    pkill dunst
    dunst &

    killall lxqt-policykit-agent
    /usr/libexec/lxqt-policykit-agent &

    killall waybar
    env LC_ALL=es_CL.UTF-8 LANG=es_CL.UTF-8 waybar &
    killall -SIGUSR1 kitty
fi
killall -SIGUSR1 kitty
