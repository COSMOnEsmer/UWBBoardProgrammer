"""Autonomous BLE acquisition behind the desktop's existing controller API."""
import asyncio
from dataclasses import asdict
import json
import queue
import sys
import threading
import time

from .ble_transport import Binding, Central, advertisement_identity
from .engine import Pipeline
from .models import utc
from .protocol import parse_line
from .recording import Recorder
from uwb_ble_wire import SERVICE_UUID


def run_ble(coroutine):
    initialized=False
    try:
        if sys.platform=='win32':
            import ctypes
            result=ctypes.windll.ole32.CoInitializeEx(None,0)
            if result not in (0,1):raise RuntimeError('BLE worker requires Windows MTA')
            initialized=True
        return asyncio.run(coroutine)
    finally:
        if initialized:
            import ctypes
            ctypes.windll.ole32.CoUninitialize()


async def discover(seconds=5, mode='passive'):
    from bleak import BleakScanner
    found={}
    def detected(device, advertisement):
        raw=advertisement.service_data.get(SERVICE_UUID)
        if raw is None:return
        try:mac,role=advertisement_identity(bytes(raw))
        except ValueError:return
        found[mac]=dict(mac=mac,role=role,address=device.address,
                        name=advertisement.local_name or device.name or 'UWB Anchor',
                        rssi=advertisement.rssi)
    async with BleakScanner(detected,scanning_mode=mode):
        await asyncio.sleep(seconds)
    return sorted(found.values(),key=lambda row:row['mac'])


class CaptureState:
    """Receive genuine measurements before the user has surveyed coordinates."""
    def __init__(self, profile, record):
        self.profile=profile;self.record=record;self.compute=False
        self.latest_angles={};self.last_blink={};self.last_rx={};self.clocks={}
    def reset(self,aid):
        self.latest_angles.pop(aid,None);self.last_blink.pop(aid,None)
        self.record('reset',dict(anchor_id=aid))
    def accept(self,o):
        self.record('observation',asdict(o));self.last_rx[o.anchor_id]=time.monotonic()
        if o.frame_type=='BLINK' and o.peer_mac==self.profile.tag_mac.upper():
            self.last_blink[o.anchor_id]=time.monotonic();self.latest_angles[o.anchor_id]=o
    def expire(self):pass
    def clock_status(self):return 'unknown'
    def snapshot(self):
        return dict(clock_status='unknown',fixes=0,rejected=0,clocks={},
                    reason='Capture only. Enter surveyed coordinates to calculate positions.')


