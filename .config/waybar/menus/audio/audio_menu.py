#!/usr/bin/env python3
# encoding:utf8
"""Custom Audio management script with Rofi UI - Refined version."""
import os
import re
import subprocess
import sys
from os.path import expanduser


ROFI_THEME = expanduser("~/.config/waybar/menus/audio/pulseaudio.rasi")
ENC = "utf-8"


WHITE = "#FFFFFF"
GRAY = "#7d7d7d"
GREEN = "#00ff00"
URGENT = "#EB6F92"

def dmenu_cmd(num_lines, prompt="Audio"):
    MIN_LINES = 1
    MAX_LINES = 10 
    current_lines = max(MIN_LINES, min(num_lines, MAX_LINES))

    return ["rofi", "-dmenu", "-p", prompt, "-theme", ROFI_THEME, "-i", "-markup-rows", "-l", str(current_lines)]

def get_selection(options, prompt="Audio"):
    if not options: return None
    

    cmd = dmenu_cmd(len(options), prompt)
    
    inp = "\n".join(options)
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding=ENC)
        stdout, _ = process.communicate(input=inp)
        return stdout.strip()
    except Exception: return None

def parse_pactl_output(output):
    """Parses pactl list output into a list of dictionaries with Port support."""
    devices = []
    current_device = {}
    in_ports = False
    
    for line in output.splitlines():
        line = line.strip()
        if not line:
            in_ports = False
            if current_device and "id" in current_device:
                devices.append(current_device)
                current_device = {}
            continue
            
        if line.startswith("Sink #") or line.startswith("Source #"):
            if current_device and "id" in current_device:
                devices.append(current_device)
            current_device = {"id": line.split("#")[1], "ports": {}, "active_port": None}
            in_ports = False
            continue
        
        # Handle 'Ports:' block start (it ends with colon but no space usually)
        if line == "Ports:":
            in_ports = True
            continue
            
        # Detect key-values with divider
        if ": " in line:
            key, value = line.split(": ", 1)
            
            if key == "Active Port":
                in_ports = False
                current_device["active_port"] = value
                continue
            
            if in_ports:
                # Format: port_name: description (priority...)
                p_name = key
                # Description often contains parenthesis with priority, type, etc.
                p_desc = value.split(" (")[0]
                current_device["ports"][p_name] = p_desc
            else:
                current_device[key] = value

    if current_device and "id" in current_device:
        devices.append(current_device)
        
    return devices

def get_audio_info():
    sinks = []
    sources = []
    
    env = os.environ.copy()
    env["LC_ALL"] = "C" # Force English keys for parsing
    
    # helper to clean up long names
    def clean_device_name(desc):
        # Remove common technical suffixes that clutter the UI
        replacements = [
            ("Audio Controller", ""),
            ("Estéreo analógico", ""),
            ("Analog Stereo", ""),
            ("Digital Stereo (HDMI)", "HDMI"),
            ("Controller", ""),
            ("Family", ""),
            ("High Definition", "HD"),
            (" HD Audio", " HD"),
            ("Unknown", ""),
        ]
        for old, new in replacements:
            desc = desc.replace(old, new)
        
        # Strip extra whitespace
        return " ".join(desc.split())

    # helper for processing raw devices
    def process_raw_devices(raw_list, default_name):
        processed = []
        for d in raw_list:
            name = d.get("Name", "")
            raw_desc = d.get("Description", name)
            base_desc = clean_device_name(raw_desc)
            if not base_desc: base_desc = raw_desc # fallback if we stripped everything
            
            # Extract volume percent
            vol_str = d.get("Volume", "")
            vol_match = re.search(r'(\d+)%', vol_str)
            vol = int(vol_match.group(1)) if vol_match else 0
            
            is_default = (name == default_name)
            
            # Ports Logic
            ports = d.get("ports", {})
            active_port = d.get("active_port")
            
            # If we have multiple valid ports
            available_ports = []
            if ports:
                for p_name, p_desc in ports.items():
                    available_ports.append((p_name, p_desc))
            
            if len(available_ports) > 1:
                # Create an entry for each port
                for p_name, p_desc in available_ports:
                    # Mark active only if device is default AND this port is active
                    is_active_port = is_default and (p_name == active_port)
                    
                    # Improved Format: Put Port FIRST so it's not truncated
                    # e.g. "Micrófono interno (Ryzen HD)"
                    full_desc = f"{p_desc} ({base_desc})"
                    
                    processed.append({
                        "name": name,
                        "desc": full_desc,
                        "vol": vol,
                        "active": is_active_port,
                        "port": p_name,
                        "base_desc_raw": base_desc
                    })
            else:
                # Single device entry
                # Check if it has a single port with a useful name (like "Speaker" vs "Headphones")
                # Sometimes single port devices don't need the port name appended if it's generic like "Analog Output"
                port_name = None
                display_desc = base_desc
                
                if available_ports:
                    p_name, p_desc = available_ports[0]
                    port_name = p_name
                    # If the single port has a specific meaningful name different from "Analog Output", maybe use it?
                    # For now keep it simple to avoid redundancy like "JBL Clip 4 - Speaker"
                
                processed.append({
                    "name": name,
                    "desc": display_desc,
                    "vol": vol,
                    "active": is_default,
                    "port": port_name
                })
        return processed

    # Get Sinks
    try:
        res = subprocess.run(["pactl", "list", "sinks"], capture_output=True, text=True, env=env).stdout
        raw_sinks = parse_pactl_output(res)
        default_sink = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True, env=env).stdout.strip()
        sinks = process_raw_devices(raw_sinks, default_sink)
    except Exception: pass

    # Get Sources
    try:
        res = subprocess.run(["pactl", "list", "sources"], capture_output=True, text=True, env=env).stdout
        raw_sources = parse_pactl_output(res)
        default_source = subprocess.run(["pactl", "get-default-source"], capture_output=True, text=True, env=env).stdout.strip()
        
        # Pre-filter monitors from raw list
        filtered_sources = []
        for s in raw_sources:
             # Ignore monitors
             if "monitor" not in s.get("Name", "") and "Monitor by" not in s.get("Description", ""):
                 filtered_sources.append(s)
                 
        sources = process_raw_devices(filtered_sources, default_source)
    except Exception: pass
    
    return sinks, sources

