"""Exercise the shipped launcher without local Python, SDK or attached boards.

Run with a developer Python. Everything under verification is a NEW copy.
No Flash, serial acquisition or RTLS traffic is initiated.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    work = ROOT/'verification'/('github-portable-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work.mkdir(parents=True, exist_ok=False)
    checkout = work/'เครื่องใหม่ มีช่องว่าง'/'UWBBoardProgrammer'
    deploy = checkout/'deployment/windows-x64'
    shutil.copytree(ROOT/'deployment/windows-x64', deploy)
    shutil.copy2(ROOT/'START_HERE.cmd', checkout/'START_HERE.cmd')
    launcher = deploy/'UWB_Board_Programmer_Launcher.exe'
    manifest = json.loads((deploy/'distribution.v1.json').read_text(encoding='utf8'))
    windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
    env = {key:value for key,value in os.environ.items() if not key.upper().startswith(('PYTHON', 'QT_', 'UWB_'))}
    env.update(PATH=os.pathsep.join([str(windows/'System32'), str(windows)]), QT_QPA_PLATFORM='offscreen')
    checks = []

    def launch(folder, name, extra=(), expected=0):
        report = work/(name+'.json')
        command = [str(launcher), '--root', str(folder), '--no-shortcut', '--report', str(report), *extra]
        process = subprocess.run(command, cwd=work, env=env, capture_output=True, timeout=90)
        assert process.returncode == expected, (name, process.returncode, process.stdout, process.stderr)
        value = json.loads(report.read_text(encoding='utf8')) if report.exists() else None
        checks.append(dict(check=name, passed=True, exit_code=process.returncode))
        return value

    launch(checkout, 'archive-verification', ['--verify-only'])
    assert not (checkout/'runtime').exists()
    prepared = launch(checkout, 'first-installation', ['--prepare-only'])
    assert prepared['ReusedInstallation'] is False
    assert prepared['VerifiedFiles'] == len(manifest['files'])
    app = Path(prepared['ApplicationRoot'])
    assert not (app/'data').exists() and not (app/'config').exists()
    repeated = launch(checkout, 'reuse-installation', ['--prepare-only'])
    assert repeated['ReusedInstallation'] is True
    assert repeated['ApplicationRoot'] == str(app)
    smoke = work/'application-smoke.json'
    launched = launch(checkout, 'no-python-launch', ['--smoke-output', str(smoke)])
    result = json.loads(smoke.read_text(encoding='utf8'))
    assert result['packed'] and result['version'] == '2.1.0'
    assert result['pages'] == 6 and result['anchor_rows'] == 4
    assert result['firmware_bundles'] >= 1
    assert not result['automatic_acquisition'] and not result['automatic_cloud']
    assert launched['ApplicationExitCode'] == 0
    for file in manifest['files']:
        path = app/file['path']
        assert path.stat().st_size == file['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256']
    # Damage a disposable installed copy, then prove repair preserves that copy.
    damaged = app/'THIRD_PARTY_NOTICES.md'
    damaged.write_text('Disposable verification fixture: damaged cache.', encoding='utf8')
    repaired = launch(checkout, 'repair-without-overwrite', ['--prepare-only'])
    assert repaired['ApplicationRoot'] != str(app)
    assert damaged.read_text(encoding='utf8') == 'Disposable verification fixture: damaged cache.'
    assert (Path(repaired['ApplicationRoot'])/'THIRD_PARTY_NOTICES.md').stat().st_size > 100
    again = launch(checkout, 'reuse-repaired-installation', ['--prepare-only'])
    assert again['ReusedInstallation'] and again['ApplicationRoot'] == repaired['ApplicationRoot']
    # Small, self-contained malicious archive fixtures need no 95 MB copies.
    for case, zipname in [('traversal', '../escape.txt'), ('unexpected-file', 'App/unlisted.dll')]:
        fixture = work/case
        folder = fixture/'deployment/windows-x64'
        folder.mkdir(parents=True)
        payload = folder/'test.zip'
        with zipfile.ZipFile(payload, 'x') as archive:
            archive.writestr('App/application.exe', b'not executed')
            archive.writestr(zipname, b'not allowed')
        content = payload.read_bytes()
        test_manifest = dict(schema=1, version='0.0.1', archive='deployment/windows-x64/test.zip',
                             archive_root='App', bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
                             executable='application.exe', files=[dict(path='application.exe', bytes=12,
                             sha256=hashlib.sha256(b'not executed').hexdigest())])
        (folder/'distribution.v1.json').write_text(json.dumps(test_manifest), encoding='utf8')
        launch(fixture, 'reject-'+case, ['--prepare-only'], expected=1)
        assert not (fixture/'runtime/installed/escape.txt').exists()
    invalid = work/'invalid-archive'
    folder = invalid/'deployment/windows-x64'
    folder.mkdir(parents=True)
    (folder/'distribution.v1.json').write_text(json.dumps(manifest), encoding='utf8')
    target = invalid/manifest['archive']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'Incomplete or corrupted git download.')
    launch(invalid, 'reject-incomplete-payload', ['--verify-only'], expected=1)
    report = dict(checks=checks, application=result, version='2.1.0',
                  python_on_launch_path=False, board_flash_attempted=False, cloud_traffic_started=False,
                  files_verified=len(manifest['files']), archive_bytes=manifest['bytes'],
                  archive_sha256=manifest['sha256'], disposable_checkout=str(checkout))
    with (work/'report.json').open('x', encoding='utf8') as output:
        json.dump(report, output, indent=2, ensure_ascii=False)
    print(json.dumps(dict(report=str(work/'report.json'), checks=len(checks), passed=True)))


if __name__ == '__main__':
    main()
