"""Package the verified 2.8.3 desktop without private workspace data or SDK inputs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'releases/desktop-v19-release/UWB_Board_Programmer_2_8_3'
DEPLOY = ROOT / 'deployment/windows-x64'
DEST = DEPLOY / '2.8.3-final/UWB_Board_Programmer_2_8_3_Windows_x64.zip'
MANIFEST = DEPLOY / 'distribution.v16.json'
LAUNCHER = DEPLOY / 'UWB_Board_Programmer_Launcher_v16.exe'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    for path in (DEST, MANIFEST, LAUNCHER, Path(str(LAUNCHER) + '.config')):
        if path.exists():
            raise FileExistsError('Preserving earlier output: ' + str(path))
    package = json.loads((SOURCE / 'package-manifest.v1.json').read_text(encoding='utf-8'))
    for entry in package['files']:
        if digest((SOURCE / entry['file']).read_bytes()) != entry['sha256']:
            raise ValueError('Firmware/tool asset changed: ' + entry['file'])
    DEST.parent.mkdir(parents=True)
    entries = []
    with zipfile.ZipFile(DEST, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(SOURCE.rglob('*')):
            if not source.is_file():
                continue
            relative = source.relative_to(SOURCE)
            if relative.parts[0] in ('data', 'config', 'verification', 'vendor', '.git'):
                continue
            raw = source.read_bytes()
            archive.writestr(SOURCE.name + '/' + relative.as_posix(), raw)
            entries.append(dict(path=relative.as_posix(), bytes=len(raw), sha256=digest(raw)))
    with zipfile.ZipFile(DEST) as archive:
        if archive.testzip():
            raise ValueError('ZIP verification failed')
    compiler = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                    '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', '/r:System.Core.dll',
                    '/r:System.IO.Compression.dll', '/r:System.IO.Compression.FileSystem.dll',
                    '/r:System.Runtime.Serialization.dll', '/r:Microsoft.CSharp.dll',
                    '/win32manifest:' + str(ROOT / 'deployment/Bootstrap.manifest'),
                    '/win32icon:' + str(ROOT / 'resources/branding/logo-v1.ico'),
                    '/out:' + str(LAUNCHER), str(ROOT / 'deployment/Bootstrap.v16.cs')], check=True)
    shutil.copy2(ROOT / 'deployment/Bootstrap.exe.config', Path(str(LAUNCHER) + '.config'))
    manifest = dict(schema=1, version='2.8.3', archive=DEST.relative_to(ROOT).as_posix(),
                    archive_root=SOURCE.name, bytes=DEST.stat().st_size, sha256=digest(DEST.read_bytes()),
                    executable=SOURCE.name + '.exe', credentials_included=False,
                    profiles_included=False, recordings_included=False, external_python_required=False,
                    files=entries)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(archive=str(DEST), bytes=manifest['bytes'], files=len(entries),
                          github_single_file_limit_ok=manifest['bytes'] < 100*1024*1024)), flush=True)


if __name__ == '__main__':
    main()
