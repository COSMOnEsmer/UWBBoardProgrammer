"""Restore a verified QN9090 application readback; preserve the protected tail.

This intentionally writes host Flash. Use the backup manifest for the same USB
device. Never use another board's backup. Does not touch OTP/EFUSE or radio NVM.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--port', required=True)
    args=parser.parse_args()
    manifest=args.manifest.resolve()
    data=json.loads(manifest.read_text(encoding='utf8'))
    if not data.get('host_flash_backup_verified') or not data.get('flash_copies_match'):
        raise RuntimeError('Two matching original backups are required')
    if data.get('coverage_bytes')!=0x9dc00 or len(data.get('files',[]))<2:
        raise RuntimeError('Unsupported backup coverage')
    copies=[]
    for row in data['files'][:2]:
        path=(manifest.parent/row['file']).resolve()
        if path.parent!=manifest.parent or row['bytes']!=0x9dc00:
            raise RuntimeError('Invalid backup path/size')
        raw=path.read_bytes()
        if len(raw)!=0x9dc00 or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise RuntimeError('Backup integrity failure')
        copies.append(path)
    if data['files'][0]['sha256']!=data['files'][1]['sha256']:
        raise RuntimeError('Backup copies do not match')
    found=[p for p in list_ports.comports() if p.device.upper()==args.port.upper()]
    if len(found)!=1 or found[0].serial_number!=data.get('usb_serial'):
        raise RuntimeError('Backup belongs to a different physical USB device')
    if (found[0].vid,found[0].pid)!=(0x0403,0x6015):
        raise RuntimeError('Unsupported USB interface')
    folder=ROOT/'verification/host-restores'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    command=[str(ROOT/'tools/dk6/DK6Programmer.exe'),'-V','0','-P','115200',
             '-s',args.port,'-Y','-p',str(copies[0]),'-v']
    report=dict(manifest=str(manifest),port=args.port,sha256=data['files'][0]['sha256'],
                bytes=0x9dc00,protected_tail_written=False,command=command)
    try:
        process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                               timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
        with (folder/'programmer.log').open('xb') as output:output.write(process.stdout)
        report['returncode']=process.returncode
        report['program_and_verify_passed']=(process.returncode==0 and
                         b'Memory verified successfully' in process.stdout)
    except Exception as error:
        report['error']=repr(error)
        report['program_and_verify_passed']=False
    with (folder/'restore-report.json').open('x',encoding='utf8') as output:
        json.dump(report,output,indent=2)
    print(json.dumps(dict(report=str(folder/'restore-report.json'),**report)))
    return 0 if report['program_and_verify_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
