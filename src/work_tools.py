#!/usr/bin/python3
"""Reuse machine tools/configuration with station-local processes and state."""
import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import sys

SHARED_PATHS = (
    '.codex/config.toml', '.codex/keybindings.json', '.codex/AGENTS.md', '.codex/hooks.json', '.codex/plugins',
    '.claude/settings.json', '.claude/CLAUDE.md', '.claude/hooks', '.claude/plugins',
    '.grok/config.toml', '.grok/sandbox.toml', '.grok/AGENTS.md', '.grok/hooks', '.grok/bin', '.grok/bundled', '.grok/vendor',
    '.hermes/config.yaml', '.hermes/profile.yaml', '.hermes/skills', '.hermes/hooks', '.hermes/hermes-agent', '.hermes/tools',
    '.pi/agent/settings.json', '.pi/agent/models.json', '.pi/agent/models-store.json', '.pi/agent/AGENTS.md', '.pi/agent/extensions', '.pi/agent/themes', '.pi/agent/bin',
    '.omp/agent/config.yml', '.omp/agent/models.yml', '.omp/agent/AGENTS.md',
    '.config/opencode/opencode.json', '.config/opencode/tui.json', '.config/opencode/tui.jsonc', '.config/opencode/AGENTS.md', '.config/opencode/plugins', '.config/opencode/node_modules',
    '.config/cursor/cli-config.json', '.cursor/permissions.json', '.cursor/cli-config.json', '.cursor/mcp.json', '.cursor/hooks.json', '.cursor/skills', '.cursor/rules',
    '.config/devin/config.json', '.config/devin/skills', '.local/share/devin', '.local/share/cursor-agent',
    '.jcode/config.toml', '.jcode/mcp.json', '.jcode/skills', '.jcode/builds',
    '.gemini/settings.json', '.gemini/GEMINI.md', '.gemini/antigravity-cli/settings.json', '.gemini/antigravity-cli/bin', '.gemini/antigravity-cli/builtin',
    '.local/opt/maestri',
)
# Dependency generation leases/locks are part of the shared install, not user sessions.
SHARED_WRITABLE_PATHS = ('.hermes/installs',)
TOOLS = {
    'codex': ('.local/share/mise/installs/codex/latest/bin/codex', ['--dangerously-bypass-approvals-and-sandbox'], {}),
    'claude': ('.local/share/mise/installs/claude/latest/claude', ['--dangerously-skip-permissions'], {}),
    'grok': ('.grok/bin/grok', ['--always-approve'], {}),
    'hermes': ('.hermes/hermes-agent/.hermes/bin/hermes', [], {'HERMES_YOLO_MODE':'true'}),
    'pi': ('.local/share/mise/installs/pi/latest/pi/pi', [], {}),
    'omp': ('.local/share/mise/installs/github-can1357-oh-my-pi/latest/omp', ['--auto-approve'], {}),
    'opencode': ('.local/share/mise/installs/opencode/latest/opencode', [], {'OPENCODE_PERMISSION':'{"*":"allow"}'}),
    'agent': ('.local/share/cursor-agent/versions/current/cursor-agent', ['--force'], {}),
    'devin': ('.local/share/devin/cli/_versions/current/bin/devin', [], {'DEVIN_PERMISSION_MODE':'dangerous'}),
    'jcode': ('.jcode/builds/current/jcode', ['--no-update'], {}),
    'agy': ('.local/share/duoomarchy-host-bin/agy', ['--dangerously-skip-permissions'], {}),
}

def seed_maestri(profile, source_home):
    # The app renews its license cache; keep those writes in the private profile.
    marker=profile/'.config/duoomarchy-work/maestri-license-seeded'
    if not marker.exists():
        for name in ('license.json','.license-credentials.json'):
            source=source_home/'.maestri'/name;target=profile/'.maestri'/name
            if source.is_file():
                target.parent.mkdir(parents=True,exist_ok=True)
                temporary=target.with_name(name+'.duoomarchy-seed.tmp')
                shutil.copy2(source,temporary);temporary.chmod(0o600);temporary.replace(target)
        marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('Private license cache initialized.\n')
    destination=profile/'.maestri/preferences.json'
    if destination.exists():return
    source=source_home/'.maestri/preferences.json'
    settings=json.loads(source.read_text()) if source.exists() else {'payload':{},'schemaVersion':1,'type':'preferences'}
    payload=settings.setdefault('payload',{})
    payload.update(sshEnabled=False,sshAddToPath=False,sshTunnelPort=7434,remoteCompanionEnabled=False)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n');destination.chmod(0o600)

