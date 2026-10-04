#!/usr/bin/python3
"""Adapt Omarchy app launchers to an independent desktop session."""
import os
from pathlib import Path
import shlex
import subprocess
import sys

HOME=Path.home()

def main():
    name=Path(sys.argv[0]).name;args=sys.argv[1:]
    if name=='uwsm-app':
        if '--' in args:args=args[args.index('--')+1:]
        if not args:raise SystemExit('Aplicativo ausente.')
        os.execvp(args[0],args)
    elif name=='omarchy-launch-shell':
        os.environ.update(QS_DISABLE_FILE_WATCHER='1',QS_NO_RELOAD_POPUP='1')
        os.execvp('quickshell',['quickshell','-n','-p',os.environ.get('OMARCHY_PATH','/usr/share/omarchy')+'/shell'])
    elif name=='omarchy-launch-browser':
        desktop=subprocess.run(['xdg-settings','get','default-web-browser'],capture_output=True,text=True).stdout.strip()
        command=None
        for folder in (HOME/'.local/share/applications',Path('/usr/share/applications')):
            path=folder/desktop if desktop else None
            if path and path.is_file():
                line=next((x[5:] for x in path.read_text().splitlines() if x.startswith('Exec=')),None)
                if line:command=[x for x in shlex.split(line) if not x.startswith('%')];break
        if not command:command=['/usr/bin/chromium']
        private='--private-window' if 'firefox' in command[0] else '--incognito'
        args=[private if x=='--private' else x for x in args]
        os.execvp(command[0],command+args)
    elif name=='omarchy-system-logout':
        subprocess.run(['hyprctl','dispatch','hl.dsp.exit()'],check=True)
    else:raise SystemExit('Launcher desconhecido.')

if __name__=='__main__':main()
