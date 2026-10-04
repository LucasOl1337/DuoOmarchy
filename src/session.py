#!/usr/bin/python3
"""Private Steam home and IPC; not a security boundary between hostile users."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import vdf

sys.path.insert(0,str(Path(__file__).resolve().parent))
from work_tools import SHARED_PATHS, SHARED_WRITABLE_PATHS

# CLI account sharing is explicitly authorized for this station.
# Browser cookies, conversation stores and the principal Maestri canvas stay private.

HOME = Path.home()
BASE = Path(os.environ.get('DUOOMARCHY_DATA', HOME / '.local/share/duoomarchy'))
CONFIG = Path(os.environ.get('DUOOMARCHY_CONFIG', HOME / '.config/duoomarchy/config.json'))
SKILL_DIRS = ('.claude/skills', '.grok/skills', '.codex/skills')

def share_machine_skills(private_home, host_home):
    """Link hub skills into the station CLIs. Accounts, sessions and cloud sync stay private."""
    hub = Path(host_home) / '.agents' / 'skills'
    if not hub.is_dir():
        return 0
    linked = 0
    live = {p.name for p in hub.iterdir() if (p.is_dir() or p.is_symlink()) and p.name != 'synced' and not p.name.startswith('.')}
    for relative in SKILL_DIRS:
        dest = Path(private_home) / relative
        if dest.is_symlink():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        for name in live:
            link = dest / name
            target = hub / name
            if link.is_symlink() and link.readlink() == target:
                linked += 1
                continue
            if link.exists() and not link.is_symlink():
                continue
            if link.is_symlink():
                link.unlink()
            link.symlink_to(target)
            linked += 1
        for link in list(dest.iterdir()):
            if not link.is_symlink():
                continue
            target = link.readlink()
            if target.parent == hub and link.name not in live:
                link.unlink()
    return linked

def command(home, runtime, env, work=False):
    private_runtime = Path(f'/run/user/{os.getuid()}')
    args = ['bwrap', '--die-with-parent', '--unshare-pid', '--unshare-ipc', '--unshare-uts',
            '--hostname', 'duoomarchy-player2', '--dev-bind', '/', '/', '--proc', '/proc',
            '--tmpfs', '/tmp',
            '--tmpfs', '/dev/shm', '--tmpfs', '/dev/input', '--bind', str(home), str(HOME),
            '--tmpfs', '/run', '--dir', str(private_runtime / 'pulse'),
            '--bind', str(runtime / 'pulse/native'), str(private_runtime / 'pulse/native')]
    # The network namespace is shared. Preserve the resolver behind the host's
    # /etc/resolv.conf symlink and the system bus used for network status.
    resolver = Path('/etc/resolv.conf').resolve()
    if resolver.is_file():
        if resolver.is_relative_to('/run'):
            args += ['--ro-bind', str(resolver.parent), str(resolver.parent)]
        else:
            args += ['--ro-bind', str(resolver), '/etc/resolv.conf']
    system_bus = Path('/run/dbus/system_bus_socket')
    if system_bus.exists():args += ['--ro-bind', str(system_bus), str(system_bus)]
    values = {'HOME': str(HOME), 'XDG_RUNTIME_DIR': str(private_runtime),
              'XDG_CONFIG_HOME': str(HOME / '.config'), 'XDG_DATA_HOME': str(HOME / '.local/share'),
              'XDG_CACHE_HOME': str(HOME / '.cache'), 'XDG_CURRENT_DESKTOP': 'Hyprland',
              'PULSE_SERVER': f'unix:{private_runtime}/pulse/native',
              'PATH': f'{HOME}/.local/bin:/usr/share/omarchy/bin:{HOME}/.local/share/duoomarchy-host-bin:{HOME}/.local/share/mise/shims:/usr/local/bin:/usr/bin:/bin',
              'XDG_STATE_HOME': str(HOME / '.local/state'), 'OMARCHY_PATH': '/usr/share/omarchy',
              'ENABLE_GAMESCOPE_WSI': '0', 'PULSE_PROP': 'duoomarchy.session=player2', 'DXVK_MAX_COMPILER_THREADS': '2'}
    for key in ('PULSE_SINK','PULSE_SOURCE'):
        if env.get(key):values[key]=env[key]
    if not work:
        args += ['--bind', '/tmp/.X11-unix', '/tmp/.X11-unix']
    if work:
        socket_name=env.get('GAMESCOPE_WAYLAND_DISPLAY', '')
        socket_path=runtime/socket_name if socket_name else None
        if not socket_path or not socket_path.exists():
            raise ValueError('Socket Wayland da estação ausente; não usar o desktop principal.')
        args += ['--bind',str(socket_path),str(private_runtime/socket_name)]
        values['WAYLAND_DISPLAY']=socket_name
        args += ['--bind',str(HOME),str(HOME/'Compartilhado')]
        for relative in SHARED_PATHS:
            source=HOME/relative
            if source.exists():args += ['--ro-bind',str(source),str(HOME/relative)]
        for relative in SHARED_WRITABLE_PATHS:
            source=HOME/relative
            if source.exists():args += ['--bind',str(source),str(HOME/relative)]
        host_bin=HOME/'.local/bin'
        if host_bin.is_dir():args += ['--ro-bind',str(host_bin),str(HOME/'.local/share/duoomarchy-host-bin')]
        pipewire=runtime/'pipewire-0'
        if pipewire.exists():args += ['--bind',str(pipewire),str(private_runtime/'pipewire-0')]
        tools=HOME/'.local/share/mise'
        if tools.exists():args += ['--ro-bind',str(tools),str(tools)]
        work_lib=Path(env.get('DUOOMARCHY_WORK_LIB',str(BASE/'runtime/lib')))
        if work_lib.is_dir():
            args += ['--ro-bind',str(work_lib),str(HOME/'.local/share/duoomarchy-work-lib')]
        agents=HOME/'.agents'
        if agents.exists():args += ['--ro-bind',str(agents),str(HOME/'.agents')]
        args += ['--dir','/run/host-user']
        for name in ('agent-bench','hypr'):
            source=runtime/name
            if source.exists():args += ['--bind',str(source),str(Path('/run/host-user')/name)]
        bus=runtime/'bus'
        if bus.exists():args += ['--bind',str(bus),'/run/host-user/bus']
        # An inherited Maestri/jcode identity belongs to the principal station.
        for key in env:
            if key.startswith(('MAESTRI_', 'JCODE_')):args += ['--unsetenv',key]
        values['XDG_DATA_DIRS']=f'{HOME}/Compartilhado/.local/share:/usr/local/share:/usr/share'
        values['XDG_SESSION_TYPE']='wayland';values['DUOOMARCHY_MODE']='work'
        values['DUOOMARCHY_WORKSPACES']=env.get('DUOOMARCHY_WORKSPACES','9')
        values['DUOOMARCHY_STARTUP']=env.get('DUOOMARCHY_STARTUP','menu')
        values['DUOOMARCHY_HOST_SIGNATURE']=env.get('HYPRLAND_INSTANCE_SIGNATURE','')
        values['DUOOMARCHY_NAME']=env.get('DUOOMARCHY_NAME','Segunda estação')
        args += ['--unsetenv','DISPLAY','--unsetenv','HYPRLAND_CONFIG',
                 '--unsetenv','UWSM_MANAGED','--unsetenv','UWSM_FINALIZE_VARNAMES']
    for key, value in values.items(): args += ['--setenv', key, value]
    for key in ('DBUS_SESSION_BUS_ADDRESS', 'WAYLAND_DISPLAY', 'XAUTHORITY',
                'HYPRLAND_INSTANCE_SIGNATURE', 'GAMESCOPE_WAYLAND_DISPLAY',
                'LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES'):
        if key=='WAYLAND_DISPLAY' and work:continue
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
        work=len(sys.argv)>2 and sys.argv[2]=='work'
        if work:share_machine_skills(home, HOME)
        if not work:install_launch_options(home)
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
        args = command(home, runtime, os.environ, work=work)
        config = json.loads(CONFIG.read_text())
        gpu = config['players'][1].get('gpu_name', '')
        if gpu:
            pos = args.index('--')
            args[pos:pos] = ['--setenv', 'DXVK_FILTER_DEVICE_NAME', gpu]
        child = sys.argv[3:] if work else sys.argv[2:]
        if not child:child=[str(HOME / '.local/bin/duoomarchy-work-desktop' if work else HOME / '.local/bin/duoomarchy-session-control')]
        return subprocess.run(args + child).returncode

if __name__ == '__main__': sys.exit(main())
