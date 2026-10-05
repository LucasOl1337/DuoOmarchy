#!/usr/bin/python3
"""Two independent Steam sessions. Physical input is held only by Gamescope."""
from contextlib import closing
import fcntl
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

HOME=Path.home()
BASE=Path(os.environ.get('DUOOMARCHY_DATA', HOME/'.local/share/duoomarchy'))
CONFIG=Path(os.environ.get('DUOOMARCHY_CONFIG', HOME/'.config/duoomarchy/config.json'))
RUNTIME=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))
RUN=RUNTIME/os.environ.get('DUOOMARCHY_RUNTIME','duoomarchy')
BIN=BASE/'runtime/bin/gamescope'
SERVICE=os.environ.get('DUOOMARCHY_SERVICE','duoomarchy.service')
MODE_FILE=RUN/'requested-mode'
APP_PREFIX=os.environ.get('DUOOMARCHY_APP_ID','duoomarchy')
RULE_FILE=Path(os.environ.get('DUOOMARCHY_RULE_FILE',HOME/'.config/hypr/duoomarchy.lua'))

def run(args,check=True,**kw):
    return subprocess.run([str(x) for x in args],capture_output=True,text=True,check=check,**kw)

def normalize_config(c):
    """Migrate old profiles in memory while keeping the stored file human-readable."""
    defaults={'gamepad':'','extra_devices':[],'mouse_native_dpi':800,'mouse_dpi':800,'sink':'','source':'',
              'sink_volume':100,'source_volume':100,'fps':120,'resolution':'native',
              'scaler':'fit','filter':'linear','backend':'wayland','gpu':'','gpu_name':'',
              'internal_workspaces':9,'startup':'menu'}
    for index,p in enumerate(c.get('players',[])):
        for key,value in defaults.items():p.setdefault(key,value.copy() if isinstance(value,list) else value)
        p.setdefault('workspace_locked',index==1)
    c.setdefault('version',2)
    return c

def config(): return normalize_config(json.loads(CONFIG.read_text()))
def session_environment():
    env=os.environ.copy()
    env.update(DUOOMARCHY_DATA=str(BASE),DUOOMARCHY_CONFIG=str(CONFIG))
    return env

def active(): return run(['systemctl','--user','is-active',SERVICE],False).stdout.strip()=='active'
def monitors(): return json.loads(run(['hyprctl','-j','monitors']).stdout)

def gpu_nodes():
    """Return Gamescope Vulkan selectors from display controllers."""
    result=[]
    try: lines=run(['lspci','-nn','-D']).stdout.splitlines()
    except (OSError,subprocess.CalledProcessError):return result
    for line in lines:
        if not re.search(r' (VGA compatible controller|3D controller|Display controller) ',line,re.I):continue
        ids=re.findall(r'\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]',line)
        if not ids:continue
        name=line.split(': ',1)[-1].rsplit(' [',1)[0]
        value=':'.join(ids[-1]).lower();result.append({'id':value,'label':f'{name}  ·  {value}'})
    return result

def audio_nodes(kind):
    """Return selectable PipeWire nodes without monitor-loopback sources."""
    try:
        items=json.loads(run(['pactl','--format=json','list',kind]).stdout)
    except (OSError,ValueError,subprocess.CalledProcessError):
        return []
    return [item for item in items if not item.get('name','').endswith('.monitor')]

def devices():
    from evdev import InputDevice, ecodes as e
    aliases={str(p.resolve()):str(p) for p in sorted(Path('/dev/input/by-id').glob('*event*'))}
    result=[]
    for p in sorted(Path('/dev/input').glob('event*')):
        try:
            with closing(InputDevice(str(p))) as d:
                if not d.phys.startswith('usb-'): continue
                caps=d.capabilities(); keys=caps.get(e.EV_KEY,[]); rel=caps.get(e.EV_REL,[])
                kind=('gamepad' if e.BTN_GAMEPAD in keys or e.BTN_SOUTH in keys
                      else 'keyboard' if e.KEY_A in keys and e.KEY_Z in keys
                      else 'mouse' if e.REL_X in rel and e.BTN_LEFT in keys else 'aux')
                result.append({'path':aliases.get(str(p),str(p)), 'real':str(p),'name':d.name.strip(),'phys':d.phys,'kind':kind,'usable':e.EV_KEY in caps and any(tag in run(['udevadm','info','-q','property','-n',str(p)]).stdout.splitlines() for tag in ('ID_INPUT_KEYBOARD=1','ID_INPUT_KEY=1','ID_INPUT_MOUSE=1','ID_INPUT_JOYSTICK=1'))})
        except (OSError,PermissionError): pass
    return result

