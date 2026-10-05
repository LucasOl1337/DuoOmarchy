import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

duo=module('duo',ROOT/'src/duoomarchy.py')
installer=module('installer',ROOT/'scripts/install.py')
session=module('session',ROOT/'src/session.py')
tools=module('tools',ROOT/'src/work_tools.py')

def config():
    return {'players':[{'name':'P1','monitor':'DP-1','workspace':1,'keyboard':'p1kbd','mouse':'p1mouse','gamepad':'','sink':'a','source':'a-input','fps':120},
                       {'name':'P2','monitor':'DP-2','workspace':2,'keyboard':'p2kbd','mouse':'p2mouse','gamepad':'','sink':'b','source':'b-input','fps':120,'backend':'wayland'}]}

class Tests(unittest.TestCase):
    def test_session_uses_the_supervisors_profile_and_config(self):
        for layout in ('jogarduo','duoomarchy'):
            with self.subTest(layout=layout),tempfile.TemporaryDirectory() as td:
                root=Path(td);data=root/layout;cfg=root/'config.json'
                cfg.write_text(json.dumps({'players':[{}, {'gpu_name':'test GPU'}]}))
                with patch.object(duo,'BASE',data),patch.object(duo,'CONFIG',cfg):
                    env=duo.session_environment()
                script='''
import importlib.util, os, subprocess, sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('session',sys.argv[1])
session=importlib.util.module_from_spec(spec);spec.loader.exec_module(session)
def launch(args):
    profile=str(Path(os.environ['DUOOMARCHY_DATA'])/'player2')
    assert profile in args, args
    assert args[args.index('DXVK_FILTER_DEVICE_NAME')+1]=='test GPU', args
    assert args[-1].endswith('/.local/bin/duoomarchy-session-control'), args
    return subprocess.CompletedProcess(args,0)
session.subprocess.run=launch
sys.argv=['session.py','2']
sys.exit(session.main())
'''
                result=subprocess.run([sys.executable,'-c',script,str(ROOT/'src/session.py')],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertTrue((data/'player2/.duo-profile.lock').is_file())

    def test_login_unit_receives_the_same_profile_paths(self):
        def run(args,*_):
            return subprocess.CompletedProcess(args,0,'inactive\n','')
        with patch.object(duo,'active',return_value=False),patch.object(duo,'config',return_value=config()),patch.object(duo,'monitors',return_value=[{'name':'DP-2','width':1920,'height':1080}]),patch.object(duo,'write_rules'),patch.object(duo,'run',side_effect=run) as launch:
            duo.login(2)
        args=launch.call_args.args[0]
        self.assertIn('DUOOMARCHY_DATA='+str(duo.BASE),args)
        self.assertIn('DUOOMARCHY_CONFIG='+str(duo.CONFIG),args)

    def test_legacy_update_installs_the_game_wrapper(self):
        updater=module('updater',ROOT/'scripts/update-local.py')
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);data=home/'.local/share/jogarduo';data.mkdir(parents=True)
            (data/'jogarduo.py').write_text('previous install')
            with patch.object(updater.subprocess,'run',return_value=subprocess.CompletedProcess([],3)),patch.object(updater.installer,'install_work_profile'):
                updater.update(home)
            wrapper=data/'player2/.local/bin/duoomarchy-overwatch'
            self.assertEqual(wrapper.read_text(),(ROOT/'src/overwatch.py').read_text())
            self.assertEqual(wrapper.stat().st_mode & 0o777,0o755)

    def test_maestri_profile_does_not_import_canvas_or_tunnel(self):
        with tempfile.TemporaryDirectory() as td:
            host=Path(td)/'host';private=Path(td)/'private'
            p=host/'.maestri/preferences.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'payload':{'sshEnabled':True,'sshAddToPath':True,'agentPresets':[{'command':'claude'}]},'schemaVersion':1}))
            (host/'.maestri/license.json').write_text('{"payload":{"isActivated":true}}')
            tools.seed_maestri(private,host)
            self.assertEqual((private/'.maestri/license.json').stat().st_mode & 0o777,0o600)
            self.assertTrue(json.loads((private/'.maestri/license.json').read_text())['payload']['isActivated'])
            own=json.loads((private/'.maestri/preferences.json').read_text())['payload']
            self.assertEqual(own['agentPresets'],[{'command':'claude'}])
            self.assertFalse(own['sshEnabled']);self.assertFalse(own['sshAddToPath'])
            self.assertEqual(own['sshTunnelPort'],7434)
            self.assertTrue(json.loads(p.read_text())['payload']['sshEnabled'])
            self.assertFalse((private/'.maestri/workspaces').exists())
            tools.seed_maestri(private,host)
            self.assertEqual(json.loads((private/'.maestri/preferences.json').read_text())['payload'],own)

    def test_maestri_launch_has_its_own_electron_and_cli_identity(self):
        home=Path('/station')
        argv,env=tools.invocation('maestri-abrir',[],home,{'MAESTRI_SOCKET':'human.sock','MAESTRI_TERMINAL_ID':'human','PATH':'/usr/bin'})
        self.assertIn('--user-data-dir=/station/.config/duoomarchy-maestri',argv)
        self.assertEqual(env['MAESTRI_DATA_DIR'],'/station/.maestri')
        self.assertNotIn('MAESTRI_SOCKET',env);self.assertNotIn('MAESTRI_TERMINAL_ID',env)
        with self.assertRaisesRegex(RuntimeError,'terminal do Maestri'):tools.invocation('maestri',['list'],home,{})
        cli,_=tools.invocation('maestri',['list'],home,{'MAESTRI_SOCKET':'own.sock','MAESTRI_TERMINAL_ID':'own'})
        self.assertEqual(cli[0],'/station/.local/opt/maestri/current/resources/cli/maestri')

    def test_jcode_maestri_routes_to_the_station_client_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)/'private';proc=Path(td)/'proc'
            client=home/'.jcode/client_sessions/123';client.parent.mkdir(parents=True);client.write_text('own-session')
            identity=proc/'123/environ';identity.parent.mkdir(parents=True)
            identity.write_bytes(b'MAESTRI_TERMINAL_ID=own-client\0MAESTRI_SOCKET=/tmp/own.sock\0SECRET_TOKEN=fixture\0')
            env=tools.maestri_identity(home,{'JCODE_SESSION_ID':'own-session','MAESTRI_TERMINAL_ID':'server-owner'},proc)
            self.assertEqual(env['MAESTRI_TERMINAL_ID'],'own-client')
            self.assertEqual(env['MAESTRI_SOCKET'],'/tmp/own.sock')
            self.assertNotIn('SECRET_TOKEN',env)
            absent=tools.maestri_identity(home,{'JCODE_SESSION_ID':'other-session'},proc)
            self.assertNotIn('MAESTRI_SOCKET',absent)

    def test_tool_wrappers_apply_bypass_to_the_shared_install(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);(home/'.local/bin').mkdir(parents=True);(home/'.config/duoomarchy-work').mkdir(parents=True)
            for name,(path,flags,env) in tools.TOOLS.items():
                if name in ('agent','devin','agy'):continue
                target=home/path;target.parent.mkdir(parents=True,exist_ok=True);target.touch()
            tools.install(home,home)
            for name in ('codex','claude','grok','omp'):
                argv,env=tools.invocation(name,['--help'],home,{})
                self.assertIn(tools.TOOLS[name][1][0],argv)
                self.assertEqual(argv[-1],'--help')
                self.assertTrue((home/'.local/share/applications'/f'duoomarchy-{name}.desktop').exists())
            _,env=tools.invocation('hermes',[],home,{})
            self.assertEqual(env['HERMES_YOLO_MODE'],'true')
            _,env=tools.invocation('opencode',[],home,{})
            self.assertEqual(json.loads(env['OPENCODE_PERMISSION']),{'*':'allow'})

    def test_shared_settings_exclude_live_session_stores(self):
        self.assertIn('.codex/config.toml',tools.SHARED_PATHS)
        self.assertIn('.hermes/hermes-agent',tools.SHARED_PATHS)
        self.assertEqual(tools.SHARED_WRITABLE_PATHS,('.hermes/installs',))
        self.assertNotIn('.hermes',tools.SHARED_WRITABLE_PATHS)
        self.assertIn('.local/opt/maestri',tools.SHARED_PATHS)
        for path in ('.codex/state_5.sqlite','.claude/projects','.jcode/client_sessions','.maestri/workspaces','.config/maestri','.omp/agent/agent.db'):
            self.assertNotIn(path,tools.SHARED_PATHS)
        with tempfile.TemporaryDirectory() as td:
            host=Path(td);runtime=host/'run';runtime.mkdir();(runtime/'gamescope-test').touch()
            settings=host/'.codex/config.toml';settings.parent.mkdir();settings.touch()
            with patch.object(session,'HOME',host):
                argv=session.command(host/'private',runtime,{'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-test','MAESTRI_SOCKET':'human','JCODE_SESSION_ID':'human'},True)
            i=argv.index(str(settings));self.assertEqual(argv[i-1],'--ro-bind')
            for key in ('MAESTRI_SOCKET','JCODE_SESSION_ID'):
                self.assertEqual(argv[argv.index(key)-1],'--unsetenv')

    def test_omp_auth_snapshot_is_writable_but_not_a_shared_database(self):
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as td:
            host=Path(td)/'host';private=Path(td)/'private';source=host/'.omp/agent/agent.db';source.parent.mkdir(parents=True)
            with closing(sqlite3.connect(source)) as db:
                db.executescript("CREATE TABLE auth_credentials (value TEXT); INSERT INTO auth_credentials VALUES ('fixture'); CREATE TABLE clients (id TEXT); INSERT INTO clients VALUES ('human');")
            tools.seed_omp_auth(private,host)
            destination=private/'.omp/agent/agent.db'
            with closing(sqlite3.connect(destination)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM auth_credentials').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT count(*) FROM clients').fetchone()[0],0)
                db.execute("INSERT INTO clients VALUES ('own')");db.commit()
            with closing(sqlite3.connect(source)) as db:self.assertEqual(db.execute('SELECT id FROM clients').fetchone()[0],'human')

    def test_control_endpoint_rejects_arbitrary_commands(self):
        control=module('control',ROOT/'src/session-control.py')
        with patch.object(control,'launch') as launch:
            self.assertFalse(control.dispatch('rm -rf /')['ok'])
            launch.assert_not_called()

    def test_work_ping_waits_for_a_sized_output(self):
        control=module('control_ready',ROOT/'src/session-control.py')
        with patch.dict(control.os.environ,{'DUOOMARCHY_MODE':'work'}),patch.object(control,'DESKTOP_READY',True):
            for width,expected in ((0,False),(1920,True)):
                result=subprocess.CompletedProcess([],0,json.dumps([{'width':width,'height':1080}]),'')
                with patch.object(control.subprocess,'run',return_value=result):
                    self.assertEqual(control.dispatch('ping')['ready'],expected)
            with patch.object(control.subprocess,'run',side_effect=subprocess.TimeoutExpired('hyprctl',2)):
                self.assertFalse(control.dispatch('ping')['ready'])

    def test_private_run_keeps_the_host_resolver(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'pulse').mkdir();(root/'pulse/native').touch()
            args=session.command(root/'home',root,{})
            resolver=Path('/etc/resolv.conf').resolve()
            if resolver.is_file():
                source=resolver.parent if resolver.is_relative_to('/run') else resolver
                index=args.index(str(source))
                self.assertEqual(args[index-1],'--ro-bind')
                self.assertNotIn('--unshare-net',args)

    def test_host_wayland_is_never_a_work_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'wayland-human').touch()
            with self.assertRaisesRegex(ValueError,'desktop principal'):
                session.command(root/'home',root,{'WAYLAND_DISPLAY':'wayland-human'},work=True)

    def test_machine_skills_are_linked_without_mixing_accounts(self):
        with tempfile.TemporaryDirectory() as td:
            host=Path(td)/'host'; private=Path(td)/'private'
            skill=host/'.agents/skills/agent-bench'; skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('# bench\n')
            (host/'.agents/skills/synced/conta-principal/pdf').mkdir(parents=True)
            (private/'.claude/skills/synced/conta-dela').mkdir(parents=True)
            (private/'.codex/skills/.system').mkdir(parents=True)
            (private/'.claude/.credentials.json').write_text('dela')
            self.assertGreater(session.share_machine_skills(private, host), 0)
            for relative in session.SKILL_DIRS:
                link=private/relative/'agent-bench'
                self.assertTrue(link.is_symlink(), relative)
                self.assertEqual(link.readlink(), host/'.agents/skills/agent-bench')
            self.assertTrue((private/'.claude/skills/synced/conta-dela').is_dir())
            self.assertFalse((private/'.claude/skills/synced/conta-principal').exists())
            self.assertFalse((private/'.grok/skills/synced').exists())
            self.assertFalse((private/'.codex/skills/synced').exists())
            self.assertTrue((private/'.codex/skills/.system').is_dir())
            self.assertEqual((private/'.claude/.credentials.json').read_text(), 'dela')
            skill.rename(host/'.agents/skills/renomeada')
            session.share_machine_skills(private, host)
            self.assertFalse((private/'.claude/skills/agent-bench').exists())
            self.assertTrue((private/'.claude/skills/renomeada').is_symlink())

    def test_cli_logins_share_only_existing_auth_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);host=root/'host';runtime=root/'run';runtime.mkdir();(runtime/'gamescope-test').touch()
            for name in ('.codex/auth.json','.claude/.credentials.json','.grok/auth.json','.hermes/.env'):
                p=host/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
            with patch.object(session,'HOME',host):args=session.command(root/'private',runtime,{'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-test'},work=True)
            for name in ('.codex/auth.json','.claude/.credentials.json','.grok/auth.json','.hermes/.env'):
                i=args.index(str(host/name));self.assertEqual(args[i-1],'--ro-bind')
            for name in ('.codex','.claude','.grok'):
                self.assertNotIn(str(host/name),args)
            self.assertNotIn(str(host/'.config/maestri'),args)

    def test_window_rule_matches_only_the_station(self):
        import re
        rule=duo.rule(config()['players'][1],2,{'activeWorkspace':{'id':2}})
        value=json.loads(re.search(r'class=("(?:[^"\\]|\\.)*")',rule).group(1))
        self.assertRegex(duo.APP_PREFIX+'.player2',value)
        self.assertIsNone(re.search(value,duo.APP_PREFIX+'Xplayer2'))
        self.assertIsNone(re.search(value,duo.APP_PREFIX+'.player1'))

    def test_station_fullscreen_targets_only_its_window(self):
        station={'class':duo.APP_PREFIX+'.player2','address':'0xabc','workspace':{'id':2},'monitor':1,'fullscreen':0,'fullscreenClient':0}
        human={'class':'brave','address':'0xdef','fullscreen':0}
        p=duo.normalize_config(config())['players'][1];p['workspace_locked']=True
        result=subprocess.CompletedProcess([],0,json.dumps([human,station]),'')
        with patch.object(duo,'run',return_value=result) as call,patch.object(duo,'monitors',return_value=[{'id':1,'name':'DP-2'}]):
            duo.keep_station_reserved(p)
            operation=call.call_args.args[0]
            self.assertEqual(operation[:2],['hyprctl','dispatch'])
            self.assertIn('window="address:0xabc"',operation[2])
            self.assertIn('action="set"',operation[2])
            self.assertNotIn('focus',operation[2])
            station.update(fullscreen=2,fullscreenClient=2)
            call.reset_mock();call.return_value=subprocess.CompletedProcess([],0,json.dumps([human,station]),'')
            duo.keep_station_reserved(p)
            self.assertEqual(call.call_count,1)

    def test_work_actions_are_fixed_commands(self):
        control=module('control_work',ROOT/'src/session-control.py')
        with patch.object(control,'launch') as launch:
            self.assertTrue(control.dispatch('codex')['ok'])
            self.assertEqual(launch.call_args.args[0][-2],'-c')
            self.assertIn(str(control.HOME/'.local/bin/codex'),launch.call_args.args[0][-1])

    def test_browser_uses_private_profile(self):
        control=module('control_browser',ROOT/'src/session-control.py')
        with patch.object(control,'launch') as launch,patch.object(control.shutil,'which',return_value='/usr/bin/chromium'):
            self.assertTrue(control.dispatch('browser_open')['ok'])
            cmd=launch.call_args.args[0]
            self.assertTrue(any(x.startswith('--user-data-dir=') and 'duoomarchy-browser' in x for x in cmd))
            self.assertFalse(any('remote-debugging' in x for x in cmd))

    def test_close_steam_keeps_control_service_alive(self):
        control=module('control_steam',ROOT/'src/session-control.py')
        with patch.object(control,'launch') as launch:
            self.assertTrue(control.dispatch('steam_close')['ok'])
            self.assertEqual(launch.call_args.args[0],['/usr/bin/steam','-shutdown'])
            self.assertTrue(control.dispatch('ping')['ok'])

    def test_live_control_socket(self):
        import os,socket,sys,time
        with tempfile.TemporaryDirectory() as td:
            env=os.environ.copy();env['HOME']=td
            proc=subprocess.Popen([sys.executable,str(ROOT/'src/session-control.py'),'--no-autostart'],env=env)
            endpoint=Path(td)/'.duoomarchy-control.sock'
            try:
                for _ in range(50):
                    if endpoint.exists():break
                    time.sleep(.02)
                self.assertTrue(endpoint.exists())
                self.assertEqual(endpoint.stat().st_mode & 0o777,0o700)
                for action,expected in [('ping',True),('arbitrary-shell',False),('ping',True)]:
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                        client.settimeout(2);client.connect(str(endpoint))
                        client.sendall(json.dumps({'action':action}).encode()+b'\n')
                        self.assertEqual(json.loads(client.recv(4096))['ok'],expected)
            finally:proc.terminate();proc.wait(timeout=5)

    def test_same_monitor_rejected(self):
        c=config();c['players'][1]['monitor']='DP-1'
        with self.assertRaisesRegex(ValueError,'monitores diferentes'):duo.validate(c)

    def test_shared_device_rejected(self):
        with patch.object(duo,'held_devices',return_value=['same']):
            with self.assertRaisesRegex(ValueError,'compartilham'):duo.validate(config())

    def test_only_second_kit_is_ever_captured(self):
        c=config();launched=[];commands=[];environments=[]
        ms={p['monitor']:{'width':2560,'height':1440} for p in c['players']}
        class Proc:
            pid=99999999
            def __init__(self):self.calls=0
            def poll(self):
                self.calls+=1;return None if self.calls<=34 else 0
            def wait(self,**kw):return 0
        def launch(cmd,**kw):launched.append(cmd);environments.append(kw['env']);return Proc()
        def run(args,*a,**kw):commands.append(args);return subprocess.CompletedProcess(args,0,'100\n','')
        with tempfile.TemporaryDirectory() as td,patch.object(duo,'RUN',Path(td)/'run'),patch.object(duo,'RUNTIME',Path(td)),patch.object(duo,'BASE',Path(td)),patch.object(duo,'config',return_value=c),patch.object(duo,'validate',return_value=([['PRIMARY'],['SECOND']],ms)),patch.object(duo,'write_rules'),patch.object(duo,'run',side_effect=run),patch.object(duo.subprocess,'Popen',side_effect=launch),patch.object(duo.time,'sleep'),patch.object(duo,'tune_background_compilers'),patch.object(duo.signal,'signal'),patch.dict(duo.os.environ,{'PULSE_SINK':'old-output','PULSE_SOURCE':'old-input'}):
            (Path(td)/'logs').mkdir();duo.serve()
        self.assertEqual(len(launched),1)
        self.assertIn('SECOND',launched[0]);self.assertNotIn('PRIMARY',launched[0])
        self.assertEqual(launched[0][-1],'2');self.assertEqual(launched[0][2],'wayland')
        self.assertFalse(any('set-property' in c for c in commands))
        self.assertIn(['pactl','set-sink-volume','b','100%'],commands)
        self.assertIn(['pactl','set-source-volume','b-input','100%'],commands)
        self.assertEqual(environments[0]['PULSE_SINK'],'b')
        self.assertEqual(environments[0]['PULSE_SOURCE'],'b-input')

    def test_agent_workspaces_are_rejected(self):
        c=config();c['players'][1]['workspace']=6
        with patch.object(duo,'held_devices',side_effect=[['PRIMARY'],['SECOND']]):
            with self.assertRaisesRegex(ValueError,'entre 1 e 5'):duo.validate(c,display=False,profiles=False)

    def test_same_workspace_is_rejected(self):
        c=config();c['players'][1]['workspace']=1
        with patch.object(duo,'held_devices',side_effect=[['PRIMARY'],['SECOND']]):
            with self.assertRaisesRegex(ValueError,'workspaces diferentes'):duo.validate(c,display=False,profiles=False)

    def test_gamescope_uses_profile_rendering_options(self):
        p=config()['players'][1]
        p.update(resolution='1920x1080',scaler='fit',filter='fsr',gpu='10de:2705',mouse_native_dpi=800,mouse_dpi=1600)
        cmd=duo.gamescope_command(p,{'width':2560,'height':1440},['/dev/input/event9'],'work')
        self.assertEqual(cmd[cmd.index('-w')+1:cmd.index('-w')+3],['1920','-h'])
        self.assertEqual(cmd[cmd.index('-h')+1],'1080')
        self.assertEqual(cmd[cmd.index('-S')+1],'fit');self.assertEqual(cmd[cmd.index('-F')+1],'fsr')
        self.assertEqual(cmd[cmd.index('-s')+1],'2.0000')
        self.assertIn('10de:2705',cmd);self.assertEqual(cmd[-1],'work')

    def test_invalid_mouse_dpi_is_rejected(self):
        c=config();c['players'][1]['mouse_dpi']=0
        with patch.object(duo,'held_devices',side_effect=[['PRIMARY'],['SECOND']]):
            with self.assertRaisesRegex(ValueError,'DPI desejado'):duo.validate(c,display=False,profiles=False)

    def test_generated_rules_reserve_selected_workspace(self):
        c=duo.normalize_config(config());c['players'][1]['workspace_locked']=True
        ms={p['monitor']:{'activeWorkspace':{'id':p['workspace']}} for p in c['players']}
        with tempfile.TemporaryDirectory() as td,patch.object(duo,'RULE_FILE',Path(td)/'rules.lua'),patch.object(duo,'run',return_value=subprocess.CompletedProcess([],0,'','')):
            duo.write_rules(c,ms);text=(Path(td)/'rules.lua').read_text()
        self.assertIn('workspace_rule',text);self.assertIn('persistent=true',text)
        self.assertIn('workspace="2"',text);self.assertIn('monitor="DP-2"',text)

    def test_audio_configuration_is_not_required_or_validated(self):
        for legacy in (False,True):
            with self.subTest(legacy=legacy),tempfile.TemporaryDirectory() as td:
                c=config()
                for p in c['players']:
                    if legacy:p.update(sink='disconnected',source='disconnected.monitor')
                    else:p.pop('sink');p.pop('source')
                binary=Path(td)/'gamescope';binary.touch()
                with patch.object(duo,'BIN',binary),patch.object(duo,'held_devices',side_effect=[['PRIMARY'],['SECOND']]),patch.object(duo.os,'access',return_value=True),patch.object(duo,'run') as run:
                    groups,_=duo.validate(c,display=False,profiles=False)
                    self.assertEqual(groups,[['PRIMARY'],['SECOND']])
                    run.assert_not_called()

    def test_restore_preserves_someone_elses_priority(self):
        with tempfile.TemporaryDirectory() as td,patch.object(duo,'RUN',Path(td)):
            duo.save_state({'phase':'running','app_weight':'100'})
            with patch.object(duo,'run',return_value=subprocess.CompletedProcess([],0,'500\n','')) as call:
                duo.restore();duo.restore()
                self.assertFalse(any('set-property' in c.args[0] for c in call.call_args_list))

    def test_installer_preserves_config_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);hypr=home/'.config/hypr';hypr.mkdir(parents=True)
            (hypr/'hyprland.lua').write_text('-- existing\n')
            binary=home/'.local/share/mise/installs/codex/latest/bin/codex'
            binary.parent.mkdir(parents=True);binary.write_text('#!/bin/sh\nexit 0\n')
            installer.install(home,False)
            cfg=home/'.config/duoomarchy/config.json';cfg.write_text('{"custom": true}')
            installer.install(home,False)
            self.assertEqual(json.loads(cfg.read_text()),{'custom':True})
            self.assertEqual((hypr/'hyprland.lua').read_text().count('require("hypr.duoomarchy")'),1)
            self.assertTrue((home/'.local/bin/jogarduosim').is_symlink())
            self.assertEqual((home/'.local/share/duoomarchy/player2').stat().st_mode & 0o777,0o700)
            self.assertTrue((home/'.local/share/duoomarchy/player2/.local/bin/duoomarchy-work-desktop').is_file())
            private=home/'.local/share/duoomarchy/player2'
            argv,_=tools.invocation('codex',['--version'],private,{})
            self.assertIn('--dangerously-bypass-approvals-and-sandbox',argv)
            self.assertEqual(argv[0],str(private/'.local/share/mise/installs/codex/latest/bin/codex'))
            self.assertTrue((home/'.local/share/duoomarchy/player2/.config/duoomarchy-work/hyprland.lua').is_file())
            self.assertTrue((home/'.local/share/duoomarchy/player2/AGENTS.md').is_file())
            self.assertIn('/run/host-user',(home/'.local/share/duoomarchy/player2/.local/bin/agent-bench').read_text())
            self.assertTrue((home/'.local/share/duoomarchy/configurator.py').is_file())

    def test_installer_refuses_existing_commands(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);p=home/'.local/bin/jogarduosim';p.parent.mkdir(parents=True);p.write_text('keep me')
            with self.assertRaisesRegex(RuntimeError,'preserved'):installer.install(home,False)
            self.assertEqual(p.read_text(),'keep me')

    def test_private_home_and_ipc_without_physical_input(self):
        cmd=session.command(Path('/private/player2'),Path('/run/user/2345'),{})
        self.assertIn('--unshare-ipc',cmd);self.assertIn('--unshare-pid',cmd)
        self.assertIn('/private/player2',cmd)
        self.assertIn('/dev/input',cmd);self.assertEqual(cmd[cmd.index('/dev/input')-1],'--tmpfs')
        self.assertIn('/run/user/2345/pulse/native',cmd)
        self.assertNotIn('PULSE_SINK',cmd);self.assertNotIn('PULSE_SOURCE',cmd)
        routed=session.command(Path('/private/player2'),Path('/run/user/2345'),{'PULSE_SINK':'headphones','PULSE_SOURCE':'microphone'})
        for key,value in (('PULSE_SINK','headphones'),('PULSE_SOURCE','microphone')):
            self.assertEqual(routed[routed.index(key)+1],value)

    def test_work_desktop_receives_only_gamescope_wayland(self):
        with tempfile.TemporaryDirectory() as td:
            host=Path(td)/'host';runtime=Path(td)/'run';runtime.mkdir();(runtime/'gamescope-7').touch()
            (host/'.local/share/mise').mkdir(parents=True)
            with patch.object(session,'HOME',host):
                cmd=session.command(Path('/private/player2'),runtime,{'GAMESCOPE_WAYLAND_DISPLAY':'gamescope-7'},work=True)
        self.assertEqual(cmd[cmd.index('WAYLAND_DISPLAY')+1],'gamescope-7')
        self.assertNotIn('WLR_BACKENDS',cmd)
        self.assertIn(str(host/'Compartilhado'),cmd)
        self.assertNotIn('/tmp/.X11-unix',cmd)
        self.assertIn('DISPLAY',cmd)
        self.assertIn(str(host/'.local/share/mise'),cmd)

    def test_custom_steam_launch_options_are_preserved(self):
        import vdf
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);p=home/'.local/share/Steam/userdata/123/config/localconfig.vdf';p.parent.mkdir(parents=True)
            data={'UserLocalConfigStore':{'Software':{'Valve':{'Steam':{'apps':{'2357570':{'LaunchOptions':'custom %command%'}}}}}}}
            with p.open('w') as f:vdf.dump(data,f)
            before=p.read_text();session.install_launch_options(home);self.assertEqual(before,p.read_text())

if __name__=='__main__':unittest.main()