class BleController:
    def __init__(self,root,profile,log,fix,diagnostic=False,*,autostart_threads=True):
        self.profile=profile;self.log=log;self.fix=fix;self.diagnostic=diagnostic
        self.cloud=None;self.publish_raw=False;self.publish_position=False
        self.running=bool(diagnostic);self.starting=False;self.latest={};self.last_tag=0
        self.hello={};self.states={a.id:'disconnected' for a in profile.anchors}
        self.connected=set();self.rx_counts={};self.dropped={}
        self.queue=queue.Queue(1024);self.stop_requested=threading.Event()
        self.receiver_ended=threading.Event();self.overflow=threading.Event()
        self.loop=None;self.central=None;self.receiver_thread=None;self.thread=None
        identities=[Binding(a.id,a.mac,a.role) for a in profile.anchors]
        if len({b.mac.upper() for b in identities})!=len(identities) or len({b.anchor_id for b in identities})!=len(identities):
            raise ValueError('Anchor IDs and MAC addresses must be unique.')
        geometry_ready=True
        try:profile.validate(require_ports=False,require_aoa=not diagnostic)
        except ValueError:
            if not diagnostic:raise
            geometry_ready=False
        self.record=Recorder(root,profile)
        self.pipe=(Pipeline(profile,record=self.record.write,fix=self.on_fix,
                            raw=self.on_raw,compute=False) if geometry_ready
                   else CaptureState(profile,self.record.write))
        self.record.write('transport',dict(name='BLE/GATT',scan_mode=profile.ble_scan_mode,
                                          autonomous=True,radio_control_writes=0))
        self.log('Recording '+str(self.record.path))
        if autostart_threads:
            self.thread=threading.Thread(target=self.process,daemon=True,name='BLE-positioning')
            self.receiver_thread=threading.Thread(target=self.receive,daemon=True,name='BLE-WinRT-MTA')
            self.thread.start();self.receiver_thread.start()

    def emit(self,aid,kind,data):
        try:self.queue.put_nowait((time.monotonic(),aid,kind,data))
        except queue.Full:self.overflow.set()

    def receive(self):
        async def receive_all():
            self.loop=asyncio.get_running_loop()
            self.central=Central([Binding(a.id,a.mac,a.role) for a in self.profile.anchors],
                                 self.emit,scan_mode=self.profile.ble_scan_mode)
            if self.stop_requested.is_set():self.central.stop.set()
            await self.central.run()
        try:run_ble(receive_all())
        except Exception as error:self.log('BLE: '+str(error))
        finally:self.loop=None;self.receiver_ended.set()

    def on_fix(self,value):
        value={**value,'engine_id':'UWBBoardProgrammer/2.1.0-StandaloneBLE'}
        self.fix(value)
        if self.cloud and self.publish_position and self.running and not self.diagnostic:
            self.cloud.publish_fix(value)

    def on_raw(self,value):
        if self.cloud and self.publish_raw:self.cloud.publish_raw(value)

    def command(self,command):
        if command not in ('start','stop'):raise ValueError('Unknown processing command')
        self.queue.put((time.monotonic(),'__processing__',command,{}),timeout=1)

    def handle_event(self,aid,kind,data):
        if aid=='__processing__':
            if kind=='start' and isinstance(self.pipe,CaptureState):
                raise ValueError('Close BLE capture and enter surveyed coordinates before positioning.')
            self.running=kind=='start'
            self.pipe.compute=self.running and not self.diagnostic
            for anchor in self.profile.anchors:self.pipe.reset(anchor.id)
            self.record.write('processing',dict(enabled=self.running,radio_commands_sent=0))
            self.log('Position processing started; waiting for fresh SYNC.' if self.running
                     else 'Position processing paused. Autonomous UWB remains active.')
            return
        self.record.write('ble_'+kind,dict(anchor_id=aid,**data))
        if kind=='connected':
            self.connected.add(aid);self.states[aid]='connected';self.hello[aid]=data
            self.log(aid+' BLE connected / '+data.get('firmware','')+' / '+data.get('radio_state',''))
        elif kind=='disconnected':
            self.connected.discard(aid);self.states[aid]='disconnected';self.hello.pop(aid,None)
        elif kind=='reset':self.pipe.reset(aid)
        elif kind=='error':self.states[aid]='error';self.log(aid+' BLE: '+data.get('message',''))
        elif kind=='observation' and aid in self.connected:
            o=parse_line(json.dumps(data),aid)
            self.latest[aid]=o;self.rx_counts[aid]=self.rx_counts.get(aid,0)+1
            self.dropped[aid]=data.get('dropped',0)
            if o.frame_type=='BLINK' and o.peer_mac==self.profile.tag_mac.upper():self.last_tag=time.monotonic()
            self.pipe.accept(o)

    def process(self):
        try:
            while not self.receiver_ended.is_set() or not self.queue.empty():
                if self.overflow.is_set():
                    self.overflow.clear()
                    while not self.queue.empty():
                        try:self.queue.get_nowait()
                        except queue.Empty:break
                    for anchor in self.profile.anchors:self.pipe.reset(anchor.id)
                    self.log('BLE processing queue overflow; clocks reset.')
                try:
                    received,aid,kind,data=self.queue.get(timeout=.1)
                    if kind=='observation' and time.monotonic()-received>.5:
                        kind='reset';data={'reason':'stale_processing_queue'}
                    self.handle_event(aid,kind,data)
                except queue.Empty:pass
                except Exception as error:self.log('BLE processing: '+str(error))
                self.pipe.expire()
        finally:
            self.record.write('closed',dict(radio_stop_commands_sent=0));self.record.close()

    def snapshot(self):
        return {**self.pipe.snapshot(),'running':self.running,'starting':False,
                'diagnostic':self.diagnostic,'states':dict(self.states),'hello':dict(self.hello),
                'connected':sorted(self.connected),'rx_counts':dict(self.rx_counts),
                'rf_total':sum(self.rx_counts.values()),'dropped':dict(self.dropped),
                'tag_age_s':round(time.monotonic()-self.last_tag,1) if self.last_tag else None}

    def health(self):
        now=time.monotonic()
        devices=[dict(device_id=a.id,device_type='anchor',status=(
            'online' if a.id in self.connected and now-self.pipe.last_rx.get(a.id,0)<3
            else 'warning' if a.id in self.connected else 'offline')) for a in self.profile.anchors]
        if self.last_tag:
            devices.append(dict(device_id=self.profile.tag_id,device_type='tag',
                                status='online' if now-self.last_tag<3 else 'lost'))
        return dict(clock_status=self.pipe.clock_status(),devices=devices)

    def close(self):
        self.stop_requested.set()
        if self.loop and self.central:
            try:self.loop.call_soon_threadsafe(self.central.stop.set)
            except RuntimeError:pass
        if self.receiver_thread:self.receiver_thread.join(timeout=12)
        if self.thread:self.thread.join(timeout=2)
        if any(t and t.is_alive() for t in (self.receiver_thread,self.thread)):
            raise RuntimeError('BLE cleanup is still running. Wait, then disconnect again.')
        if self.thread is None:self.record.close()