def held_devices(player):
    all_devices=devices(); chosen=[]
    roots=set()
    for kind in ('keyboard','mouse','gamepad'):
        p=player.get(kind,'')
        if kind=='gamepad' and not p:continue
        match=next((d for d in all_devices if d['real']==str(Path(p).resolve())),None)
        if not match or match['kind']!=kind: raise ValueError(f"{player['name']}: {kind} ausente/inválido: {p or '(não configurado)'}")
        roots.add(match['phys'].split('/input')[0])
    for path in player.get('extra_devices',[]):
        match=next((d for d in all_devices if d['real']==str(Path(path).resolve())),None)
        if not match or not match['usable']:raise ValueError(f"{player['name']}: periférico extra ausente/inválido: {path}")
        roots.add(match['phys'].split('/input')[0])
    for d in all_devices:
        if d['usable'] and d['phys'].split('/input')[0] in roots: chosen.append(d['real'])
    return sorted(set(chosen))

def validate(c,display=True,profiles=True):
    ps=c['players']
    if len(ps)!=2: raise ValueError('Configure exatamente dois jogadores.')
    if ps[0]['monitor']==ps[1]['monitor']: raise ValueError('Escolha monitores diferentes.')
    groups=[held_devices(p) for p in ps]
    if set(groups[0]) & set(groups[1]): raise ValueError('Os dois kits compartilham dispositivos. Escolha um kit por pessoa.')
    ms={m['name']:m for m in monitors()} if display else {}
    for index,p in enumerate(ps,1):
        if not p.get('workspace') and display and p.get('monitor') in ms:
            p['workspace']=ms[p['monitor']]['activeWorkspace']['id']
        p.setdefault('workspace',index)
        if not 30<=int(p['fps'])<=240: raise ValueError('FPS deve ficar entre 30 e 240.')
        if not 0<=int(p.get('sink_volume',100))<=150:raise ValueError('Volume deve ficar entre 0 e 150%.')
        if not 0<=int(p.get('source_volume',100))<=150:raise ValueError('Ganho do microfone deve ficar entre 0 e 150%.')
        if not 1<=int(p.get('internal_workspaces',9))<=9:raise ValueError('Use entre 1 e 9 workspaces internos.')
        if not 100<=int(p.get('mouse_native_dpi',800))<=42000:raise ValueError('O DPI físico deve ficar entre 100 e 42000.')
        if not 100<=int(p.get('mouse_dpi',800))<=42000:raise ValueError('O DPI desejado deve ficar entre 100 e 42000.')
        if p.get('resolution','native')!='native' and not re.fullmatch(r'\d{3,4}x\d{3,4}',p['resolution']):raise ValueError('Resolução interna inválida.')
        if p.get('scaler','fit') not in ('auto','integer','fit','fill','stretch'):raise ValueError('Encaixe de imagem inválido.')
        if p.get('filter','linear') not in ('linear','nearest','fsr','nis','pixel'):raise ValueError('Filtro de imagem inválido.')
        if p.get('startup','menu') not in ('menu','terminal','browser','none'):raise ValueError('Aplicativo inicial inválido.')
        if display:
            if p['monitor'] not in ms: raise ValueError(f"Monitor {p['monitor']} desconectado.")
            w=ms[p['monitor']]['activeWorkspace']['id']
            if index==2 and not 1<=w<=5: raise ValueError(f"Volte o monitor {p['monitor']} a um workspace humano (1–5) antes de ativar.")
    workspaces=[int(p['workspace']) for p in ps]
    if any(w not in range(1,6) for w in workspaces):raise ValueError('Escolha workspaces humanos entre 1 e 5.')
    if workspaces[0]==workspaces[1]:raise ValueError('Escolha workspaces diferentes.')
    for n in ((2,) if profiles else ()):
        with (BASE/f'player{n}'/'.duo-profile.lock').open('a') as handle:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError(f'A Steam do jogador {n} já está aberta em outra sessão duo. Encerre essa sessão primeiro.')
    if ps[1].get('backend','wayland') not in ('wayland','sdl'):raise ValueError('Backend deve ser wayland ou sdl.')
    for device in groups[1]:
        if not os.access(device,os.R_OK):raise ValueError('Sem acesso ao dispositivo: '+device+' (consulte docs/INSTALL.md)')
    if not BIN.is_file(): raise ValueError('Gamescope duo não instalado.')
    return groups,ms

