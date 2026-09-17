#!/usr/bin/python3
"""Install user files without starting a game or taking any input device."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def install(home, reload_systemd=True):
    data = home / '.local/share/duoomarchy'
    bindir = home / '.local/bin'
    configdir = home / '.config/duoomarchy'
    units = home / '.config/systemd/user'
    aliases = ('duoomarchy', 'jogarduosim', 'jogarduonao')
    target = data / 'duoomarchy.py'
    for name in aliases:
        dest = bindir / name
        if (dest.exists() or dest.is_symlink()) and (not dest.is_symlink() or dest.resolve() != target.resolve()):
            raise RuntimeError(f'Existing command preserved: {dest}. Rename it yourself before installing.')
    for folder in (data, bindir, configdir, units, data/'logs', data/'player2/.local/bin', home/'.config/hypr'):
        folder.mkdir(parents=True, exist_ok=True)
    (data/'player2').chmod(0o700)
    for name in ('duoomarchy.py', 'session.py', 'manager.py'):
        shutil.copy2(ROOT/'src'/name, data/name)
        (data/name).chmod(0o755)
    wrapper=data/'player2/.local/bin/duoomarchy-overwatch'
    shutil.copy2(ROOT/'src/overwatch.py', wrapper); wrapper.chmod(0o755)
    shutil.copy2(ROOT/'src/session-control.py', data/'player2/.local/bin/duoomarchy-session-control')
    (data/'player2/.local/bin/duoomarchy-session-control').chmod(0o755)
    for name in aliases:
        dest=bindir/name
        if not dest.is_symlink():dest.symlink_to(target)
    config=configdir/'config.json'
    if not config.exists():
        players=[{'name':name,'monitor':'','keyboard':'','mouse':'','fps':120}
                 for name in ('Principal','Segundo jogador')]
        players[1].update(backend='wayland',gpu='',gpu_name='')
        config.write_text(json.dumps({'players':players},indent=2,ensure_ascii=False)+'\n')
        config.chmod(0o600)
    # Use systemd specifiers so spaces in a home path do not split arguments.
    (units/'duoomarchy.service').write_text('''[Unit]
Description=DuoOmarchy second-player session
After=graphical-session.target
PartOf=graphical-session.target
[Service]
Type=simple
Slice=duoomarchy.slice
MemoryLow=16G
MemorySwapMax=0
ExecStart="%h/.local/share/duoomarchy/duoomarchy.py" serve
ExecStopPost="%h/.local/share/duoomarchy/duoomarchy.py" restore
KillMode=control-group
TimeoutStopSec=25
Restart=no
''')
    (units/'duoomarchy.slice').write_text('''[Unit]
Description=DuoOmarchy resource group
[Slice]
CPUWeight=100
MemoryLow=20G
''')
    hypr=home/'.config/hypr/hyprland.lua'
    module=home/'.config/hypr/duoomarchy.lua'
    if not module.exists():module.write_text('-- DuoOmarchy writes rules for its own window when activated.\n')
    include='require("hypr.duoomarchy")'
    if hypr.exists():
        text=hypr.read_text()
        if include not in text:
            backup=hypr.with_suffix('.lua.before-duoomarchy')
            if not backup.exists():shutil.copy2(hypr,backup)
            hypr.write_text(text.rstrip()+'\n'+include+'\n')
    else:
        print('Add require("hypr.duoomarchy") to your Omarchy Lua config before starting.')
    apps=home/'.local/share/applications';apps.mkdir(parents=True,exist_ok=True)
    (apps/'duoomarchy-manager.desktop').write_text('[Desktop Entry]\nType=Application\nName=DuoOmarchy — Gerenciador\nComment=Controle a segunda estação pelo seu desktop\nExec="'+str(data/'manager.py')+'"\nIcon=input-gaming\nTerminal=false\nCategories=Game;Settings;\n')
    if reload_systemd:subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    print('Installed. Build Gamescope, then run: duoomarchy configurar')
    print('No game was launched and no input was captured.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--home',type=Path,default=Path.home());ap.add_argument('--no-systemd',action='store_true')
    args=ap.parse_args();install(args.home.resolve(),not args.no_systemd)
