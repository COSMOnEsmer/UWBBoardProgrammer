import asyncio
import json
import struct
import zlib
import re
import uuid
from pathlib import Path
import pytest
from uwb_battery_calibration.ble_tag import BleSurveyTag,tag_info

MAC='0200000000000101'

def test_firmware_uuid_uses_bluetooth_octet_order():
    root=Path(__file__).resolve().parents[2]
    source=(root/'firmware/source/v25-battery-radio-recovery/gatt_uuid_ubp.h').read_text()
    values=re.search(r'UUID128\(uuid_tag_radio_diag_ubp,([^)]*)\)',source).group(1)
    octets=bytes(int(word,16) for word in values.split(','))
    assert str(uuid.UUID(bytes=octets[::-1]))=='3b3386f8-26d6-5832-8fd6-8b5ebc8b820e'

def test_new_candidate_requires_the_same_commissioned_identity():
    info=dict(v=1,model='Type2DK',role='tag',mac=MAC,firmware='1.5.1-pilot',survey=1,
              battery_calibration=True,autonomous=True,radio_state='running',provisioned=True,
              interval_ms=1000,boot='12345678',config_crc='769ab90c',ble_window_remaining_s=600)
    assert tag_info(json.dumps(info).encode(),MAC)['firmware']=='1.5.1-pilot'
    for field,value in [('config_crc','00000000'),('firmware','1.5.2-pilot'),('radio_state','radio_transition_failed')]:
        with pytest.raises(ValueError):tag_info(json.dumps({**info,field:value}).encode(),MAC)

def test_decodes_frame_from_actual_native_candidate():
    # Frame emitted by the real C diagnostic function during native injection.
    raw=bytes.fromhex('01020021000000000100000001000000de9eabf0')
    tag=BleSurveyTag(MAC);tag.info={'firmware':'1.5.1-pilot'}
    class Client:
        async def read_gatt_char(self,uuid):
            assert uuid=='3b3386f8-26d6-5832-8fd6-8b5ebc8b820e';return raw
    tag.client=Client()
    assert asyncio.run(tag.diagnostic())==dict(stage=2,api_status=0,last_rf_status=33,
                                              hpd_recoveries=0,good_ranges=1,failed_ranges=1)

def test_corrupt_diagnostic_is_rejected():
    tag=BleSurveyTag(MAC);tag.info={'firmware':'1.5.1-pilot'}
    class Client:
        async def read_gatt_char(self,uuid):return bytes.fromhex('01020021000000000100000001000000de9eabf1')
    tag.client=Client()
    with pytest.raises(ValueError,match='CRC'):asyncio.run(tag.diagnostic())

def test_legacy_tag_does_not_query_a_missing_characteristic():
    tag=BleSurveyTag(MAC);tag.info={'firmware':'1.5.0-pilot'}
    assert asyncio.run(tag.diagnostic()) is None
