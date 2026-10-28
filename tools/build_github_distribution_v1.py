"""Publish a self-contained Git payload from an existing, verified desktop build.

Developer-only build tool. End users run START_HERE.cmd; they need no Python.
Creates new files only and refuses to replace an earlier distribution.
"""
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'releases/desktop-v5/UWB_Board_Programmer_2_1_0'
DEPLOY = ROOT / 'deployment/windows-x64'
DEST = DEPLOY / '2.1.0/UWB_Board_Programmer_2_1_0_Windows_x64.zip'
MANIFEST = DEPLOY / 'distribution.v1.json'
LAUNCHER = DEPLOY / 'UWB_Board_Programmer_Launcher.exe'


def digest(content):
    return hashlib.sha256(content).hexdigest()


def notices():
    result = {}
    packages = []
    prefixes = ('bidict-', 'certifi-', 'charset_normalizer-', 'h11-', 'idna-',
                'numpy-', 'packaging-', 'pycryptodome-', 'pyserial-', 'pyside6',
                'python_engineio-', 'python_socketio-', 'requests-', 'scipy-',
                'shiboken6-', 'simple_websocket-', 'urllib3-', 'websocket_client-',
                'wsproto-', 'bleak-', 'winrt_', 'pyinstaller-')
    for folder in (ROOT/'runtime/python-v1/Lib/site-packages', ROOT/'runtime/ble-bench-v2/Lib/site-packages'):
        for info in sorted(folder.glob('*.dist-info')):
            if not info.name.lower().startswith(prefixes):
                continue
            packages.append(info.name.removesuffix('.dist-info'))
            for file in info.rglob('*'):
                if file.is_file() and any(word in file.name.lower() for word in ('license', 'copying', 'notice', 'copyright')):
                    result['licenses/python-packages/'+info.name+'/'+file.relative_to(info).as_posix()] = file.read_bytes()
    result['licenses/CPython-LICENSE.txt'] = (Path(sys.base_prefix)/'LICENSE.txt').read_bytes()
    for file in (ROOT/'deployment/notices/Qt').glob('*.txt'):
        result['licenses/Qt/'+file.name] = file.read_bytes()
    if 'licenses/Qt/LGPL-3.0-only.txt' not in result:
        raise FileNotFoundError('Qt license texts are required under deployment/notices/Qt.')
    archive = ROOT.parent/'Archive/UWBIOT_SR040_v04.03.14_MCUx.zip'
    with zipfile.ZipFile(archive) as source:
        for name in ('EULA.pdf', 'SCR.txt'):
            entry = 'UWBIOT_SR040_v04.03.14_MCUx/'+name
            result['licenses/NXP-SR040/'+name] = source.read(entry)
    archive = ROOT.parent/'Archive/Type2BP_SDK_UWBIOT_SR150_v04.06.05_MCUx.zip'
    with zipfile.ZipFile(archive) as outer:
        entry = next(name for name in outer.namelist() if name.endswith('/UWBIOT_SR150_v04.06.05_MCUx.zip'))
        with zipfile.ZipFile(io.BytesIO(outer.read(entry))) as source:
            for name in ('EULA.pdf', 'SCR.txt'):
                result['licenses/NXP-SR150/'+name] = source.read(name)
    with zipfile.ZipFile(ROOT.parent/'Archive/SDK_2_6_16_QN9090.zip') as source:
        result['licenses/NXP-QN9090/SW-Content-Register.txt'] = source.read('SW-Content-Register.txt')
    for relative, name in [
        ('vendor/originals/sr040/uwbiot-top/ext/freertos/LICENSE.md', 'FreeRTOS-LICENSE.md'),
        ('vendor/originals/qn9090-sdk/CMSIS/LICENSE.txt', 'CMSIS-LICENSE.txt'),
        ('tools/arm-gcc-10.3-2021.10/gcc-arm-none-eabi-10.3-2021.10/share/doc/gcc-arm-none-eabi/license.txt', 'GNU-Arm-runtime-licenses.txt'),
    ]:
        result['licenses/firmware/'+name] = (ROOT/relative).read_bytes()
    notice = '''# Third-party components

This application includes unmodified CPython, Qt for Python (PySide6/Shiboken),
NumPy, SciPy, Bleak, PyWinRT, pyserial and HTTP/Socket.IO dependencies.
Their notices and license texts are in licenses/. PyInstaller's distribution
exception applies to its bootloader; its COPYING text is included.

Qt for Python is used under LGPLv3. Qt and Shiboken DLLs remain separate in
_internal/ and may be replaced with compatible builds. Reverse engineering
for debugging modifications to LGPL components is permitted. Corresponding
upstream sources and build instructions:
https://code.qt.io/cgit/pyside/pyside-setup.git/
https://code.qt.io/cgit/qt/qtbase.git/
https://doc.qt.io/qtforpython-6/building_from_source/index.html
Use the tag matching the version listed below. This application does not
modify these libraries; its application/build sources are available at
https://github.com/COSMOnEsmer/UWBBoardProgrammer .

Compiled firmware and the included DK6 programming components target Murata
Type2BP/Type2DK EVKs using NXP QN9090/SR150/SR040 products. Use them only for
these NXP-based boards as an integrated part of this application. NXP EULAs
and Software Content Registers accompany the firmware in licenses/.
The raw vendor SDK archives and vendor source trees are not included.
The USB programming tools also include FTDI D2XX and GCC runtime components;
their original DLLs and notices are retained. FTDI drivers are supplied by
Windows Update or https://ftdichip.com/drivers/ .

Bundled Python component versions:
'''+''.join('- '+name+'\n' for name in sorted(set(packages)))
    result['THIRD_PARTY_NOTICES.md'] = notice.encode('utf8')
    return result


