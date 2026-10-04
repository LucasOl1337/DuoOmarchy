#!/usr/bin/python3
"""Update the existing jogarduo installation, preserving profiles and devices."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

def update(home):
    data=home/'.local/share/jogarduo'
    if not (data/'jogarduo.py').is_file():raise RuntimeError('Instalação jogarduo ausente.')
    if subprocess.run(['systemctl','--user','is-active','--quiet','jogarduo.service']).returncode==0:
        raise RuntimeError('Encerre a estação antes de atualizar.')
    backup=data/'backups'/time.strftime('work-%Y%m%d-%H%M%S');backup.mkdir(parents=True)
    for name in ('jogarduo.py','session.py','manager.py','configurator.py','work_tools.py'):
        if (data/name).is_file():shutil.copy2(data/name,backup/name)
    for relative in ('.local/bin','.config/duoomarchy-work','.config/hypr'):
        if (data/'player2'/relative).exists():shutil.copytree(data/'player2'/relative,backup/'player2'/relative,symlinks=True)
    source=(ROOT/'src/duoomarchy.py').read_text()
    # Preserve command aliases and all deployed legacy paths.
    source=source.replace("HOME/'.local/share/duoomarchy'","HOME/'.local/share/jogarduo'")
    source=source.replace("HOME/'.config/duoomarchy/config.json'","HOME/'.config/jogarduo/config.json'")
    source=source.replace("'DUOOMARCHY_RUNTIME','duoomarchy'","'DUOOMARCHY_RUNTIME','jogarduo'")
    source=source.replace("'DUOOMARCHY_SERVICE','duoomarchy.service'","'DUOOMARCHY_SERVICE','jogarduo.service'")
    source=source.replace("'DUOOMARCHY_APP_ID','duoomarchy'","'DUOOMARCHY_APP_ID','jogarduo'")
    source=source.replace("HOME/'.config/hypr/duoomarchy.lua'","HOME/'.config/hypr/jogarduo.lua'")
    (data/'jogarduo.py').write_text(source);(data/'jogarduo.py').chmod(0o755)
    for name in ('session.py','manager.py','configurator.py','work_tools.py'):
        source=(ROOT/'src'/name).read_text()
        if name=='session.py':
            source=source.replace("HOME / '.local/share/duoomarchy'","HOME / '.local/share/jogarduo'")
            source=source.replace("HOME / '.config/duoomarchy/config.json'","HOME / '.config/jogarduo/config.json'")
        (data/name).write_text(source);(data/name).chmod(0o755)
    shutil.copy2(ROOT/'VERSION',data/'VERSION')
    installer.install_work_profile(data,home)
    print('Atualizado; perfis e configuração preservados. Backup:',backup)

if __name__=='__main__':update(Path.home())
