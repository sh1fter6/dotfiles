#!/usr/bin/env python3
# encoding:utf8
"""Bluetooth Menu - Clonado de network_manager_custom.py"""
import configparser
import locale
import os
from os.path import expanduser
import shlex
from shutil import which
import sys
from time import sleep
import subprocess
import re

WHITE = "#FFFFFF"
GRAY = "#7d7d7d"
BLUE = "#00bfff"

ENV = os.environ.copy()
ENC = locale.getpreferredencoding()

CONF = configparser.ConfigParser()
CONF.read(expanduser("~/.config/networkmanager/config.ini"))

try:
    LANG_CODE = locale.getlocale()[0]
    if not LANG_CODE:
        LANG_CODE = os.environ.get('LANG', 'en_US')
except:
    LANG_CODE = 'en_US'

TR = {
    'es': {
        'forget_device': "Olvidar dispositivo",
        'refresh_list': "Refrescar lista",
        'olvidar_prompt': "Olvidar:",
        'no_saved_devices': "No hay dispositivos guardados",
        'scanning': "Escaneando...",
        'searching': "Buscando dispositivos...",
        'connected_suffix': "(Conectado)",
        'disconnecting': "Desconectando",
        'connecting': "Conectando a",
        'forgotten': "Olvidado"
    },
    'en': {
        'forget_device': "Forget Device",
        'refresh_list': "Refresh List",
        'olvidar_prompt': "Forget:",
        'no_saved_devices': "No saved devices",
        'scanning': "Scanning...",
        'searching': "Searching for devices...",
        'connected_suffix': "(Connected)",
        'disconnecting': "Disconnecting",
        'connecting': "Connecting to",
        'forgotten': "Forgotten"
    }
}

L = TR['es'] if str(LANG_CODE).lower().startswith('es') else TR['en']

def notify(message, urgency="low"):
    if which("notify-send"):
        subprocess.run(["notify-send", "-u", urgency, "-a", "bluetooth-menu", "-t", "3000", "-h", "string:x-canonical-private-synchronous:bluetooth_menu", message], check=False)

def cli_args():
    args = sys.argv[1:]
    cmd = CONF.get('dmenu', 'dmenu_command', fallback=False)
    if "-l" in args or "-p" in args:
        for nope in ['-l', '-p'] if cmd is not False else ['-p']:
            try:
                nope_idx = args.index(nope)
                del args[nope_idx]
                del args[nope_idx]
            except ValueError:
                pass
    return args

def dmenu_cmd(num_lines, prompt="Bluetooth"):
    MIN_LINES = 1
    MAX_LINES = 10
    current_lines = max(MIN_LINES, min(num_lines, MAX_LINES))

    raw_cmd = CONF.get('dmenu', 'dmenu_command', fallback="rofi -dmenu")
    command = shlex.split(raw_cmd)
    
    # Limpiar flags de líneas existentes en el comando base para evitar conflictos
    if "-l" in command:
        try:
            idx = command.index("-l")
            del command[idx:idx+2]
        except: pass
    if "-lines" in command:
        try:
            idx = command.index("-lines")
            del command[idx:idx+2]
        except: pass
    
    if "-dmenu" not in command:
        command.append("-dmenu")
    
    if "-markup-rows" not in command:
        command.append("-markup-rows")
    
    if "-p" in command:
        idx = command.index("-p")
        del command[idx:idx+2]
        
    command.extend(["-p", str(prompt)])
    command.extend(["-l", str(current_lines)])
    command.extend(cli_args())
    

    if "-theme" in command:
        idx = command.index("-theme")
        try:
            command[idx+1] = expanduser("~/.config/waybar/menus/bluetooth/bluetooth.rasi")
        except IndexError:
            # Should not happen if -theme is the last arg without value, but just in case
            command.extend([expanduser("~/.config/waybar/menus/bluetooth/bluetooth.rasi")])
    else:
        command.extend(["-theme", expanduser("~/.config/waybar/menus/bluetooth/bluetooth.rasi")])
    
    return command

class Action():
    def __init__(self, name, func, args=None, active=False):
        self.name = name
        self.func = func
        self.is_active = active
        self.args = args if isinstance(args, list) else ([args] if args else None)
    def __str__(self):
        return self.name
    def __call__(self):
        self.func(*self.args) if self.args else self.func()

