#!/usr/bin/python3
"""Small local control endpoint INSIDE the second player's namespace."""
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time
import threading

HOME=Path.home()
SOCKET=HOME/'.duoomarchy-control.sock'
DESKTOP_READY=False

def launch(command):
    subprocess.Popen(command,stdin=subprocess.DEVNULL,start_new_session=True)

def dispatch(action):
    if action=='ping':
        ready=True
        if os.environ.get('DUOOMARCHY_MODE')=='work':
            try:
                result=subprocess.run(['hyprctl','-j','monitors'],capture_output=True,text=True,timeout=2,check=True)
                ready=DESKTOP_READY and any(m.get('width',0)>0 and m.get('height',0)>0 for m in json.loads(result.stdout))
            except (OSError,ValueError,subprocess.SubprocessError):ready=False
        return {'ok':True,'message':'Sessão pronta' if ready else 'Desktop iniciando', 'ready':ready,
        'mode':os.environ.get('DUOOMARCHY_MODE','game'),
        'wayland_display':os.environ.get('WAYLAND_DISPLAY',''),
        'display':os.environ.get('DISPLAY',''),
        'hyprland_instance':os.environ.get('HYPRLAND_INSTANCE_SIGNATURE','')}
    if action=='steam_open':
        launch(['/usr/bin/steam','-desktop','-language','brazilian','-nochatui','-nofriendsui'])
    elif action=='steam_close':
        launch(['/usr/bin/steam','-shutdown'])
    elif action=='overwatch':
        launch(['/usr/bin/steam','-applaunch','2357570'])
    elif action=='browser_open':
        if os.environ.get('DUOOMARCHY_MODE')=='work':launch(['omarchy-launch-browser','about:blank'])
        else:
            browser=shutil.which('chromium') or shutil.which('google-chrome-stable')
            if not browser:return {'ok':False,'message':'Instale chromium para abrir o navegador.'}
            launch([browser,'--ozone-platform=x11','--user-data-dir='+str(HOME/'.config/duoomarchy-browser'),'--no-first-run','--new-window','about:blank'])
    elif action=='terminal':launch(['omarchy-launch-terminal'])
    elif action=='files':launch(['/usr/bin/nautilus','--new-window',str(HOME/'Compartilhado') if os.environ.get('DUOOMARCHY_MODE')=='work' else str(HOME)])
    elif action in ('codex','claude'):
        launch(['/usr/bin/foot','-T',action.capitalize(),'-e','/bin/bash','-c',str(HOME/'.local/bin'/action)+'; exec /bin/bash'])
    else:return {'ok':False,'message':'Comando desconhecido'}
    return {'ok':True,'message':'Comando enviado à sessão do segundo usuário'}

def desktop_start():
    global DESKTOP_READY
    # Local D-Bus activation only. Do not import environment into host systemd.
    subprocess.run(['dbus-update-activation-environment','DISPLAY','WAYLAND_DISPLAY',
                    'XDG_CURRENT_DESKTOP','HYPRLAND_INSTANCE_SIGNATURE'],check=False)
    for _ in range(60):
        try:
            if subprocess.run(['omarchy-shell','shell','ping'],capture_output=True,timeout=2).returncode==0:
                DESKTOP_READY=True
                break
        except (OSError,subprocess.TimeoutExpired):pass
        time.sleep(.2)
    startup=os.environ.get('DUOOMARCHY_STARTUP','menu')
    if DESKTOP_READY:
        if startup=='menu':launch(['omarchy-menu','summon','apps'])
        elif startup in ('terminal','browser'):dispatch('browser_open' if startup=='browser' else startup)

def send(action):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(5);client.connect(str(SOCKET))
        client.sendall(json.dumps({'action':action}).encode()+b'\n')
        return json.loads(client.recv(4096))

def serve(autostart=True,work_start=False):
    os.umask(0o077)
    if SOCKET.exists():SOCKET.unlink()
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(SOCKET));server.listen(4)
        if work_start:threading.Thread(target=desktop_start,daemon=True).start()
        if autostart:dispatch('steam_open')
        try:
            while True:
                conn,_=server.accept()
                with conn:
                    conn.settimeout(3)
                    _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid!=os.getuid():continue
                    try:
                        data=b''
                        while b'\n' not in data and len(data)<4096:
                            part=conn.recv(4096-len(data))
                            if not part:break
                            data+=part
                        request=json.loads(data)
                        result=dispatch(request.get('action'))
                    except (ValueError,OSError,AttributeError) as exc:
                        result={'ok':False,'message':str(exc)}
                    try:conn.sendall(json.dumps(result,ensure_ascii=False).encode()+b'\n')
                    except OSError:pass
        finally:SOCKET.unlink(missing_ok=True)

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--send':
        result=send(sys.argv[2]);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['ok'] else 1)
    serve('--no-autostart' not in sys.argv, '--desktop-start' in sys.argv)