def get_input_icon(desc, lower_desc):
    """Determine icon based on keywords"""
    if any(x in lower_desc for x in ["headset", "auriculares", "casco", "audífono"]):
        return "󰋎" # Headset
    elif any(x in lower_desc for x in ["buds", "pods", "air", "dots", "pequeños", "earphone"]):
        return "󰋐" # Earbuds (Requires proper Nerd Font)
    elif "internal" in lower_desc or "interno" in lower_desc:
        return "" # Mic
    return "" # Default Mic

def format_line(device, type="sink"):
    """Format row using Pango markup with specific requested styles."""
    name = device["desc"]
    active = device["active"]
    vol = device["vol"]
    lower_desc = name.lower()
    
    # Determine Icon
    if type == "sink":
        # Output logic: Icons depend strictly on volume level
        if vol > 60: icon = ""
        elif vol > 30: icon = ""
        else: icon = ""
    else:
        # Input icons
        icon = get_input_icon(name, lower_desc)
    
    # Construct Label
    if active:
        # Active: Green Icon + White Bold Text
        return f"<span foreground='{GREEN}'>{icon}</span>  <span foreground='{WHITE}' weight='bold'>{name} ({vol}%)</span>"
    else:
        # Inactive: All Gray
        return f"<span foreground='{GRAY}'>{icon}  {name}</span>"

def main():
    sinks, sources = get_audio_info()
    options = []
    
    # Outputs Section
    options.append("<b>SALIDAS:</b>")
    for s in sinks:
        options.append(format_line(s, "sink"))
    
    options.append("") # Spacer
    
    # Inputs Section
    options.append("<b>ENTRADAS:</b>")
    for s in sources:
        options.append(format_line(s, "source"))

    sel = get_selection(options)
    
    # Validation and Execution
    if not sel or "<b>" in sel or sel.strip() == "":
        sys.exit(0)
    
    # Parsing logic refined for Pango markup
    # Format: <span ...>{icon}  {name} ({vol}%)</span>
    
    # 1. Strip all tags
    text_only = re.sub(r'<[^>]+>', '', sel).strip()
    
    # 2. Remove Icon
    parts = text_only.split(maxsplit=1)
    if len(parts) > 1:
        pure_name = parts[1]
    else:
        pure_name = text_only

    # 3. Remove volume info like (50%) at end
    pure_name = re.sub(r'\s*\(\d+%\)$', '', pure_name).strip()
    
    # Find the device with this desc
    target_device = None
    target_type = None
    
    # Helper to find match
    for s in sinks:
        if s["desc"] == pure_name:
            target_device = s
            target_type = "sink"
            break
            
    if not target_device:
        for s in sources:
            if s["desc"] == pure_name:
                target_device = s
                target_type = "source"
                break
    
    if target_device:
        # Set Default Device
        cmd_type = "set-default-sink" if target_type == "sink" else "set-default-source"
        subprocess.run(["pactl", cmd_type, target_device["name"]])
        
        # Set Port if specific port is associated
        if target_device["port"]:
            port_cmd_type = "set-sink-port" if target_type == "sink" else "set-source-port"
            subprocess.run(["pactl", port_cmd_type, target_device["name"], target_device["port"]])
    
    for s in sinks:
        if s["desc"] == pure_name:
            target_device = s
            target_type = "sink"
            break
            
    if not target_device:
        for s in sources:
            if s["desc"] == pure_name:
                target_device = s
                target_type = "source"
                break
    
    if target_device:
        cmd_type = "set-default-sink" if target_type == "sink" else "set-default-source"
        subprocess.run(["pactl", cmd_type, target_device["name"]])
        
        # Optional: Notifications?
        # subprocess.run(["notify-send", f"Audio {target_type} changed", target_device["desc"]])

if __name__ == "__main__":
    main()
