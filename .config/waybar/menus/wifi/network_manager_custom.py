#!/usr/bin/env python3
import pathlib
import struct
import configparser
import locale
import os
from os.path import basename, expanduser
import shlex
from shutil import which
import sys
from time import sleep
import uuid
import subprocess
import gettext
import gi
gi.require_version('NM', '1.0')
from gi.repository import GLib, NM

ENV = os.environ.copy()
ENC = locale.getpreferredencoding()

SCRIPT_DIR = pathlib.Path(__file__).parent
LOCALE_DIR = SCRIPT_DIR / "locales"

try:
    lang = locale.getlocale()[0]
    if not lang:
        lang = os.environ.get('LANG', 'en')
    
    if str(lang).lower().startswith('es'):
        lang = 'es'
    else:
        lang = 'en'
except:
    lang = 'en'

try:
    t = gettext.translation('wifi-menu', localedir=str(LOCALE_DIR), languages=[lang, 'en'])
    _ = t.gettext
except:
    _ = lambda x: x

CONF = configparser.ConfigParser()
CONF.read(expanduser("~/.config/networkmanager/config.ini"))

CLIENT = None
CONNS = None
LOOP = None

ROFI_THEME = expanduser("~/.config/waybar/menus/wifi/wifi.rasi")

def notify(message, urgency="low"):
    if is_installed("notify-send"):
        subprocess.run(["notify-send", "-u", urgency, "-a", "networkmanager-dmenu", message], check=False)

def is_installed(cmd):
    return which(cmd) is not None

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

def dmenu_cmd(num_lines, prompt="Redes", active_lines=None, password=False):
    raw_cmd = CONF.get('dmenu', 'dmenu_command', fallback="rofi -dmenu")
    command = shlex.split(raw_cmd)
    
    if "-dmenu" not in command:
        command.append("-dmenu")
    
    if "-markup-rows" not in command:
        command.append("-markup-rows")
    
    if "-p" in command:
        idx = command.index("-p")
        del command[idx:idx+2]
        
    command.extend(["-p", str(prompt)])
    command.extend(cli_args())
    
    if password:
        password_theme = expanduser("~/.config/waybar/menus/wifi/password.rasi")
        if "-theme" in command:
            idx = command.index("-theme")
            command[idx+1] = password_theme
        else:
            command.extend(["-theme", password_theme])
        command.append("-password")
    else:
        # Enforce wifi theme if not password
        if "-theme" in command:
            idx = command.index("-theme")
            try:
                command[idx+1] = ROFI_THEME
            except IndexError:
                command.extend([ROFI_THEME])
        else:
            command.extend(["-theme", ROFI_THEME])
    
    return command

def get_passphrase():
    cmd = dmenu_cmd(0, prompt="Contraseña", password=True)
    res = subprocess.run(cmd, capture_output=True, encoding=ENC, input="").stdout.strip()
    if not res: sys.exit(0)
    return res

def ssid_to_utf8(nm_ap):
    ssid = nm_ap.get_ssid()
    if not ssid: return ""
    return NM.utils_ssid_to_utf8(ssid.get_data())

def ap_security(nm_ap):
    flags = nm_ap.get_flags()
    wpa_flags = nm_ap.get_wpa_flags()
    rsn_flags = nm_ap.get_rsn_flags()
    sec_str = ""
    if ((flags & getattr(NM, '80211ApFlags').PRIVACY) and (wpa_flags == 0) and (rsn_flags == 0)):
        sec_str = " WEP"
    if wpa_flags: sec_str = " WPA1"
    if rsn_flags & getattr(NM, '80211ApSecurityFlags').KEY_MGMT_PSK: sec_str += " WPA2"
    if rsn_flags & getattr(NM, '80211ApSecurityFlags').KEY_MGMT_SAE: sec_str += " WPA3"
    return sec_str.strip() if sec_str else "--"

class Action():
    def __init__(self, name, func, args=None, active=False):
        self.name = name; self.func = func; self.is_active = active
        self.args = args if isinstance(args, list) else ([args] if args else None)
    def __str__(self): return self.name
    def __call__(self): self.func(*self.args) if self.args else self.func()

