"""Build the original full desktop workspace with integrated BLE into a NEW release."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BLE=ROOT/'runtime/ble-bench-v2/Lib/site-packages'
sys.path[:0]=[str(ROOT/'app/revisions/v5'),str(ROOT/'app/ble_prototype/v1'),str(BLE)]
from uwb_board_programmer.standalone_flashing import latest_bundle,validate_image
from uwb_board_programmer.flashing import bundles,images

release=ROOT/'releases/desktop-v5';work=ROOT/'runtime/pyinstaller-work-v5';spec=ROOT/'runtime/pyinstaller-spec-v5'
if any(path.exists() for path in (release,work,spec)):raise FileExistsError('Preserving earlier build. Use a new package revision.')
name='UWB_Board_Programmer_2_1_0'
command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name',name,
         '--icon',str(ROOT/'resources/branding/logo-v1.ico'),'--distpath',str(release),'--workpath',str(work),'--specpath',str(spec),
         '--paths',str(ROOT/'app/revisions/v5'),'--paths',str(ROOT/'app/ble_prototype/v1'),'--paths',str(BLE),
         '--hidden-import','engineio.async_drivers.threading','--hidden-import','socketio',
         '--hidden-import','scipy.spatial.transform._rotation_cy','--collect-all','bleak','--collect-all','winrt',
         '--exclude-module','pytest']
for dist in importlib.metadata.distributions(path=[str(BLE)]):
    if dist.metadata['Name'].lower().startswith(('winrt','bleak')):
        command.extend(['--copy-metadata',dist.metadata['Name']])
command.append(str(ROOT/'app/revisions/v5/launch.py'))
windows=Path(os.environ.get('WINDIR','C:/Windows'))
environment=dict(os.environ,PATH=os.pathsep.join([str(Path(sys.executable).parent),str(Path(sys.base_prefix)),str(windows/'System32'),str(windows)]),
                 PYTHONPATH=os.pathsep.join([str(BLE),str(ROOT/'app/revisions/v5'),str(ROOT/'app/ble_prototype/v1')]))
print('Building integrated UWB Board Programmer 2.1.0',flush=True)
with (ROOT/'verification/package-integrated-v5.log').open('x',encoding='utf8') as log:
    subprocess.run(command,check=True,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
target=release/name
shutil.copytree(ROOT/'resources',target/'resources')
shutil.copytree(ROOT/'docs',target/'docs',ignore=shutil.ignore_patterns('vendor','archive'))
manifest,entries=latest_bundle(ROOT)
copy_files=[manifest]
for entry in entries:copy_files.append(validate_image(ROOT,entry))
legacy=bundles(ROOT)
if legacy:
    copy_files.append(legacy[0]);copy_files.extend(e['path'] for e in images(ROOT,legacy[0]).values())
copy_files.extend(ROOT/'tools/dk6'/name for name in ['DK6Programmer.exe','ftd2xx.dll','libgcc_s_dw2-1.dll','pdcurses.dll','programmer.dll'])
copied=[]
for source in copy_files:
    relative=source.resolve().relative_to(ROOT);destination=target/relative;destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():raise FileExistsError(destination)
    shutil.copy2(source,destination)
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    if digest!=hashlib.sha256(source.read_bytes()).hexdigest():raise RuntimeError('Package copy mismatch')
    copied.append(dict(file=relative.as_posix(),sha256=digest,bytes=destination.stat().st_size))
with (target/'programmer-workspace.json').open('x',encoding='utf8') as out:
    json.dump(dict(application='UWB Board Programmer',version='2.1.0',schema=1),out,indent=2)
with (target/'package-manifest.v1.json').open('x',encoding='utf8') as out:
    json.dump(dict(version='2.1.0',firmware=entries[0]['version'],files=copied,
                   credentials_included=False,recordings_included=False,external_python_required=False),out,indent=2)
print('PACKAGED '+str(target/(name+'.exe')),flush=True)
