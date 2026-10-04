#!/usr/bin/python3
"""Install user files without starting a game or taking any input device."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def seed_omarchy_profile(profile, source_home):
    marker=profile/'.config/duoomarchy-work/omarchy-seeded'
    if marker.exists():return
    preferences=('alacritty','ghostty','kitty','foot','fastfetch','btop','fontconfig','gtk-3.0','gtk-4.0',
                 'omarchy','mimeapps.list','user-dirs.dirs','xdg-terminals.list','starship.toml')
    for relative in preferences:
        source=source_home/'.config'/relative;target=profile/'.config'/relative
        if not source.exists() or target.exists():continue
        if source.is_dir():shutil.copytree(source,target)
        else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for relative in ('.local/state/omarchy/current','.local/state/omarchy/defaults','.local/share/applications','.local/share/icons'):
        source=source_home/relative;target=profile/relative
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,target,symlinks=True)
    for filename in ('input.lua','looknfeel.lua','bindings.lua','autostart.lua'):
        target=profile/'.config/hypr'/filename
        if not target.exists():
            source=Path('/usr/share/omarchy/config/hypr')/filename
            if source.exists():shutil.copy2(source,target)
            else:target.write_text('-- Personal Omarchy overrides.\n')
    # Carry personal styling and keyboard preferences, without host device rules.
    for filename in ('input.lua','looknfeel.lua'):
        source=source_home/'.config/hypr'/filename
        if source.exists():shutil.copy2(source,profile/'.config/hypr'/filename)
    shell=profile/'.config/omarchy/shell.json'
    if shell.exists():
        c=json.loads(shell.read_text())
        for widgets in c.get('bar',{}).get('layout',{}).values():
            for widget in widgets:
                if widget.get('id')=='sofos.workspaces':widget['minimumWorkspaces']=9
        shell.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    bash=profile/'.bashrc'
    if not bash.exists():bash.write_text('source /usr/share/omarchy/default/bashrc\nexport PATH="$HOME/.local/bin:/usr/share/omarchy/bin:$HOME/.local/share/duoomarchy-host-bin:$PATH"\n')
    for folder in ('Documents','Projects'):
        source=source_home/folder;target=profile/folder
        if source.is_dir() and (not target.exists() or (target.is_dir() and not any(target.iterdir()))):
            if target.exists():target.rmdir()
            target.symlink_to(Path('Compartilhado')/folder)
    for folder in ('Downloads','Pictures','Videos','Music','Desktop'):(profile/folder).mkdir(exist_ok=True)
    bin_dir=profile/'.local/bin'
    reserved={'duoomarchy-session-control','duoomarchy-work-desktop','duoomarchy-work-menu','codex','claude','grok','agent-bench','uwsm-app','omarchy-launch-shell','omarchy-launch-browser','omarchy-system-logout'}
    for source in (source_home/'.local/bin').glob('*'):
        if source.name in reserved:continue
        target=bin_dir/source.name
        if not target.exists() and not target.is_symlink():target.symlink_to(Path('../share/duoomarchy-host-bin')/source.name)
    marker.write_text('Omarchy profile initialized. Preferences belong to this station.\n')

def install_work_profile(data, source_home=None):
    (data/'player2/.grok').mkdir(parents=True,exist_ok=True)
    for relative in ('.local/bin','.config/duoomarchy-work','.config/hypr','.codex','.claude','Compartilhado'):
        (data/'player2'/relative).mkdir(parents=True,exist_ok=True)
    if source_home is not None:seed_omarchy_profile(data/'player2',source_home)
    shutil.copy2(ROOT/'src/session-control.py', data/'player2/.local/bin/duoomarchy-session-control')
    (data/'player2/.local/bin/duoomarchy-session-control').chmod(0o755)
    for source,work_target in (('work-desktop.py','duoomarchy-work-desktop'),('work-menu.py','duoomarchy-work-menu')):
        shutil.copy2(ROOT/'src'/source,data/'player2/.local/bin'/work_target);(data/'player2/.local/bin'/work_target).chmod(0o755)
    shutil.copy2(ROOT/'data/work-hyprland.lua',data/'player2/.config/hypr/hyprland.lua')
    (data/'player2/.config/duoomarchy-work/hyprland.lua').write_text('dofile(os.getenv("HOME") .. "/.config/hypr/hyprland.lua")\n')
    for name in ('uwsm-app','omarchy-launch-shell','omarchy-launch-browser','omarchy-system-logout'):
        target=data/'player2/.local/bin'/name
        if target.is_symlink():target.unlink()
        shutil.copy2(ROOT/'src/work-launch.py',target);target.chmod(0o755)
    import importlib.util
    spec=importlib.util.spec_from_file_location('work_tools',ROOT/'src/work_tools.py')
    tools=importlib.util.module_from_spec(spec);spec.loader.exec_module(tools)
    tools.install(data/'player2',source_home or Path.home())
    bench=data/'player2/.local/bin/agent-bench'
    if bench.is_symlink():bench.unlink()
    bench.write_text('''#!/bin/sh
signature=${DUOOMARCHY_HOST_SIGNATURE:?Assinatura do desktop principal ausente}
export XDG_RUNTIME_DIR=/run/host-user
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/host-user/bus
export HYPRLAND_INSTANCE_SIGNATURE="$signature"
exec "$HOME/.agents/bin/agent-bench" "$@"
''');bench.chmod(0o755)
    shutil.copy2(ROOT/'data/work-AGENTS.md',data/'player2/AGENTS.md')
    if source_home is not None:
        import importlib.util
        spec=importlib.util.spec_from_file_location('duoomarchy_session', ROOT/'src/session.py')
        session_mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(session_mod)
        session_mod.share_machine_skills(data/'player2', source_home)

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
    for folder in (data, bindir, configdir, units, data/'logs', data/'player2/.local/bin', data/'player2/.config/duoomarchy-work', data/'player2/Projects', data/'player2/.agents', data/'player2/.codex', data/'player2/.claude', data/'player2/.grok', data/'player2/Compartilhado', home/'.config/hypr'):
        folder.mkdir(parents=True, exist_ok=True)
    (data/'player2').chmod(0o700)
    shutil.copy2(ROOT/'VERSION',data/'VERSION')
    for name in ('duoomarchy.py', 'session.py', 'manager.py', 'configurator.py', 'work_tools.py'):
        shutil.copy2(ROOT/'src'/name, data/name)
        (data/name).chmod(0o755)
    wrapper=data/'player2/.local/bin/duoomarchy-overwatch'
    shutil.copy2(ROOT/'src/overwatch.py', wrapper); wrapper.chmod(0o755)
    install_work_profile(data,home)
    for name in aliases:
        dest=bindir/name
        if not dest.is_symlink():dest.symlink_to(target)
    config=configdir/'config.json'
    if not config.exists():
        players=[{'name':name,'monitor':'','workspace':n,'workspace_locked':n==2,'keyboard':'','mouse':'','mouse_native_dpi':800,'mouse_dpi':800,'gamepad':'','extra_devices':[],
                  'sink':'','source':'','sink_volume':100,'source_volume':100,'fps':120,'resolution':'native','scaler':'fit','filter':'linear',
                  'internal_workspaces':9,'startup':'menu'}
                 for n,name in enumerate(('Principal','Segundo jogador'),1)]
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