def rule(p,n,m):
    workspace=int(p.get('workspace') or m['activeWorkspace']['id'])
    return 'hl.window_rule({name='+json.dumps(APP_PREFIX+'-'+str(n))+',match={class='+json.dumps('^'+re.escape(APP_PREFIX)+r'[.]player'+str(n)+'$')+'},monitor='+json.dumps(p['monitor'])+',workspace='+json.dumps(str(workspace)+' silent')+',fullscreen_state="2 2",suppress_event="fullscreen maximize",no_initial_focus=true,no_anim=true,content="game",idle_inhibit="always"})'

def write_rules(c,ms):
    f=RULE_FILE
    s='-- Generated by jogarduo. Only its own compositor windows match.\n'
    s+='if duo_rules then for _,r in ipairs(duo_rules) do pcall(function() r:remove() end) end end\nduo_rules={}\n'
    s+='if duo_workspace_rules then for _,r in ipairs(duo_workspace_rules) do pcall(function() r:set_enabled(false) end) end end\nduo_workspace_rules={}\n'
    for p in c['players']:
        if p.get('workspace_locked'):
            s+='table.insert(duo_workspace_rules,hl.workspace_rule({workspace='+json.dumps(str(p['workspace']))+',monitor='+json.dumps(p['monitor'])+',persistent=true}))\n'
    for n,p in [(2,c['players'][1])]:s+='table.insert(duo_rules,'+rule(p,n,ms[p['monitor']])+')\n'
    f.write_text(s)
    run(['hyprctl','reload'])
    errors=run(['hyprctl','configerrors']).stdout.strip()
    if errors and errors!='ok':raise ValueError('Configuração Hyprland: '+errors)

def apply_audio_profile(p):
    """Apply initial levels only to explicitly selected dedicated nodes."""
    if p.get('sink'):run(['pactl','set-sink-volume',p['sink'],str(int(p.get('sink_volume',100)))+'%'],False)
    if p.get('source'):run(['pactl','set-source-volume',p['source'],str(int(p.get('source_volume',100)))+'%'],False)

def route_primary_audio(p):
    """Route ordinary desktop apps to player one's selected defaults for this session."""
    previous={}
    for kind,field in (('sink','sink'),('source','source')):
        selected=p.get(field,'')
        if not selected:continue
        old=run(['pactl',f'get-default-{kind}'],False).stdout.strip()
        if old:previous['old_'+kind]=old
        run(['pactl',f'set-default-{kind}',selected],False);previous['set_'+kind]=selected
    apply_audio_profile(p)
    return previous

def render_size(p,m):
    if p.get('resolution','native')=='native':return int(m['width']),int(m['height'])
    width,height=p['resolution'].split('x',1);return int(width),int(height)

def gamescope_command(p,m,devices,mode):
    width,height=render_size(p,m)
    mouse_scale=int(p.get('mouse_dpi',800))/int(p.get('mouse_native_dpi',800))
    cmd=[str(BIN),'--backend',p.get('backend','wayland'),'-f','--backend-disable-keyboard','--backend-disable-mouse','-g',
         '-W',str(m['width']),'-H',str(m['height']),'-w',str(width),'-h',str(height),'-r',str(p['fps']),'-o',str(p['fps']),
         '-S',p.get('scaler','fit'),'-F',p.get('filter','linear'),'-s',f'{mouse_scale:.4f}']
    if p.get('gpu'):cmd+=['--prefer-vk-device',p['gpu']]
    for device in devices:cmd+=['--libinput-hold-dev',device]
    cmd+=['--',str(BASE/'session.py'),'2']
    if mode=='work':
        cmd.insert(cmd.index('--'),'--expose-wayland')
        cmd.append('work')
    return cmd