def main():
    for file in (DEST, MANIFEST, LAUNCHER, Path(str(LAUNCHER)+'.config')):
        if file.exists():
            raise FileExistsError('Preserving previous output: '+str(file))
    DEPLOY.mkdir(parents=True, exist_ok=True)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    compiler = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                    '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', '/r:System.Core.dll',
                    '/r:System.IO.Compression.dll', '/r:System.IO.Compression.FileSystem.dll',
                    '/r:System.Runtime.Serialization.dll', '/r:Microsoft.CSharp.dll',
                    '/win32manifest:'+str(ROOT/'deployment/Bootstrap.manifest'),
                    '/win32icon:'+str(ROOT/'resources/branding/logo-v1.ico'),
                    '/out:'+str(LAUNCHER), str(ROOT/'deployment/Bootstrap.cs')], check=True)
    shutil.copyfile(ROOT/'deployment/Bootstrap.exe.config', Path(str(LAUNCHER)+'.config'))
    files = {}
    packaged = json.loads((SOURCE/'package-manifest.v1.json').read_text(encoding='utf8'))
    for entry in packaged['files']:
        if digest((SOURCE/entry['file']).read_bytes()) != entry['sha256']:
            raise ValueError('Flash asset changed: '+entry['file'])
    for file in sorted(SOURCE.rglob('*')):
        if not file.is_file():
            continue
        relative = file.relative_to(SOURCE)
        if relative.parts[0] in ('data', 'config', 'verification', 'vendor', '.git'):
            continue
        files[relative.as_posix()] = file
    for name, content in notices().items():
        if name in files:
            raise ValueError('Duplicate archive file: '+name)
        files[name] = content
    entries = []
    with zipfile.ZipFile(DEST, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, source in sorted(files.items()):
            content = source.read_bytes() if isinstance(source, Path) else source
            archive.writestr(SOURCE.name+'/'+name, content)
            entries.append(dict(path=name, bytes=len(content), sha256=digest(content)))
    if DEST.stat().st_size >= 100*1024*1024:
        raise ValueError('Distribution exceeds GitHub single-file limit.')
    with zipfile.ZipFile(DEST) as archive:
        if archive.testzip():
            raise ValueError('ZIP verification failed.')
    manifest = dict(schema=1, version='2.1.0', archive=DEST.relative_to(ROOT).as_posix(),
                    archive_root=SOURCE.name, bytes=DEST.stat().st_size,
                    sha256=digest(DEST.read_bytes()), executable=SOURCE.name+'.exe',
                    credentials_included=False, recordings_included=False, profiles_included=False,
                    external_python_required=False, files=entries)
    with MANIFEST.open('x', encoding='utf8', newline='\n') as output:
        json.dump(manifest, output, indent=2)
        output.write('\n')
    print(json.dumps(dict(archive=str(DEST), bytes=manifest['bytes'], sha256=manifest['sha256'], files=len(entries))))


if __name__ == '__main__':
    main()