def install(profile, source_home):
    tools={}
    bin_dir=profile/'.local/bin';apps=profile/'.local/share/applications'
    apps.mkdir(parents=True,exist_ok=True)
    for name,(relative,flags,environment) in TOOLS.items():
        source=source_home/relative
        if name in ('agent','devin'):
            launcher=source_home/'.local/bin'/name
            if launcher.exists():source=launcher.resolve();relative=str(source.relative_to(source_home))
        if name=='agy':source=source_home/'.local/bin/agy'
        if not source.is_file():continue
        tools[name]={'path':relative,'args':flags,'env':environment}
        wrapper=bin_dir/name
        if wrapper.is_symlink():wrapper.unlink()
        shutil.copy2(__file__,wrapper);wrapper.chmod(0o755)
        display={'agent':'Cursor Agent','agy':'Antigravity','omp':'Oh My Pi'}.get(name,name.capitalize())
        (apps/f'duoomarchy-{name}.desktop').write_text(f'[Desktop Entry]\nType=Application\nName={display}\nComment=Terminal com configuração compartilhada e permissões liberadas\nExec=omarchy-launch-tui {name}\nIcon=utilities-terminal\nTerminal=false\nCategories=Development;\n')
    settings=profile/'.config/duoomarchy-work/tools.json'
    settings.write_text(json.dumps(tools,indent=2)+'\n')
    for name in ('maestri','maestri-abrir'):
        target=bin_dir/name
        if target.is_symlink():target.unlink()
        shutil.copy2(__file__,target);target.chmod(0o755)
    if (source_home/'.local/opt/maestri/current/maestri-app').exists():
        seed_maestri(profile,source_home)
        (apps/'duoomarchy-maestri.desktop').write_text('[Desktop Entry]\nType=Application\nName=Maestri\nComment=Canvas próprio da segunda estação\nExec=maestri-abrir\nIcon=utilities-terminal\nTerminal=false\nCategories=Development;\n')

def maestri_identity(home, environ, proc_root=Path('/proc')):
    environment=dict(environ)
    session=environment.get('JCODE_SESSION_ID')
    if not session:return environment
    matches=[]
    for path in (home/'.jcode/client_sessions').glob('*'):
        try:
            if path.name.isdigit() and path.read_text().strip()==session:matches.append(path)
        except OSError:continue
    for path in sorted(matches,key=lambda p:p.stat().st_mtime,reverse=True):
        try:entries=(proc_root/path.name/'environ').read_bytes().split(b'\0')
        except OSError:continue
        for entry in entries:
            key,sep,value=entry.partition(b'=')
            if sep and key in (b'MAESTRI_TERMINAL_ID',b'MAESTRI_SOCKET',b'MAESTRI_WORKSPACE_ID'):
                environment[key.decode()]=value.decode()
        break
    return environment

def invocation(name, arguments, home, environ):
    environment=dict(environ)
    if name=='maestri':
        environment=maestri_identity(home,environment)
        cli=home/'.local/opt/maestri/current/resources/cli/maestri'
        if not environment.get('MAESTRI_SOCKET') or not environment.get('MAESTRI_TERMINAL_ID'):
            raise RuntimeError('Use maestri dentro de um terminal do Maestri desta estação. Pra abrir o app: maestri-abrir.')
        return [str(cli),*arguments],environment
    if name=='maestri-abrir':
        bundle=home/'.local/opt/maestri/current'
        for key in list(environment):
            if key.startswith('MAESTRI_'):environment.pop(key)
        environment.update(MAESTRI_CORE_BIN=str(bundle/'resources/cli/maestri'),MAESTRI_DATA_DIR=str(home/'.maestri'))
        return [str(bundle/'maestri-app'),f'--user-data-dir={home}/.config/duoomarchy-maestri','--ozone-platform=x11',*arguments],environment
    tools=json.loads((home/'.config/duoomarchy-work/tools.json').read_text())
    tool=tools[name];environment.update(tool['env'])
    return [str(home/tool['path']),*tool['args'],*arguments],environment

def main():
    try:arguments,environment=invocation(Path(sys.argv[0]).name,sys.argv[1:],Path.home(),os.environ)
    except (RuntimeError,KeyError) as error:sys.exit(str(error))
    if Path(sys.argv[0]).name in ('opencode','jcode') and (Path.home()/'.jcode/provider-9router.env').is_file():
        os.execve('/bin/bash',['bash','-c','set -a; . "$HOME/.jcode/provider-9router.env"; exec "$@"','duoomarchy',*arguments],environment)
    os.execve(arguments[0],arguments,environment)

if __name__=='__main__':main()
