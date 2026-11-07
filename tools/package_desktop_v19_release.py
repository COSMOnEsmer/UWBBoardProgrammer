"""Build BLE recovery 2.8.3; reuse only verified firmware/tools from 2.8.2 ZIP.

No SDK rebuild, flashing, credentials, profiles, or recordings enter the package.
Run with the clean environment installed from requirements-build.txt and
requirements-ble-pilot.v1.txt. Existing outputs are never replaced.
"""
from pathlib import Path
import ast
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'UWB_Board_Programmer_2_8_3'
RELEASE = ROOT / 'releases/desktop-v19-release'
WORK = ROOT / 'runtime/pyinstaller-work-v19-release'
SPEC = ROOT / 'runtime/pyinstaller-spec-v19-release'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    for path in (RELEASE, WORK, SPEC):
        if path.exists():
            raise FileExistsError('Preserving earlier output: ' + str(path))
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onedir',
               '--name', NAME, '--icon', str(ROOT / 'resources/branding/logo-v1.ico'),
               '--distpath', str(RELEASE), '--workpath', str(WORK), '--specpath', str(SPEC),
               '--paths', str(ROOT / 'app/revisions/v19'),
               '--paths', str(ROOT / 'app/battery_calibration/v2'),
               '--paths', str(ROOT / 'app/ble_prototype/v1'),
               '--hidden-import', 'engineio.async_drivers.threading', '--hidden-import', 'socketio',
               '--hidden-import', 'scipy.spatial.transform._rotation_cy',
               '--collect-all', 'bleak', '--collect-all', 'winrt', '--exclude-module', 'pytest']
    for dist in importlib.metadata.distributions():
        if dist.metadata['Name'].lower().startswith(('winrt', 'bleak')):
            command.extend(['--copy-metadata', dist.metadata['Name']])
    command.append(str(ROOT / 'app/revisions/v19/launch.py'))
    environment = dict(os.environ)
    windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
    # Do not collect unrelated ICU/OpenSSL DLLs from host tools on PATH.
    environment['PATH'] = os.pathsep.join([str(Path(sys.executable).parent), str(Path(sys.base_prefix)),
                                           str(Path(sys.base_prefix) / 'DLLs'), str(windows / 'System32'), str(windows)])
    for key in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QT_QPA_PLATFORM'):
        environment.pop(key, None)
    log_path = ROOT / 'verification/package-integrated-v19-release.log'
    with log_path.open('x', encoding='utf-8') as log:
        subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    allowed = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), windows.resolve()]
    collection = ast.literal_eval((WORK / NAME / 'COLLECT-00.toc').read_text(encoding='utf-8'))[0]
    unexpected = [entry[1] for entry in collection if entry[2] == 'BINARY' and
                  not any(Path(entry[1]).resolve().is_relative_to(base) for base in allowed)]
    if unexpected:
        raise ValueError('Native DLLs outside the build/runtime directories: ' + repr(unexpected))
    target = RELEASE / NAME
    shutil.copytree(ROOT / 'resources', target / 'resources')
    shutil.copytree(ROOT / 'docs', target / 'docs', ignore=shutil.ignore_patterns('vendor', 'archive'))
    manifest = json.loads((ROOT / 'deployment/windows-x64/distribution.v15.json').read_text(encoding='utf-8'))
    archive_path = ROOT / manifest['archive']
    if archive_path.stat().st_size != manifest['bytes'] or digest(archive_path.read_bytes()) != manifest['sha256']:
        raise ValueError('Original distribution ZIP changed')
    originals = {entry['path']: entry for entry in manifest['files']}
    copied = []
    with zipfile.ZipFile(archive_path) as archive:
        for relative, expected in originals.items():
            parts = Path(relative).parts
            if parts[0] not in ('firmware', 'tools', 'licenses'):
                continue
            if parts[0] == 'licenses' and (parts[1] == 'python-packages' or parts[1].startswith('CPython-')):
                continue
            raw = archive.read(manifest['archive_root'] + '/' + relative)
            if len(raw) != expected['bytes'] or digest(raw) != expected['sha256']:
                raise ValueError('Original asset hash mismatch: ' + relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            if parts[0] in ('firmware', 'tools'):
                copied.append(dict(file=relative, bytes=len(raw), sha256=digest(raw)))
    versions = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata['Name']
        if name.lower() in ('pip', 'pytest', 'pluggy', 'iniconfig', 'pygments', 'setuptools'):
            continue
        versions[name] = dist.version
        for entry in dist.files or []:
            if '.dist-info' not in str(entry) or not any(word in entry.name.lower() for word in ('license', 'copying', 'copyright', 'notice')):
                continue
            source = Path(dist.locate_file(entry))
            if source.is_file():
                destination = target / 'licenses/python-packages' / str(entry)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', target / 'licenses/CPython-LICENSE.txt')
    with zipfile.ZipFile(archive_path) as archive:
        old_notice = archive.read(manifest['archive_root'] + '/THIRD_PARTY_NOTICES.md').decode('utf-8')
    notice = old_notice.split('Bundled Python component versions:')[0]
    notice += 'Bundled Python component versions:\n\n' + ''.join('- ' + k + '==' + v + '\n' for k, v in sorted(versions.items()))
    (target / 'THIRD_PARTY_NOTICES.md').write_text(notice, encoding='utf-8')
    (target / 'programmer-workspace.json').write_text(json.dumps(dict(application='UWB Board Programmer', version='2.8.3', schema=1), indent=2), encoding='utf-8')
    package = dict(version='2.8.3', firmware='1.4.1-pilot', files=copied,
                   credentials_included=False, profiles_included=False, recordings_included=False,
                   external_python_required=False, build_python=sys.version, packages=versions)
    (target / 'package-manifest.v1.json').write_text(json.dumps(package, indent=2), encoding='utf-8')
    print(json.dumps(dict(executable=str(target / (NAME + '.exe')), log=str(log_path))), flush=True)


if __name__ == '__main__':
    main()
