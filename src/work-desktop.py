#!/usr/bin/python3
"""Run the private compositor; start apps only in its display environment."""
import os
from pathlib import Path
import subprocess
import sys

HOME = Path.home()
CONFIG = HOME / '.config/hypr/hyprland.lua'

def main():
    env = os.environ.copy()
    env['DUOOMARCHY_MODE'] = 'work'
    library = HOME / '.local/share/duoomarchy-work-lib'
    if library.is_dir():
        env['LD_LIBRARY_PATH'] = str(library)
    for key in ('HYPRLAND_INSTANCE_SIGNATURE', 'HYPRLAND_CONFIG', 'DISPLAY', 'XAUTHORITY'):
        env.pop(key, None)
    return subprocess.call(['/usr/bin/Hyprland', '--config', str(CONFIG)], env=env)

if __name__ == '__main__': sys.exit(main())