def keep_station_reserved(p):
    """Keep the dedicated station on its monitor and fullscreen without focusing it."""
    if not p.get('workspace_locked'):return
    try:clients=json.loads(run(['hyprctl','-j','clients']).stdout)
    except (ValueError,subprocess.CalledProcessError):return
    target=next((client for client in clients if client.get('class')==APP_PREFIX+'.player2'),None)
    if not target:return
    if target.get('workspace',{}).get('id')!=int(p['workspace']) or target.get('monitor')!=next((m['id'] for m in monitors() if m['name']==p['monitor']),None):
        run(['hyprctl','dispatch','movetoworkspacesilent',f"{p['workspace']},address:{target['address']}"],False)
    if target.get('fullscreen')!=2 or target.get('fullscreenClient')!=2:
        # Mapping through Gamescope can drop the initial static fullscreen rule.
        # Address the station explicitly; never act on the focused human window.
        operation='hl.dsp.window.fullscreen_state({internal=2,client=2,action="set",layout_aware=false,window='+json.dumps('address:'+target['address'])+'})'
        run(['hyprctl','dispatch',operation],False)

def save_state(s):
    RUN.mkdir(mode=0o700,parents=True,exist_ok=True)
    p=RUN/'state.tmp';p.write_text(json.dumps(s,indent=2)+'\n');p.replace(RUN/'state.json')

def work_ready():
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(.5);client.connect(str(BASE/'player2/.duoomarchy-control.sock'))
            client.sendall(b'{"action":"ping"}\n')
            result=json.loads(client.recv(4096))
            return bool(result.get('ready') and result.get('mode')=='work' and result.get('hyprland_instance'))
    except (OSError,ValueError):return False

def restore():
    p=RUN/'state.json'
    if not p.exists():return
    s=json.loads(p.read_text())
    if s.get('phase')=='off':return
    # Only undo our own weight, never overwrite a new jogarsim decision.
    current=run(['systemctl','--user','show','app.slice','-p','CPUWeight','--value'],False).stdout.strip()
    if s.get('app_weight') and current=='30' and not (RUNTIME/'jogar/active').exists():
        run(['systemctl','--user','set-property','--runtime','app.slice','CPUWeight='+s['app_weight']],False)
    for kind in ('sink','source'):
        selected=s.get('primary_audio',{}).get('set_'+kind);old=s.get('primary_audio',{}).get('old_'+kind)
        current_audio=run(['pactl',f'get-default-{kind}'],False).stdout.strip()
        if selected and old and current_audio==selected:run(['pactl',f'set-default-{kind}',old],False)
    s['phase']='off';s['stopped_at']=time.time();save_state(s)

def tune_background_compilers():
    # Only this service's game. Keep on-demand shader compilation at normal priority.
    own=Path('/proc/self/cgroup').read_text()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            if (proc/'comm').read_text().strip()!='Overwatch.exe':continue
            if (proc/'cgroup').read_text()!=own:continue
            for thread in (proc/'task').iterdir():
                if (thread/'comm').read_text().strip() in ('dxvk-shader-l','dxvk-cache'):
                    if os.getpriority(os.PRIO_PROCESS,int(thread.name))<10:
                        os.setpriority(os.PRIO_PROCESS,int(thread.name),10)
        except (OSError,ProcessLookupError):continue

