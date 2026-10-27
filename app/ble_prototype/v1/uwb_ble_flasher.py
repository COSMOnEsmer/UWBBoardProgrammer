"""One physical EVK at a time: verify identity, back up twice, program, verify.

Only the selected board is required. Original files and earlier backups are kept.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import time
import zlib


def inventory():
    from serial.tools import list_ports
    return [p for p in list_ports.comports() if (p.vid,p.pid)==(0x0403,0x6015) and p.serial_number]


def latest_bundle(root):
    found=[]
    for path in (Path(root)/'firmware/releases/_experimental').glob('*/bundle-manifest.json'):
        value=json.loads(path.read_text(encoding='utf8'))
        images=value.get('images',[])
        if images and all(e.get('config_crc') and e.get('image_label') for e in images):
            found.append((value.get('created_utc',''),path,images))
    if not found:raise ValueError('Build the provisioned pilot firmware bundle first')
    _,path,images=max(found,key=lambda row:row[0])
    return path,images


def validate_image(root,entry):
    root=Path(root).resolve();path=(root/entry['file']).resolve()
    if not path.is_relative_to(root):raise ValueError('Firmware must remain in this workspace')
    raw=path.read_bytes()
    if not 44<=len(raw)<=0x90000 or len(raw)!=entry['bytes']:
        raise ValueError('Image size/allocation mismatch')
    words=struct.unpack('<11I',raw[:44])
    if sum(words[:8])&0xffffffff or zlib.crc32(raw[:40])&0xffffffff!=words[10]:
        raise ValueError('Invalid boot vector/header checksum')
    if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Firmware SHA-256 mismatch')
    mac=bytes.fromhex(entry['provisioned_mac'])
    role=2 if entry['model']=='Type2DK' else (1 if entry['role']=='master' else 0)
    crc=zlib.crc32(struct.pack('<I8sII',0xE2E11001,mac,entry['interval_ms'],role))&0xffffffff
    if len(mac)!=8 or entry['config_crc']!=f'{crc:08x}':raise ValueError('Provisioning manifest checksum')
    return path


def _identity(port,serial_number):
    matches=[p for p in inventory() if p.device.upper()==port.upper() and p.serial_number==serial_number]
    if len(matches)!=1:raise ValueError('Selected USB identity changed or disconnected')


def flash_selected(root,entry,port,serial_number,log=lambda value:None):
    root=Path(root).resolve();image=validate_image(root,entry);_identity(port,serial_number)
    folder=root/'verification/flash-jobs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    result=dict(port=port,usb_serial=serial_number,image=str(image),image_label=entry['image_label'],
                mac=entry['provisioned_mac'],program_verify_passed=False,configuration_acknowledged=False,
                protected_tail_written=False,real_rf_measurements_verified=False)
    try:
        log('Reading two backups from '+port+'; keep this board connected')
        backup=subprocess.run([str(root/'runtime/python-v1/Scripts/python.exe'),
                str(root/'tools/backup_host_flash_v1.py'),'--port',port,'--expected-usb-serial',serial_number],
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=420,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (folder/'backup.log').open('xb') as output:output.write(backup.stdout)
        if backup.returncode:raise ValueError('Backup failed; no firmware programming was attempted')
        summary=json.loads(backup.stdout.decode('utf8').strip().splitlines()[-1])
        if not summary.get('verified'):raise ValueError('Original backup was not verified')
        manifest=Path(summary['manifest']);saved=json.loads(manifest.read_text(encoding='utf8'))
        if not saved.get('flash_copies_match') or saved.get('coverage_bytes')!=0x9dc00:
            raise ValueError('Backup copies or coverage are not valid')
        for row in saved['files'][:2]:
            if hashlib.sha256((manifest.parent/row['file']).read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('Backup integrity changed')
        result['pre_flash_backup']=str(manifest)
        _identity(port,serial_number)
        log('Backup verified. Programming '+entry['anchor_slot']+' / '+entry['provisioned_mac'])
        command=[str(root/'tools/dk6/DK6Programmer.exe'),'-V','0','-P','115200','-s',port,'-Y','-p',str(image),'-v']
        program=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with (folder/'programmer.log').open('xb') as output:output.write(program.stdout)
        if program.returncode or b'Memory verified successfully' not in program.stdout:
            raise ValueError('Programming/verify failed; use the saved same-board backup for recovery')
        result['program_verify_passed']=True
        _identity(port,serial_number)
        log('Flash bytes verified. Listening for autonomous configuration acknowledgement')
        import serial
        handle=serial.Serial(port=None,baudrate=3_000_000,timeout=.1)
        handle.port=port;handle.rts=False;handle.dtr=False
        raw=bytearray()
        with handle:
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:raw.extend(handle.read(min(handle.in_waiting or 1,4096)))
        with (folder/'uart.bin').open('xb') as output:output.write(raw)
        text=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',bytes(raw))
        for line in text.splitlines():
            start=line.find(b'{"v":1,')
            if start<0:continue
            try:message=json.JSONDecoder().raw_decode(line[start:].decode('utf8'))[0]
            except (ValueError,UnicodeError):continue
            if message.get('kind')=='hello':
                result['last_hello']=message
                expected_role='tag' if entry['model']=='Type2DK' else entry['role']
                if (message.get('model')==entry['model'] and message.get('role')==expected_role and
                    message.get('version')==entry['version'] and message.get('mac')==entry['provisioned_mac'] and
                    message.get('config_crc')==entry['config_crc'] and message.get('provisioned') is True):
                    result['configuration_acknowledged']=True
        log('Configuration acknowledged' if result['configuration_acknowledged'] else
            'Flash verified; board acknowledgement pending. Check BLE/USB diagnostics before deployment.')
    except Exception as error:
        result['error']=type(error).__name__+': '+str(error);log(result['error'])
    result['report']=str(folder/'report.json')
    with (folder/'report.json').open('x',encoding='utf8') as output:json.dump(result,output,indent=2)
    return result
