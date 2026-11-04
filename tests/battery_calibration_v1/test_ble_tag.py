import asyncio
import json
import struct
import time
import zlib
import pytest
from uwb_board_programmer.survey_protocol import STATUS,COMMAND
from uwb_battery_calibration.ble_tag import advertisement_tag,tag_info,BleSurveyTag

MAC='0200000000000101'
def info(**changes):
    value=dict(v=1,model='Type2DK',role='tag',mac=MAC,firmware='1.5.0-pilot',survey=1,
               battery_calibration=True,autonomous=True,radio_state='running',provisioned=True,
               interval_ms=1000,boot='12345678',config_crc='769ab90c',ble_window_remaining_s=600)
    value.update(changes);return json.dumps(value).encode()

def test_tag_advertisement_does_not_match_an_anchor():
    assert advertisement_tag(b'\x01\x02'+bytes.fromhex(MAC),MAC)
    assert not advertisement_tag(b'\x01\x00'+bytes.fromhex(MAC),MAC)
    assert not advertisement_tag(b'\x01\x02'+bytes.fromhex('0200000000000001'),MAC)

def test_info_rejects_wrong_role_identity_and_unverified_protocol():
    assert tag_info(info(),MAC)['model']=='Type2DK'
    for changes in (dict(model='Type2BP'),dict(role='master'),dict(config_crc='00000000'),
                    dict(mac='0200000000000001'),dict(firmware='1.4.2-pilot'),dict(ble_window_remaining_s=-1)):
        with pytest.raises(ValueError):tag_info(info(**changes),MAC)

def packet(mode,request,session,peer):
    raw=STATUS.pack(1,mode,0,request,session,bytes.fromhex(peer),0)
    return raw[:-4]+struct.pack('<I',zlib.crc32(raw[:-4])&0xffffffff)

def test_gatt_ack_binding_and_expiring_window():
    tag=BleSurveyTag(MAC);tag.info=tag_info(info(),MAC);tag.connected_at=time.monotonic();writes=[]
    class Client:
        async def write_gatt_char(self,uuid,data,*,response):writes.append(COMMAND.unpack(data))
        async def read_gatt_char(self,uuid):return packet(2,17,42,'0200000000000001')
    tag.client=Client()
    result=asyncio.run(tag.set_mode(2,request=17,session=42,peer='0200000000000001',lease_ms=30000))
    assert result['request']==17 and writes[0][2]==17
    tag.info['ble_window_remaining_s']=10
    with pytest.raises(ValueError,match='expiring'):
        asyncio.run(tag.set_mode(2,request=18,session=42,peer='0200000000000001',lease_ms=30000))
    assert len(writes)==1  # Never send an active command beyond the window.

def test_unrelated_ack_cannot_be_accepted():
    tag=BleSurveyTag(MAC);tag.info=tag_info(info(),MAC);tag.connected_at=time.monotonic()
    class Client:
        async def write_gatt_char(self,*args,**kwargs):pass
        async def read_gatt_char(self,uuid):return packet(2,17,43,'0200000000000001')
    tag.client=Client()
    with pytest.raises(ValueError,match='rejected'):
        asyncio.run(tag.set_mode(2,request=17,session=42,peer='0200000000000001',lease_ms=30000))

def test_disconnected_tag_is_not_reported_as_restored():
    tag=BleSurveyTag(MAC)
    class Client:
        is_connected=False
        async def disconnect(self):pass
    tag.client=Client()
    with pytest.raises(ConnectionError,match='restoration'):
        asyncio.run(tag.__aexit__(None,None,None))