def serve():
    RUN.mkdir(mode=0o700,parents=True,exist_ok=True)
    lock=(RUN/'lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    c=config();groups,ms=validate(c)
    mode=MODE_FILE.read_text().strip() if MODE_FILE.exists() else 'game'
    if mode not in ('game','work'):raise ValueError('Modo de sessão inválido.')
    if (RUNTIME/'tv-gaming/active').exists():raise ValueError('Desative o modo TV antes do modo duo.')
    if (RUNTIME/'jogar/active').exists():raise ValueError('Execute jogarnao antes: o modo duo faz sua própria reserva e mantém os dois monitores.')
    weight=run(['systemctl','--user','show','app.slice','-p','CPUWeight','--value']).stdout.strip()
    state={'phase':'starting','mode':mode,'app_weight':weight,'started_at':time.time(),'players':[]}
    save_state(state)
    procs=[];stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        write_rules(c,ms)
        state['primary_audio']=route_primary_audio(c['players'][0]);save_state(state)
        # The primary player stays in the native desktop. Never grab that kit.
        for n,p in [(2,c['players'][1])]:
            m=ms[p['monitor']];env=session_environment()
            apply_audio_profile(p)
            # Empty values deliberately inherit the desktop/Sonora choice.
            for key,field in (('PULSE_SINK','sink'),('PULSE_SOURCE','source')):
                value=p.get(field,'')
                if value:env[key]=value
                else:env.pop(key,None)
            app_id=f'{APP_PREFIX}.player{n}'
            env.update(SDL_APP_ID=app_id,SDL_VIDEODRIVER='x11',SDL_VIDEO_X11_WMCLASS=app_id,JOGARDUO_APP_ID=app_id,JOGARDUO_FPS=str(p['fps']),DUOOMARCHY_MODE=mode,
                       DUOOMARCHY_WORKSPACES=str(p.get('internal_workspaces',9)),DUOOMARCHY_STARTUP=p.get('startup','menu'),DUOOMARCHY_NAME=p['name'],DXVK_MAX_COMPILER_THREADS='2',__GL_SHADER_DISK_CACHE='1')
            cmd=gamescope_command(p,m,groups[n-1],mode)
            log=(BASE/'logs'/f'player{n}.log').open('w')
            proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            log.close();procs.append(proc)
            state['players'].append({'name':p['name'],'pid':proc.pid,'monitor':p['monitor'],'workspace':p['workspace'],'devices':groups[n-1],'sink':p.get('sink',''),'source':p.get('source','')});save_state(state)
            # Give compositor initialization time before launching another GPU client.
            for _ in range(600 if mode=='work' else 30):
                if stopping or proc.poll() is not None:break
                if mode=='work' and work_ready():break
                time.sleep(.1)
            if stopping or proc.poll() is not None:raise RuntimeError(f"Sessão {n} não abriu. Consulte {BASE}/logs/player{n}.log")
            if mode=='work' and not work_ready():raise RuntimeError('Hyprland da estação não ficou pronto. Veja logs/player2.log.')
        keep_station_reserved(c['players'][1])
        state['phase']='running';save_state(state)
        while not stopping and all(p.poll() is None for p in procs):
            if mode=='game':tune_background_compilers()
            keep_station_reserved(c['players'][1])
            time.sleep(2)
    finally:
        for proc in procs:
            if proc.poll() is None:
                try:os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        for proc in procs:
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
        restore()
        lock.close()

def start(mode='game'):
    if mode not in ('game','work'):raise ValueError('Use game ou work.')
    if active():print('Modo duo já está ativo. Encerre antes de trocar entre jogo e trabalho.');return
    validate(config(),profiles=False)
    # Login windows belong to this mode and hand their profiles over to the duo service.
    for n in (1,2):
        run(['systemctl','--user','stop',f'duoomarchy-login{n}.service'],False)
    validate(config())
    RUN.mkdir(mode=0o700,parents=True,exist_ok=True);MODE_FILE.write_text(mode+'\n')
    envkeys=['DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','XAUTHORITY','HYPRLAND_INSTANCE_SIGNATURE']
    run(['systemctl','--user','import-environment']+[k for k in envkeys if k in os.environ])
    run(['systemctl','--user','reset-failed',SERVICE],False)
    run(['systemctl','--user','start',SERVICE])
    for _ in range(650 if mode=='work' else 100):
        time.sleep(.1)
        p=RUN/'state.json';s=json.loads(p.read_text()) if p.exists() else {}
        if s.get('phase')=='running' and active():
            label=f"trabalho com workspaces 1–{config()['players'][1].get('internal_workspaces',9)}" if mode=='work' else 'jogo'
            print(f'Modo duo ativo ({label}): seu kit permanece no Omarchy; somente o segundo kit fica isolado. Para sair: jogarduonao no seu terminal, ou Ctrl+Alt+F12 no teclado dela.');return
        if not active():break
    raise RuntimeError(f'Modo duo não ficou ativo. Veja: journalctl --user -u {SERVICE} -n 40')

def login(n):
    if n != 2:raise ValueError('Use sua Steam normal no Omarchy. Somente a conta dela é isolada.')
    if active():raise ValueError('O modo duo já está aberto.')
    unit=f'duoomarchy-login{n}'
    if run(['systemctl','--user','is-active',unit],False).stdout.strip()=='active':
        print('A janela de login já está aberta.');return
    c=config();p=c['players'][n-1];ms={m['name']:m for m in monitors()}
    write_rules(c,ms)
    m=ms[p['monitor']]
    app_id=f'{APP_PREFIX}.player{n}'
    env=[f'DUOOMARCHY_DATA={BASE}',f'DUOOMARCHY_CONFIG={CONFIG}','SDL_VIDEODRIVER=x11',f'SDL_APP_ID={app_id}',f'SDL_VIDEO_X11_WMCLASS={app_id}',f'JOGARDUO_APP_ID={app_id}']
    if p.get('sink'):env.append('PULSE_SINK='+p['sink'])
    if p.get('source'):env.append('PULSE_SOURCE='+p['source'])
    cmd=['systemd-run','--user','--unit='+unit,'--collect','--service-type=exec','-p','KillMode=control-group','env']+env+[str(BIN),'--backend',p.get('backend','wayland'),'-f','-W',str(m['width']),'-H',str(m['height']),'-w','1920','-h','1080','-r','60','--',str(BASE/'session.py'),str(n)]
    run(cmd)
    print(f"Steam de {p['name']} aberta em {p['monitor']}, com controle normal do desktop.")

def status():
    state={}
    try:state=json.loads((RUN/'state.json').read_text())
    except (OSError,ValueError):pass
    suffix=' — '+state.get('mode','jogo') if active() else ''
    print('Modo duo: '+('ATIVO' if active() else 'DESLIGADO')+suffix)
    for n,p in enumerate(config()['players'],1):
        print(f"{n}. {p['name']}: {p['monitor']} / workspace {p.get('workspace','?')} — {p['fps']} FPS alvo")
        print('   Teclado:',p['keyboard']);print('   Mouse:',p['mouse'] or 'FALTA CONFIGURAR');print('   DPI:',p.get('mouse_native_dpi',800),'→',p.get('mouse_dpi',800));print('   Controle:',p.get('gamepad') or 'nenhum')
        print('   Saída:',p.get('sink') or 'padrão/Sonora');print('   Microfone:',p.get('source') or 'padrão/Sonora')
    try:validate(config(),profiles=not active());print('Dispositivos/configuração: OK; kit principal livre no Omarchy')
    except (ValueError,subprocess.CalledProcessError) as e:print('Pendente:',e)

def configure():
    import configurator
    c=config();ms=monitors()
    for index,p in enumerate(c['players'],1):
        p.setdefault('workspace',next((m['activeWorkspace']['id'] for m in ms if m['name']==p.get('monitor')),index))
    inventory={'devices':devices(),'monitors':ms,'sinks':audio_nodes('sinks'),'sources':audio_nodes('sources'),'gpus':gpu_nodes()}
    def save(updated):
        validate(updated,profiles=False)
        tmp=CONFIG.with_suffix('.tmp');tmp.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+'\n');tmp.chmod(0o600);tmp.replace(CONFIG)
        write_rules(updated,{m['name']:m for m in ms})
    configurator.launch(c,inventory,active(),save)

