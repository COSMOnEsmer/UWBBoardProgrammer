"""Software-only flash admission tests; no hardware tools are launched."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
import struct
import sys
import zlib
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
import uwb_ble_flasher as module


def image(root):
    words=[0x040157e0,0x101,0,0,0,0,0,0,0,64,0]
    words[7]=(-sum(words[:7]))&0xffffffff
    raw=bytearray(struct.pack('<11I',*words)+bytes(20))
    raw[40:44]=struct.pack('<I',zlib.crc32(raw[:40])&0xffffffff)
    path=root/'image.bin';path.write_bytes(raw)
    mac='0200000000000001'
    crc=zlib.crc32(struct.pack('<I8sII',0xE2E11001,bytes.fromhex(mac),500,1))&0xffffffff
    return dict(file=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                provisioned_mac=mac,model='Type2BP',role='master',interval_ms=500,
                config_crc=f'{crc:08x}',anchor_slot='A1',image_label='master')


def test_only_selected_board_is_needed_and_failed_backup_never_programs(tmp_path,monkeypatch):
    entry=image(tmp_path);calls=[]
    monkeypatch.setattr(module,'inventory',lambda:[SimpleNamespace(device='COM99',serial_number='TEST-ONLY')])
    def run(command,**kwargs):calls.append(command);return SimpleNamespace(returncode=1,stdout=b'backup unavailable')
    monkeypatch.setattr(module.subprocess,'run',run)
    result=module.flash_selected(tmp_path,entry,'COM99','TEST-ONLY')
    assert len(calls)==1 and '--expected-usb-serial' in calls[0]
    assert '-p' not in calls[0] and not result['program_verify_passed']
    assert 'no firmware programming' in result['error']


def test_wrong_usb_identity_stops_before_any_backup_or_program(tmp_path,monkeypatch):
    entry=image(tmp_path)
    monkeypatch.setattr(module,'inventory',lambda:[SimpleNamespace(device='COM99',serial_number='ANOTHER-BOARD')])
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('No hardware tool should run'))
    with pytest.raises(ValueError,match='USB identity'):module.flash_selected(tmp_path,entry,'COM99','TEST-ONLY')


def test_corrupt_provision_manifest_is_rejected_before_hardware(tmp_path):
    entry=image(tmp_path);entry['config_crc']='00000000'
    with pytest.raises(ValueError,match='Provisioning'):module.validate_image(tmp_path,entry)