def get_selection(actions):
    inp = [str(a) for a in actions]
    cmd = dmenu_cmd(len(inp))
    sel = subprocess.run(cmd, capture_output=True, input="\n".join(inp), encoding=ENC, env=ENV).stdout.strip()
    if not sel:
        sys.exit(0)
    for a in actions:
        if str(a).strip() == sel.strip():
            return a
    sys.exit(0)

def get_bt_devices():
    """Obtener dispositivos bluetooth paired."""
    devices = []
    seen = set()
    
    # Obtener dispositivos paired
    result = subprocess.run(["bluetoothctl", "devices", "Paired"], capture_output=True, text=True)
    for line in result.stdout.strip().splitlines():
        parts = line.split(" ", 2)
        if len(parts) >= 3 and parts[0] == "Device":
            mac = parts[1]
            name = parts[2]
            seen.add(mac)
            
            info = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
            connected = "Connected: yes" in info
            
            devices.append({
                "mac": mac,
                "name": name,
                "connected": connected,
                "paired": True
            })
    
    return devices

def scan_and_get_devices():
    """Hacer scan bloqueante y obtener TODOS los dispositivos (paired + descubiertos)."""
    devices = []
    seen = set()
    
    # Primero agregar paired
    result = subprocess.run(["bluetoothctl", "devices", "Paired"], capture_output=True, text=True)
    for line in result.stdout.strip().splitlines():
        parts = line.split(" ", 2)
        if len(parts) >= 3 and parts[0] == "Device":
            mac = parts[1]
            name = parts[2]
            seen.add(mac)
            
            info = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
            connected = "Connected: yes" in info
            
            devices.append({
                "mac": mac,
                "name": name,
                "connected": connected,
                "paired": True
            })
    
    # Hacer scan y capturar dispositivos descubiertos
    # Hacer scan y capturar dispositivos descubiertos
    try:
        # Usar stdbuf para evitar buffering
        cmd = ["stdbuf", "-oL", "bluetoothctl", "--timeout", "4", "scan", "on"]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
            
        # Usar diccionario para permitir actualizaciones de nombre
        # Clave: MAC, Valor: dict del dispositivo
        scanned_devices = {}
        
        # Agregar dispositivos paired previos al tracking
        for d in devices:
            scanned_devices[d['mac']] = d
        
        # Regex para limpiar ANSI codes
        def clean_ansi(text):
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text)
        
        # Regex para capturar MAC de cualquier linea de dispositivo
        import re
        mac_pattern = re.compile(r"\[(?:NEW|CHG)\] Device ([0-9A-F:]{17})(?:\s+(.*))?", re.IGNORECASE)
        
        for line in output.splitlines():
            line = clean_ansi(line) # Limpiar colores
            match = mac_pattern.search(line)
            if match:
                mac = match.group(1).upper()
                raw_rest = match.group(2).strip() if match.group(2) else ""
                
                # Detectar actualizaciones de nombre
                possible_name = None
                
                # Casos comunes:
                # [NEW] Device AA:BB... Name
                # [CHG] Device AA:BB... Name: RealName
                # [CHG] Device AA:BB... Alias: RealName
                
                if "Name:" in raw_rest:
                    possible_name = raw_rest.split("Name:", 1)[1].strip()
                elif "Alias:" in raw_rest:
                    possible_name = raw_rest.split("Alias:", 1)[1].strip()
                elif not any(x in raw_rest for x in ["RSSI:", "TxPower:", "ManufacturerData", "ServiceData", "Class:", "Icon:", "Connected:", "UUIDs:", "Modalias:"]):
                    # Si no es ruido tecnico, asumimos que es el nombre (formato NEW)
                    possible_name = raw_rest
                
                # Validar nombre
                if possible_name:
                    # Normalizar guiones a dos puntos para comparar con MAC
                    norm_name = possible_name.replace("-", ":").upper()
                    if norm_name == mac:
                        possible_name = None # El nombre es solo la MAC disfrazada
                
                if mac not in scanned_devices:
                    # Nuevo dispositivo
                    
                    # Intentar obtener info si no tenemos nombre o si el nombre es solo la MAC
                    if not possible_name:
                         info = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
                         for info_line in info.splitlines():
                            if "Name:" in info_line:
                                possible_name = info_line.split("Name:", 1)[1].strip()
                                break
                            if "Alias:" in info_line and not possible_name: # Fallback al alias
                                 possible_name = info_line.split("Alias:", 1)[1].strip().replace("-", ":")
                    
                    name = possible_name if possible_name else mac
                    
                    # Estado (default desconectado para escaneados)
                    connected = False
                    paired = False
                    
                    scanned_devices[mac] = {
                        "mac": mac,
                        "name": name,
                        "connected": connected,
                        "paired": paired
                    }
                else:
                    # Dispositivo ya conocido, actualizamos nombre si encontramos uno mejor
                    if possible_name and possible_name != mac:
                        current_name = scanned_devices[mac]['name']
                        # Si el nombre actual es la MAC, o tenemos un nombre nuevo distinto
                        if current_name == mac or (possible_name != current_name):
                             scanned_devices[mac]['name'] = possible_name

        # Convertir a lista y filtrar fantasmas (MACs sin nombre)
        devices = []
        for d in scanned_devices.values():
             # Si esta emparejado o conectado, siempre mostrar
             if d['paired'] or d['connected']:
                 devices.append(d)
                 continue
             
             # Si no esta emparejado, solo mostrar si tiene un nombre real
             # (que no sea igual a la MAC normalizada)
             d_name_norm = d['name'].replace("-", ":").upper()
             if d_name_norm != d['mac']:
                 devices.append(d)
    
    except Exception as e:
        print(f"Scan error: {e}")
        pass
    
    return devices

