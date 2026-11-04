"""Explicit, leased radio control for Auto Survey; never publishes RTLS data."""
import asyncio
from contextlib import AsyncExitStack
import json
import secrets
import time
from .ble_transport import advertisement_identity,device_info
from .survey_protocol import CONTROL_UUID,STATUS_UUID,TWR_UUID,command,status,ranging
from uwb_ble_wire import SERVICE_UUID,INFO_UUID


class SurveyNetwork:
    def __init__(self,bindings,log=lambda value:None,*,allow_partial=False,tag_initiator_first=False):
        if len({b.mac[-4:].upper() for b in bindings})!=len(bindings):
            raise ValueError('Auto Survey needs distinct MAC suffixes for the short-address TWR phase')
        self.bindings=bindings;self.log=log;self.clients={};self.info={};self.queue=asyncio.Queue(512)
        self.stack=AsyncExitStack();self.overflow=False;self.callbacks={};self.subscribed=set();self.modes={}
        self.last_restore_acknowledged=True
        self.allow_partial=allow_partial;self.missing=[]
        self.tag_initiator_first=tag_initiator_first

    async def __aenter__(self):
        from bleak import BleakScanner,BleakClient
        expected={b.mac.upper():b for b in self.bindings};found={};last_new=[time.monotonic()]
        def detect(device,adv):
            data=adv.service_data.get(SERVICE_UUID)
            if data is None:return
            try:mac,role=advertisement_identity(data)
            except ValueError:return
            if mac in expected and expected[mac].role==role:
                if mac not in found:last_new[0]=time.monotonic()
                found[mac]=device
        try:
            async with BleakScanner(detect,scanning_mode='active'):
                self.log('Scanning for powered survey anchors...')
                for index in range(150):
                    if len(found)==len(expected):break
                    if self.allow_partial and found and index>=30 and time.monotonic()-last_new[0]>1:break
                    await asyncio.sleep(.1)
            missing=set(expected)-set(found)
            self.missing=[expected[mac].anchor_id for mac in sorted(missing)]
            if missing and not self.allow_partial:raise ValueError('Survey anchors not advertising: '+', '.join(sorted(missing))+'. Close other BLE applications and retry.')
            if not found:raise ValueError('No powered Auto Survey anchors were found')
            for mac,binding in expected.items():
                if mac not in found:continue
                client=await self.stack.enter_async_context(BleakClient(found[mac],winrt={'use_cached_services':False},timeout=12))
                info=device_info(await client.read_gatt_char(INFO_UUID),binding)
                if info.get('survey')!=1:raise ValueError(binding.anchor_id+' requires Auto Survey firmware')
                try:version=tuple(int(part) for part in info['firmware'].split('-')[0].split('.'))
                except ValueError:version=()
                if len(version)!=3 or version<(1,4,1):raise ValueError(binding.anchor_id+' requires Auto Survey firmware 1.4.1 or newer')
                self.clients[binding.anchor_id]=client;self.info[binding.anchor_id]=info
                self.modes[binding.anchor_id]=0
                def notify(characteristic,data,aid=binding.anchor_id):
                    try:self.queue.put_nowait((time.monotonic(),aid,bytes(data)))
                    except asyncio.QueueFull:self.overflow=True
                await client.start_notify(TWR_UUID,notify)
                self.callbacks[binding.anchor_id]=notify;self.subscribed.add(binding.anchor_id)
                self.log(binding.anchor_id+' connected / '+info['firmware'])
            return self
        except BaseException:
            await self.__aexit__(None,None,None)
            raise

    async def set_mode(self,aid,mode,*,request=None,peer='0000000000000000',session=0,lease_ms=0):
        request=request or secrets.randbelow(0xfffffffe)+1
        client=self.clients[aid]
        self.modes[aid]=None
        self.log(f'{aid} radio request {request:08x} / mode {mode}')
        began=time.monotonic()
        try:await asyncio.wait_for(client.write_gatt_char(CONTROL_UUID,command(mode,request,peer,session,lease_ms),response=True),8)
        except TimeoutError as error:raise TimeoutError(aid+' ATT write timed out') from error
        self.log(f'{aid} ATT write completed in {time.monotonic()-began:.2f} s')
        end=time.monotonic()+12
        last=None
        while time.monotonic()<end:
            try:last=status(await asyncio.wait_for(client.read_gatt_char(STATUS_UUID),8))
            except TimeoutError as error:raise TimeoutError(aid+' status read timed out') from error
            if last['request']==request:
                if last['status'] or last['mode']!=mode or last['session']!=session or last['peer']!=peer.upper():
                    raise ValueError(aid+' rejected radio command: '+str(last))
                self.modes[aid]=mode
                self.log(aid+' radio acknowledged '+str(last));return last
            await asyncio.sleep(.05)
        raise TimeoutError(aid+' radio acknowledgement missing: '+str(last))

    async def restore(self):
        errors=[]
        # Stop telemetry before control traffic; serialize ATT commands across
        # WinRT links rather than queueing simultaneous long GATT procedures.
        for aid in list(self.subscribed):
            try:
                await asyncio.wait_for(self.clients[aid].stop_notify(TWR_UUID),5)
                self.subscribed.discard(aid)
            except Exception as error:errors.append(aid+' stop notify '+type(error).__name__+': '+str(error))
        for aid in self.clients:
            if self.modes.get(aid)==0:continue
            try:await self.set_mode(aid,0)
            except Exception as error:errors.append(aid+' '+type(error).__name__+': '+str(error))
        if errors:self.log('Restore acknowledgement pending; firmware leases still expire: '+'; '.join(errors))
        self.last_restore_acknowledged=not errors
        return self.last_restore_acknowledged

    async def __aexit__(self,*args):
        try:
            if self.clients:await self.restore()
        finally:
            await self.stack.aclose();self.clients.clear()

    async def measure_pair(self,initiator,responder,seconds=5.):
        if initiator==responder or not 1<=seconds<=20:raise ValueError('Survey pair/duration')
        for aid,client in self.clients.items():
            if aid not in self.subscribed:
                await client.start_notify(TWR_UUID,self.callbacks[aid]);self.subscribed.add(aid)
        lease_ms=30000
        for aid in self.clients:await self.set_mode(aid,1,lease_ms=lease_ms)
        while not self.queue.empty():self.queue.get_nowait()
        request=secrets.randbelow(0xfffffffe)+1;session=secrets.randbelow(0x7ffffffe)+1
        try:
            await self.set_mode(responder,2,request=request,session=session,peer=self.info[initiator]['mac'],lease_ms=lease_ms)
            await self.set_mode(initiator,3,request=request,session=session,peer=self.info[responder]['mac'],lease_ms=lease_ms)
            end=time.monotonic()+seconds;records=[];indices=set();discarded=0
            while time.monotonic()<end:
                if self.overflow:raise ValueError('Survey BLE queue overflow')
                try:received,aid,raw=await asyncio.wait_for(self.queue.get(),min(.25,max(.001,end-time.monotonic())))
                except asyncio.TimeoutError:continue
                if aid!=initiator:continue
                try:record=ranging(raw,request=request,session=session)
                except ValueError:discarded+=1;continue
                if time.monotonic()-received>.5 or record['index'] in indices:discarded+=1;continue
                indices.add(record['index']);records.append({**record,'received_monotonic':received})
            return dict(initiator=initiator,responder=responder,request=request,session=session,records=records,discarded=discarded)
        finally:
            await self.restore()

    async def measure_tag(self,initiator,tag,seconds=5.):
        for aid,client in self.clients.items():
            if aid not in self.subscribed:
                await client.start_notify(TWR_UUID,self.callbacks[aid]);self.subscribed.add(aid)
        for aid in self.clients:await self.set_mode(aid,1,lease_ms=30000)
        while not self.queue.empty():self.queue.get_nowait()
        request=secrets.randbelow(0xfffffffe)+1;session=secrets.randbelow(0x7ffffffe)+1
        try:
            if self.tag_initiator_first:
                # Avoid leaving the coin-cell responder listening continuously
                # while the PC performs a slow ATT start on the Anchor.
                await self.set_mode(initiator,3,request=request,peer=tag.mac,session=session,lease_ms=30000)
                await tag.set_mode(2,request=request,peer=self.info[initiator]['mac'],session=session,lease_ms=30000)
                # Acquisition begins only after both acknowledgements. Discard
                # pre-responder timeouts already queued by the initiator.
                while not self.queue.empty():self.queue.get_nowait()
            else:
                await tag.set_mode(2,request=request,peer=self.info[initiator]['mac'],session=session,lease_ms=30000)
                await self.set_mode(initiator,3,request=request,peer=tag.mac,session=session,lease_ms=30000)
            end=time.monotonic()+seconds;records=[];seen=set()
            while time.monotonic()<end:
                if self.overflow:raise ValueError('Survey BLE queue overflow')
                try:received,aid,raw=await asyncio.wait_for(self.queue.get(),min(.25,max(.001,end-time.monotonic())))
                except asyncio.TimeoutError:continue
                if aid!=initiator:continue
                try:value=ranging(raw,request=request,session=session)
                except ValueError:continue
                if value['index'] in seen or time.monotonic()-received>.5:continue
                seen.add(value['index']);records.append(value)
            return dict(initiator=initiator,responder='Tag',request=request,session=session,records=records,
                        startup_order='anchor-first' if self.tag_initiator_first else 'tag-first')
        finally:
            try:await tag.set_mode(0,request=secrets.randbelow(0xfffffffe)+1)
            finally:await self.restore()
