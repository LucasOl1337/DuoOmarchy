#!/usr/bin/python3
"""Private Steam home and IPC; not a security boundary between hostile users."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import vdf

HOME = Path.home()
BASE = Path(os.environ.get('DUOOMARCHY_DATA', HOME / '.local/share/duoomarchy'))
CONFIG = Path(os.environ.get('DUOOMARCHY_CONFIG', HOME / '.config/duoomarchy/config.json'))

def command(home, runtime, env):
    args = ['bwrap', '--die-with-parent', '--unshare-pid', '--unshare-ipc', '--unshare-uts',
            '--hostname', 'duoomarchy-player2', '--dev-bind', '/', '/', '--proc', '/proc',
            '--tmpfs', '/tmp', '--bind', '/tmp/.X11-unix', '/tmp/.X11-unix',
            '--tmpfs', '/dev/shm', '--tmpfs', '/dev/input', '--bind', str(home), str(HOME),
            '--tmpfs', str(runtime), '--dir', str(runtime / 'pulse'),
            '--bind', str(runtime / 'pulse/native'), str(runtime / 'pulse/native')]
    values = {'HOME': str(HOME), 'XDG_RUNTIME_DIR': str(runtime),
              'XDG_CONFIG_HOME': str(HOME / '.config'), 'XDG_DATA_HOME': str(HOME / '.local/share'),
              'XDG_CACHE_HOME': str(HOME / '.cache'), 'XDG_CURRENT_DESKTOP': 'Hyprland',
              'PULSE_SERVER': f'unix:{runtime}/pulse/native',
              'PATH': f'{HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin',
              'ENABLE_GAMESCOPE_WSI': '0', 'PULSE_PROP': 'duoomarchy.session=player2', 'DXVK_MAX_COMPILER_THREADS': '2'}
    for key, value in values.items(): args += ['--setenv', key, value]
    for key in ('DBUS_SESSION_BUS_ADDRESS', 'WAYLAND_DISPLAY', 'XAUTHORITY',
                'HYPRLAND_INSTANCE_SIGNATURE', 'GAMESCOPE_WAYLAND_DISPLAY',
                'LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES'):
        args += ['--unsetenv', key]
    args += ['--chdir', str(HOME), '--', 'dbus-run-session', '--']
    return args

def install_launch_options(home):
    # Steam is not running: our parent holds the profile lock for its whole lifetime.
    for path in (home / '.local/share/Steam/userdata').glob('*/config/localconfig.vdf'):
        with path.open() as f: data = vdf.load(f)
        node = data
        for key in ('UserLocalConfigStore', 'Software', 'Valve', 'Steam', 'apps', '2357570'):
            node = node.setdefault(key, {})
        wrapper = str(HOME / '.local/bin/duoomarchy-overwatch')
        old = node.get('LaunchOptions', '')
        if old.strip() and not old.startswith(wrapper + ' '): continue
        node['LaunchOptions'] = wrapper + ' %command%'
        tmp = path.with_suffix('.duo.tmp')
        with tmp.open('w') as f: vdf.dump(data, f, pretty=True)
        tmp.chmod(0o600)
        tmp.replace(path)

def main():
    if len(sys.argv) < 2 or sys.argv[1] != '2':
        sys.exit('Only player 2 is isolated. Use the normal desktop Steam for player 1.')
    home = BASE / 'player2'
    home.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (home / '.duo-profile.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: sys.exit('The second Steam profile is already open.')
        install_launch_options(home)
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
        args = command(home, runtime, os.environ)
        config = json.loads(CONFIG.read_text())
        gpu = config['players'][1].get('gpu_name', '')
        if gpu:
            pos = args.index('--')
            args[pos:pos] = ['--setenv', 'DXVK_FILTER_DEVICE_NAME', gpu]
        child = sys.argv[2:] or [str(HOME / '.local/bin/duoomarchy-session-control')]
        return subprocess.run(args + child).returncode

if __name__ == '__main__': sys.exit(main())
