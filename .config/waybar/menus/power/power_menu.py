#!/usr/bin/env python3
# encoding:utf8
"""Power Menu - Sistema de apagado/power management con Rofi UI."""
import locale
import os
from os.path import expanduser
import subprocess
import sys


ROFI_THEME = expanduser("~/.config/waybar/menus/power/logout.rasi")
ENC = "utf-8"


WHITE = "#FFFFFF"
GRAY = "#7d7d7d"
RED = "#ff0000"
YELLOW = "#ffff00"


try:
    LANG_CODE = locale.getlocale()[0]
    if not LANG_CODE:
        LANG_CODE = os.environ.get('LANG', 'en_US')
except:
    LANG_CODE = 'en_US'


TR = {
    'es': {
        'lock': 'Bloquear',
        'logout': 'Cerrar sesión',
        'suspend': 'Suspender',
        'reboot': 'Reiniciar',
        'shutdown': 'Apagar',
        'hibernate': 'Hibernar',
        'confirm_logout': '¿Cerrar sesión?',
        'confirm_reboot': '¿Reiniciar el sistema?',
        'confirm_shutdown': '¿Apagar el sistema?',
        'yes': 'Sí',
        'no': 'No',
        'prompt': 'Power'
    },
    'en': {
        'lock': 'Lock',
        'logout': 'Logout',
        'suspend': 'Suspend',
        'reboot': 'Reboot',
        'shutdown': 'Shutdown',
        'hibernate': 'Hibernate',
        'confirm_logout': 'Logout?',
        'confirm_reboot': 'Reboot system?',
        'confirm_shutdown': 'Shutdown system?',
        'yes': 'Yes',
        'no': 'No',
        'prompt': 'Power'
    }
}


L = TR['es'] if str(LANG_CODE).lower().startswith('es') else TR['en']

def dmenu_cmd(num_lines, prompt="Power"):
    MIN_LINES = 1
    MAX_LINES = 10
    current_lines = max(MIN_LINES, min(num_lines, MAX_LINES))
    
    return [
        "rofi", "-dmenu", 
        "-p", prompt, 
        "-theme", ROFI_THEME, 
        "-i", 
        "-markup-rows", 
        "-l", str(current_lines)
    ]

def get_selection(options, prompt="Power"):

    if not options:
        return None
    
    cmd = dmenu_cmd(len(options), prompt)
    inp = "\n".join(options)
    
    try:
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding=ENC
        )
        stdout, _ = process.communicate(input=inp)
        return stdout.strip()
    except Exception:
        return None

def confirm_action(message):

    options = [
        f"<span foreground='{WHITE}'>{L['yes']}</span>",
        f"<span foreground='{GRAY}'>{L['no']}</span>"
    ]
    
    sel = get_selection(options, prompt=message)
    if not sel:
        return False
    
    # Strip markup to compare
    import re
    text_only = re.sub(r'<[^>]+>', '', sel).strip()
    return text_only == L['yes']

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

def lock_screen():

    subprocess.run(["hyprlock"], check=False)

def logout_session():

    if confirm_action(L['confirm_logout']):
        subprocess.run(["hyprctl", "dispatch", "exit"], check=False)

def suspend_system():

    subprocess.run(["systemctl", "suspend"], check=False)

def reboot_system():

    if confirm_action(L['confirm_reboot']):
        subprocess.run(["systemctl", "reboot"], check=False)

def shutdown_system():

    if confirm_action(L['confirm_shutdown']):
        subprocess.run(["systemctl", "poweroff"], check=False)

def hibernate_system():

    subprocess.run(["systemctl", "hibernate"], check=False)

def main():

    actions = []
    

    actions.append(Action(
        f"<span foreground='#ffff00'>󰌾</span>  <span foreground='#FFFFFF'>{L['lock']}</span>",
        lock_screen
    ))
    

    actions.append(Action(
        f"<span foreground='#ff8800'>󰍃</span>  <span foreground='#FFFFFF'>{L['logout']}</span>",
        logout_session
    ))
    

    actions.append(Action(
        f"<span foreground='#aa00ff'>󰖔</span>  <span foreground='#FFFFFF'>{L['suspend']}</span>",
        suspend_system
    ))
    

    actions.append(Action(
        f"<span foreground='#00ddff'>󰒲</span>  <span foreground='#FFFFFF'>{L['hibernate']}</span>",
        hibernate_system
    ))
    

    actions.append(Action(
        f"<span foreground='#00ff00'>󰑓</span>  <span foreground='#FFFFFF'>{L['reboot']}</span>",
        reboot_system
    ))
    

    actions.append(Action(
        f"<span foreground='#ff0000'>󰐥</span>  <span foreground='#FFFFFF'>{L['shutdown']}</span>",
        shutdown_system
    ))
    

    inp = [str(a) for a in actions]
    sel = get_selection(inp, prompt=L['prompt'])
    
    if not sel:
        sys.exit(0)
    

    for action in actions:
        if str(action).strip() == sel.strip():
            action()
            break

if __name__ == "__main__":
    main()