def toggle_connection(device):
    """Conectar o desconectar un dispositivo."""
    if device["connected"]:
        notify(f"{L['disconnecting']} {device['name']}...")
        subprocess.run(["bluetoothctl", "disconnect", device["mac"]], capture_output=True)
    else:
        notify(f"{L['connecting']} {device['name']}...")
        # Si no está paired, primero emparejar
        if not device.get("paired", False):
            subprocess.run(["bluetoothctl", "pair", device["mac"]], capture_output=True, timeout=10)
            subprocess.run(["bluetoothctl", "trust", device["mac"]], capture_output=True)
        subprocess.run(["bluetoothctl", "connect", device["mac"]], capture_output=True)

def forget_device_menu():
    """Mostrar menú para olvidar dispositivos."""
    devices = get_bt_devices()
    
    if not devices:
        notify(L['no_saved_devices'])
        main()
        return
    
    inp = [d["name"] for d in devices]
    cmd = dmenu_cmd(len(inp), prompt=L['olvidar_prompt'])
    sel = subprocess.run(cmd, capture_output=True, input="\n".join(inp), encoding=ENC, env=ENV).stdout.strip()
    
    if not sel:
        main()
        return
    
    for d in devices:
        if d["name"] == sel:
            subprocess.run(["bluetoothctl", "remove", d["mac"]], capture_output=True)
            notify(f"{L['forgotten']}: {sel}")
            break
    
    main()

def refresh_and_show():
    """Escanear (bloqueante) y mostrar menú con todos los dispositivos."""
    notify(L['scanning'])
    devices = scan_and_get_devices()
    show_menu(devices)

def main():
    # Mostrar dispositivos paired inmediatamente
    devices = get_bt_devices()
    show_menu(devices)

def show_menu(devices=None):
    if devices is None:
        devices = get_bt_devices()
    
    # Ordenar: conectados primero, luego paired, luego otros
    devices.sort(key=lambda d: (not d["connected"], not d.get("paired", False), d["name"]))
    
    actions = []
    
    # Opciones fijas - White text
    actions.append(Action(f"<span foreground='{WHITE}'>󰆴  {L['forget_device']}</span>", forget_device_menu))
    actions.append(Action(f"<span foreground='{WHITE}'>󰑐  {L['refresh_list']}</span>", refresh_and_show))
    actions.append(Action("               ", lambda: None))
    
    # Lista de dispositivos
    for dev in devices:
        name = dev['name']
        if dev["connected"]:
            icon = "󰂱"  # Connected icon
            # Active: Blue Icon + White Bold Text
            label = f"<span foreground='{BLUE}'>{icon}</span>  <span foreground='{WHITE}' weight='bold'>{name}</span>"
        else:
            icon = "󰂯"  # Bluetooth icon
            # Inactive: Gray
            label = f"<span foreground='{GRAY}'>{icon}  {name}</span>"
        
        actions.append(Action(label, toggle_connection, dev))
    
    # Si no hay dispositivos
    if not devices:
        actions.append(Action(f"<span foreground='{GRAY}'>󰂲  {L['searching']}</span>", lambda: None))
    
    selected = get_selection(actions)
    if selected:
        selected()

if __name__ == "__main__":
    main()
