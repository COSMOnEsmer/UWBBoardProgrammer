"""Package a fresh Windows desktop release without replacing any earlier build."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parents[1]
release=root/'releases/desktop-v2';work=root/'runtime/pyinstaller-work-v2';spec=root/'runtime/pyinstaller-spec-v2'
if any(path.exists() for path in (release,work,spec)):raise FileExistsError('Use a new package revision.')
command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','UWB_Board_Programmer','--icon',str(root/'resources/branding/logo-v1.ico'),'--distpath',str(release),'--workpath',str(work),'--specpath',str(spec),'--paths',str(root/'app/revisions/v3'),'--hidden-import','engineio.async_drivers.threading','--hidden-import','socketio','--hidden-import','scipy.spatial.transform._rotation_cy',str(root/'app/revisions/v3/launch.py')]
# Avoid unrelated Qt/Poppler binaries on the machine's PATH entering the package.
windows=Path(os.environ.get('WINDIR','C:/Windows'))
environment=dict(os.environ,PATH=os.pathsep.join([str(Path(sys.executable).parent),str(Path(sys.base_prefix)),str(windows/'System32'),str(windows)]))
subprocess.run(command,check=True,cwd=root,env=environment)
print(release/'UWB_Board_Programmer/UWB_Board_Programmer.exe')