def process_ap(nm_ap, is_active, adapter):
    if is_active:
        CLIENT.deactivate_connection_async(nm_ap, None, lambda *a: LOOP.quit(), None)
        LOOP.run()
    else:
        conns_cur = [i for i in CONNS if i.get_setting_wireless() is not None and conn_matches_adapter(i, adapter)]
        con = nm_ap.filter_connections(conns_cur)
        if len(con) == 1:
            CLIENT.activate_connection_async(con[0], adapter, nm_ap.get_path(), None, lambda *a: LOOP.quit(), None)
            LOOP.run()
        else:
            password = get_passphrase() if ap_security(nm_ap) != "--" else ""
            set_new_connection(nm_ap, password, adapter)

def conn_matches_adapter(conn, adapter):
    sw = conn.get_setting_wireless()
    if not sw: return False
    mac = sw.get_mac_address()
    if mac: return mac == adapter.get_permanent_hw_address()
    sc = conn.get_setting_connection()
    iface = sc.get_interface_name()
    if iface: return iface == adapter.get_iface()
    return True

def on_connection_finish(client, res, data):
    try:
        client.add_and_activate_connection_finish(res)
        notify("Conexión iniciada con éxito")
    except Exception as e:
        err_msg = str(e)
        print(f"Connection Error: {err_msg}")
        notify(f"Fallo en la conexión: {err_msg}", "critical")
    LOOP.quit()

def set_new_connection(nm_ap, password, adapter):

    profile = create_wifi_profile(nm_ap, password, adapter)
    CLIENT.add_and_activate_connection_async(profile, adapter, nm_ap.get_path(), None, on_connection_finish, None)
    LOOP.run()

def create_wifi_profile(nm_ap, password, adapter):
    sec = ap_security(nm_ap)
    profile = NM.SimpleConnection.new()
    s_con = NM.SettingConnection.new()
    s_con.set_property(NM.SETTING_CONNECTION_ID, ssid_to_utf8(nm_ap))
    s_con.set_property(NM.SETTING_CONNECTION_TYPE, "802-11-wireless")
    profile.add_setting(s_con)
    s_wifi = NM.SettingWireless.new()
    s_wifi.set_property(NM.SETTING_WIRELESS_SSID, nm_ap.get_ssid())
    s_wifi.set_property(NM.SETTING_WIRELESS_MAC_ADDRESS, adapter.get_permanent_hw_address())
    profile.add_setting(s_wifi)
    
    # Critical Fix: Explicitly set IP configuration method to 'auto'
    s_ip4 = NM.SettingIP4Config.new()
    s_ip4.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")
    profile.add_setting(s_ip4)
    
    s_ip6 = NM.SettingIP6Config.new()
    s_ip6.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")
    profile.add_setting(s_ip6)
    
    if sec != "--":
        s_sec = NM.SettingWirelessSecurity.new()
        if "WPA" in sec:
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, "sae" if "WPA3" in sec else "wpa-psk")
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)
        profile.add_setting(s_sec)
    return profile

# Colors
WHITE = "#FFFFFF"
GRAY = "#7d7d7d"
GREEN = "#00ff00"

def get_wifi_state():
    client = NM.Client.new(None)
    loop = GLib.MainLoop()
    conns = client.get_connections()
    
    devices = client.get_devices()
    wifi_devices = [i for i in devices if i.get_device_type() == NM.DeviceType.WIFI]
    if not wifi_devices:
        return None, None, None, None
        
    adapter = wifi_devices[0]
    return client, loop, conns, adapter

def get_selection(actions):
    inp = [str(a) for a in actions]
    cmd = dmenu_cmd(len(inp))
    sel = subprocess.run(cmd, capture_output=True, input="\n".join(inp), encoding=ENC, env=ENV).stdout.strip()
    if not sel: sys.exit(0)
    for a in actions:
        if str(a).strip() == sel.strip(): return a
    sys.exit(0)

