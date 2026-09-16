#!/usr/bin/python3
"""Copy only game content and its manifest. Never copy Steam identity files."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import vdf

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('appid',type=int)
ap.add_argument('--steamapps',type=Path,default=Path.home()/'.local/share/Steam/steamapps')
ap.add_argument('--allow-full-copy',action='store_true',help='Allow a full disk copy if reflinks are unavailable')
a=ap.parse_args()
base=Path(os.environ.get('DUOOMARCHY_DATA',Path.home()/'.local/share/duoomarchy'))
profile=base/'player2';profile.mkdir(parents=True,exist_ok=True,mode=0o700)
with (profile/'.duo-profile.lock').open('a') as lock:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:ap.error('Close the second Steam session before importing.')
    manifest=a.steamapps/f'appmanifest_{a.appid}.acf'
    with manifest.open() as f:metadata=vdf.load(f)
    directory=metadata['AppState']['installdir']
    if Path(directory).name!=directory or directory in ('.','..'):ap.error('Unsafe game directory in manifest')
    dest=profile/'.local/share/Steam/steamapps';(dest/'common').mkdir(parents=True,exist_ok=True)
    final=dest/'common'/directory
    if final.exists():ap.error(f'Destination already exists: {final}')
    staging=dest/'common'/f'.duoomarchy-import-{a.appid}'
    if staging.exists():ap.error(f'Previous import needs inspection: {staging}')
    subprocess.run(['cp','-a','--reflink='+('auto' if a.allow_full_copy else 'always'),str(a.steamapps/'common'/directory),str(staging)],check=True)
    staging.rename(final)
    # Drop ownership/account metadata. Steam refreshes this manifest after login.
    metadata['AppState'].pop('LastOwner',None)
    with (dest/manifest.name).open('w') as f:vdf.dump(metadata,f,pretty=True)
    print('Imported game files only:',final)