def enter_station():
    """User-requested navigation to the reserved station; never called by agents automatically."""
    p=config()['players'][1]
    if not active():raise ValueError('A estação está desligada.')
    result=run(['hyprctl','dispatch','focuswindow',f'class:^({re.escape(APP_PREFIX)}\\.player2)$'],False)
    if result.returncode:raise ValueError('Não foi possível mostrar a estação.')
    print(f"Estação de {p['name']} visível no workspace {p['workspace']}. Use o kit dela para controlar a sessão isolada.")

def main():
    alias=Path(sys.argv[0]).name
    cmd={'jogarduosim':'on','jogarduonao':'off'}.get(alias,sys.argv[1] if len(sys.argv)>1 else 'status')
    if cmd=='on':start('game')
    elif cmd in ('work','trabalho'):start('work')
    elif cmd=='off':run(['systemctl','--user','stop',SERVICE]);run(['systemctl','--user','stop','duoomarchy-login1.service','duoomarchy-login2.service'],False);restore();MODE_FILE.unlink(missing_ok=True);print('Modo duo desligado. Kits liberados; perfis preservados.')
    elif cmd=='serve':serve()
    elif cmd=='restore':restore()
    elif cmd in ('configurar','configure'):configure()
    elif cmd in ('enter','entrar'):enter_station()
    elif cmd=='manager':subprocess.Popen([str(BASE/'manager.py')])
    elif cmd=='login':login(int(sys.argv[2]) if len(sys.argv)>2 else 2)
    elif cmd=='devices':print(json.dumps(devices(),indent=2,ensure_ascii=False))
    elif cmd in ('check','status'):status()
    else:raise ValueError('Uso: duoomarchy status|configurar|work|devices; jogarduosim; jogarduonao')
if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,subprocess.CalledProcessError,OSError) as e:
        print('Jogar duo:',e,file=sys.stderr);sys.exit(1)
