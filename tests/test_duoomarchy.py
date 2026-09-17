import importlib.util
import json
from pathlib import Path
import subprocess
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

def config():
    return {'players':[{'name':'P1','monitor':'DP-1','keyboard':'p1kbd','mouse':'p1mouse','sink':'a','source':'a.monitor','fps':120},
                       {'name':'P2','monitor':'DP-2','keyboard':'p2kbd','mouse':'p2mouse','sink':'b','source':'b.monitor','fps':120,'backend':'wayland'}]}

class Tests(unittest.TestCase):
    def test_control_endpoint_rejects_arbitrary_commands(self):
        control=module('control',ROOT/'src/session-control.py')
        with patch.object(control,'launch') as launch:
            self.assertFalse(control.dispatch('rm -rf /')['ok'])
            launch.assert_not_called()

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
        self.assertFalse(any(c[0]=='pactl' for c in commands))
        self.assertNotIn('PULSE_SINK',environments[0])
        self.assertNotIn('PULSE_SOURCE',environments[0])

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
            installer.install(home,False)
            cfg=home/'.config/duoomarchy/config.json';cfg.write_text('{"custom": true}')
            installer.install(home,False)
            self.assertEqual(json.loads(cfg.read_text()),{'custom':True})
            self.assertEqual((hypr/'hyprland.lua').read_text().count('require("hypr.duoomarchy")'),1)
            self.assertTrue((home/'.local/bin/jogarduosim').is_symlink())
            self.assertEqual((home/'.local/share/duoomarchy/player2').stat().st_mode & 0o777,0o700)

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
        for key in ('PULSE_SINK','PULSE_SOURCE'):
            self.assertEqual(cmd[cmd.index(key)-1],'--unsetenv')

    def test_custom_steam_launch_options_are_preserved(self):
        import vdf
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);p=home/'.local/share/Steam/userdata/123/config/localconfig.vdf';p.parent.mkdir(parents=True)
            data={'UserLocalConfigStore':{'Software':{'Valve':{'Steam':{'apps':{'2357570':{'LaunchOptions':'custom %command%'}}}}}}}
            with p.open('w') as f:vdf.dump(data,f)
            before=p.read_text();session.install_launch_options(home);self.assertEqual(before,p.read_text())

if __name__=='__main__':unittest.main()