def refresh_and_show():
    subprocess.run(['nmcli', 'device', 'wifi', 'rescan'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    notify("Escaneando redes...")
    sleep(2)
    main()

def delete_connection_menu():
    global CLIENT, LOOP, CONNS
    saved = [i for i in CONNS if i.get_setting_wireless() is not None]
    if not saved:
        notify("No hay redes guardadas")
        main()
        return

    inp = [i.get_id() for i in saved]
    # White prompt
    cmd = dmenu_cmd(len(inp), prompt="OLVIDAR RED")
    
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding=ENC)
        sel, _ = proc.communicate(input="\n".join(inp))
        sel = sel.strip()
    except: sel = ""
    
    if not sel:
        main()
        return
        
    to_delete = [i for i in saved if i.get_id() == sel]
    if to_delete:
        try:
            to_delete[0].delete(None) # Sync delete
            notify(f"Olvidada: {sel}")
        except: 
            notify("Error al eliminar la conexión", "critical")
    main()

def main():
    global CLIENT, LOOP, CONNS
    
    # Ensure scan happens
    subprocess.Popen(['nmcli', 'device', 'wifi', 'rescan'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    CLIENT, LOOP, CONNS, adapter = get_wifi_state()
    if not CLIENT:
        notify("No se encontró adaptador WiFi", "critical")
        sys.exit(1)
        
    aps_all = adapter.get_access_points()
    active_ap = adapter.get_active_access_point()
    active_bssid = active_ap.get_bssid() if active_ap else ""
    
    networks = []
    ap_names = set()
    
    for ap in aps_all:
        try:
            ssid = ap.get_ssid()
            if not ssid: continue
            name = NM.utils_ssid_to_utf8(ssid.get_data())
            if not name or name in ap_names: continue
            ap_names.add(name)
            
            strength = ap.get_strength()
            rsn_flags = ap.get_rsn_flags()
            wpa_flags = ap.get_wpa_flags()
            # Simple security check
            is_secure = (rsn_flags != 0) or (wpa_flags != 0)
            
            is_active = (ap.get_bssid() == active_bssid)
            
            networks.append({
                'ap': ap,
                'name': name,
                'strength': strength,
                'secure': is_secure,
                'active': is_active
            })
        except: continue
    
    # Sort: Active first, then Signal
    networks.sort(key=lambda n: (not n['active'], -n['strength']))
    
    actions = []
    
    # Fixed Options - White Text
    forget_label = f"<span foreground='{WHITE}'>󰆴  Olvidar red guardada</span>"
    refresh_label = f"<span foreground='{WHITE}'>󰑐  Actualizar lista</span>"
    
    actions.append(Action(forget_label, delete_connection_menu))
    actions.append(Action(refresh_label, refresh_and_show))
    actions.append(Action("     ", lambda: None))

    for net in networks:
        # Determine Icon based on Security/Saved
        saved_conns = [c for c in CONNS if c.get_setting_wireless() and c.get_id() == net['name']]
        is_saved = len(saved_conns) > 0
        
        strength = net['strength']
        # Bars icon logic
        wifi_icons = CONF.get('dmenu', 'wifi_icons', fallback="󰤯󰤟󰤢󰤥󰤨")
        
        # Ensure we have enough icons, fallback to defaults if config is short
        if len(wifi_icons) < 5: wifi_icons = "󰤯󰤟󰤢󰤥󰤨"
            
        if strength > 80: bars = wifi_icons[4]
        elif strength > 60: bars = wifi_icons[3]
        elif strength > 40: bars = wifi_icons[2]
        elif strength > 20: bars = wifi_icons[1]
        else: bars = wifi_icons[0]
        
        # Lock icon logic: Only show lock if secure AND NOT SAVED
        lock = " " if net['secure'] and not is_saved else ""
        name = net['name']
        
        # Construct Label
        # Construct Label
        if net['active']:
            # Active: Green Icon + White Bold Text
            label = f"<span foreground='{GREEN}'>{bars}</span>  <span foreground='{WHITE}' weight='bold'>{name}{lock}</span>"
        else:
            # Inactive: Gray
            label = f"<span foreground='{GRAY}'>{bars}</span>  <span foreground='{GRAY}'>{name}{lock}</span>"
        
        actions.append(Action(label, process_ap, [net['ap'], net['active'], adapter]))
    
    if not networks:
        actions.append(Action(f"<span foreground='{GRAY}'>󰤯  Buscando redes...</span>", lambda: None))
    
    if actions:
        selected = get_selection(actions)
        if selected:
            selected()

if __name__ == '__main__':
    main()
