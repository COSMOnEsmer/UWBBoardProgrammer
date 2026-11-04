"""Leased Type2DK GATT control with no USB dependency during ranging."""
import asyncio
import json
import secrets
import struct
import time
import zlib
from uwb_ble_wire import SERVICE_UUID,INFO_UUID
from uwb_board_programmer.survey_protocol import CONTROL_UUID,STATUS_UUID,command,status

def advertisement_tag(data,expected_mac):
    value=bytes(data)
    return len(value)==10 and value[:2]==b'\x01\x02' and value[2:].hex().upper()==expected_mac.upper()

def tag_info(raw,expected_mac):
    if len(raw)>1024:raise ValueError('Tag info exceeds protocol size')
    info=json.loads(bytes(raw).decode('utf8'))
    if not isinstance(info,dict):raise ValueError('Tag info protocol')
    if info.get('v')!=1 or info.get('model')!='Type2DK' or info.get('role')!='tag' or info.get('mac','').upper()!=expected_mac.upper():
        raise ValueError('BLE device is not the commissioned Type2DK Tag')
    if info.get('firmware')!='1.5.0-pilot' or info.get('battery_calibration') is not True or info.get('survey')!=1:
        raise ValueError('Tag requires the experimental BLE calibration firmware')
    if info.get('autonomous') is not True or info.get('radio_state')!='running' or info.get('provisioned') is not True:
        raise ValueError('Autonomous Tag radio is not ready')
    interval=info.get('interval_ms')
    if type(interval) is not int or not 100<=interval<=10000:raise ValueError('Tag interval')
    crc=zlib.crc32(struct.pack('<I8sII',0xE2E11001,bytes.fromhex(expected_mac),interval,2))&0xffffffff
    if info.get('config_crc','').lower()!=f'{crc:08x}':raise ValueError('Tag provisioning CRC mismatch')
    if not isinstance(info.get('boot'),str) or len(info['boot'])!=8:raise ValueError('Tag boot identifier')
    int(info['boot'],16)
    remaining=info.get('ble_window_remaining_s')
    if type(remaining) is not int or not 0<=remaining<=900:raise ValueError('Tag calibration window')
    return info

class BleSurveyTag:
    def __init__(self,mac,log=lambda line:None):
        if len(bytes.fromhex(mac))!=8:raise ValueError('Tag MAC')
        self.mac=mac.upper();self.log=log;self.client=None;self.info=None;self.connected_at=0
    async def __aenter__(self):
        from bleak import BleakScanner,BleakClient
        found=[]
        def detect(device,adv):
            if advertisement_tag(adv.service_data.get(SERVICE_UUID,b''),self.mac):found.append(device)
        async with BleakScanner(detect,scanning_mode='active'):
            for _ in range(150):
                if found:break
                await asyncio.sleep(.1)
        if not found:raise ValueError('Battery calibration Tag not advertising. Reset the Tag to open its BLE window; check firmware and power.')
        self.client=BleakClient(found[0],winrt={'use_cached_services':False},timeout=12)
        try:
            await self.client.connect()
            self.info=tag_info(await self.client.read_gatt_char(INFO_UUID),self.mac);self.connected_at=time.monotonic()
            self.log('Type2DK BLE control connected / '+self.info['firmware'])
            return self
        except BaseException:
            await self.client.disconnect();raise
    def remaining(self):return self.info['ble_window_remaining_s']-(time.monotonic()-self.connected_at)
    async def set_mode(self,mode,*,request,peer='0000000000000000',session=0,lease_ms=0):
        if mode and self.remaining()<lease_ms/1000+10:
            raise ValueError('Tag calibration window is expiring; restore first, then Reset the Tag')
        payload=command(mode,request,peer,session,lease_ms)
        await asyncio.wait_for(self.client.write_gatt_char(CONTROL_UUID,payload,response=True),8)
        deadline=time.monotonic()+12;last=None
        while time.monotonic()<deadline:
            last=status(await asyncio.wait_for(self.client.read_gatt_char(STATUS_UUID),8))
            if last['request']==request:
                if last['status'] or last['mode']!=mode or last['session']!=session or last['peer']!=peer.upper():
                    raise ValueError('Tag rejected BLE calibration command: '+str(last))
                return last
            await asyncio.sleep(.05)
        raise TimeoutError('Tag BLE calibration acknowledgement missing: '+str(last))
    async def __aexit__(self,exc_type,*args):
        error=None
        try:
            if self.client and self.client.is_connected:
                await self.set_mode(0,request=secrets.randbelow(0xfffffffe)+1)
            elif self.client:
                raise ConnectionError('Tag disconnected before restoration could be acknowledged')
        except Exception as failure:error=failure;self.log('Tag restore not acknowledged; firmware lease remains the fallback: '+str(failure))
        finally:
            if self.client:await self.client.disconnect()
        if error is not None and exc_type is None:raise error
