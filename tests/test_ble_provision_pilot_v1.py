import json
from pathlib import Path
import struct
import sys
import zlib
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from uwb_ble_receiver_v4 import Binding,device_info


def test_receiver_requires_crc_verified_persistent_identity():
    mac='0200000000000001';binding=Binding('A1',mac,'master')
    crc=zlib.crc32(struct.pack('<I8sII',0xE2E11001,bytes.fromhex(mac),500,1))&0xffffffff
    info=dict(v=1,model='Type2BP',role='master',mac=mac,boot='12345678',sequence=0,
              firmware='1.3.1-pilot',autonomous=True,radio_state='running',
              provisioned=True,interval_ms=500,config_crc=f'{crc:08x}')
    assert device_info(json.dumps(info).encode(),binding)['provisioned'] is True
    for changes in [dict(provisioned=False),dict(config_crc='00000000'),dict(interval_ms=1000)]:
        with pytest.raises(ValueError):device_info(json.dumps({**info,**changes}).encode(),binding)
