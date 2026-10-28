"""QN9090 host readback, with USB identity check and two independent copies.

No erase/program/unlock command is issued. Protected FLASH tail and radio NVM
are excluded. Use only on the supported Murata Type2BP/Type2DK QN9090 EVKs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]
COVERAGE=0x9dc00


def backup_host(root, port, serial_number):
    ROOT=Path(root).resolve()
    args=argparse.Namespace(port=port,expected_usb_serial=serial_number)
    matches=[p for p in list_ports.comports() if p.device.upper()==args.port.upper()]
    if len(matches)!=1 or matches[0].serial_number!=args.expected_usb_serial:
        raise RuntimeError('The expected physical USB device is not on that COM port')
    if (matches[0].vid, matches[0].pid)!=(0x0403,0x6015):
        raise RuntimeError('This helper supports the documented EVK FTDI interface only')
    folder=ROOT/'verification/host-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True, exist_ok=False)
    record=dict(port=args.port, usb_serial=args.expected_usb_serial,
                coverage_bytes=COVERAGE, protected_tail_readable=False,
                host_flash_backup_verified=False, files=[], commands=[])
    exe=ROOT/'tools/dk6/DK6Programmer.exe'

    def run(extra, label):
        command=[str(exe), '-V','0','-P','115200','-s',args.port,*extra]
        process=subprocess.run(command, cwd=folder, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=180,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        with (folder/(label+'.log')).open('xb') as output:
            output.write(process.stdout)
        record['commands'].append(dict(command=command, returncode=process.returncode))
        return process

    try:
        device=run(['-m'],'device')
        if device.returncode or b'Detected QN9090' not in device.stdout:
            raise RuntimeError('QN9090 bootloader did not identify successfully; no Flash writes permitted')
        for suffix in ('a','b'):
            stem='original-FLASH-'+suffix
            result=run(['-d',f'FLASH:{COVERAGE}@0={stem}.bin'], 'read-'+suffix)
            actual=list(folder.glob(stem+'*.bin'))
            if result.returncode or len(actual)!=1:
                raise RuntimeError('Original readback failed')
            data=actual[0].read_bytes()
            if len(data)!=COVERAGE:
                raise RuntimeError('Backup coverage mismatch')
            record['files'].append(dict(file=actual[0].name, bytes=len(data),
                                        sha256=hashlib.sha256(data).hexdigest()))
        record['flash_copies_match']=record['files'][0]['sha256']==record['files'][1]['sha256']
        if not record['flash_copies_match']:
            raise RuntimeError('Readback copies differ')
        record['host_flash_backup_verified']=True
    except Exception as error:
        record['error']=repr(error)
    finally:
        record['scope']='Host FLASH [0,0x9DC00); excludes protected tail, radio NVM and all OTP/EFUSE.'
        with (folder/'backup-manifest.json').open('x',encoding='utf8') as output:
            json.dump(record,output,indent=2)
    if not record['host_flash_backup_verified']:raise RuntimeError(record.get('error','Backup failed; no programming attempted'))
    return folder/'backup-manifest.json'
