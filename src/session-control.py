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

HOME=Path.home()
SOCKET=HOME/'.duoomarchy-control.sock'

def launch(command):
    subprocess.Popen(command,stdin=subprocess.DEVNULL,start_new_session=True)

def dispatch(action):
    if action=='ping':return {'ok':True,'message':'Sessão pronta'}
    if action=='steam_open':
        launch(['/usr/bin/steam','-desktop','-language','brazilian','-nochatui','-nofriendsui'])
    elif action=='steam_close':
        launch(['/usr/bin/steam','-shutdown'])
    elif action=='overwatch':
        launch(['/usr/bin/steam','-applaunch','2357570'])
    elif action=='browser_open':
        browser=shutil.which('chromium') or shutil.which('google-chrome-stable')
        if not browser:return {'ok':False,'message':'Instale chromium para abrir o navegador.'}
        # Dedicated profile; cannot attach to the primary player's Chromium.
        launch([browser,'--ozone-platform=x11','--user-data-dir='+str(HOME/'.config/duoomarchy-browser'),'--no-first-run','--new-window','about:blank'])
    else:return {'ok':False,'message':'Comando desconhecido'}
    return {'ok':True,'message':'Comando enviado à sessão do segundo jogador'}

def serve(autostart=True):
    os.umask(0o077)
    if SOCKET.exists():SOCKET.unlink()
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(SOCKET));server.listen(4)
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
                    conn.sendall(json.dumps(result,ensure_ascii=False).encode()+b'\n')
        finally:SOCKET.unlink(missing_ok=True)

if __name__=='__main__':serve('--no-autostart' not in sys.argv)
