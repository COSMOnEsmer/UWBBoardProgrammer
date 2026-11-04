"""USB-powered calibration Tag control. Normal coin-cell image is separate."""
import asyncio
import json
import queue
import re
import threading
import time


class UsbSurveyTag:
    def __init__(self,port,usb_serial,mac,version='1.4.2-pilot'):
        self.port=port;self.usb_serial=usb_serial;self.mac=mac.upper();self.version=version
        self.handle=None;self.thread=None;self.stopped=threading.Event();self.messages=queue.Queue(256)
        self.hello=None

    def open(self):
        import serial
        from .standalone_flashing import _identity
        _identity(self.port,self.usb_serial)
        self.handle=serial.Serial(port=None,baudrate=3000000,timeout=.1)
        self.handle.port=self.port;self.handle.rts=False;self.handle.dtr=False;self.handle.open()
        self.thread=threading.Thread(target=self._read,daemon=True,name='Survey-USB-Tag');self.thread.start()
        end=time.monotonic()+5
        try:
            while time.monotonic()<end:
                try:value=self.messages.get(timeout=.2)
                except queue.Empty:continue
                if value.get('kind')=='hello':
                    if value.get('model')!='Type2DK' or value.get('mac','').upper()!=self.mac:
                        raise ValueError('Selected USB port is not the configured Type2DK Tag')
                    if value.get('version')!=self.version:
                        raise ValueError('Flash the USB calibration Tag image before capturing references')
                    self.hello=value;return self
            raise ValueError('No awake USB calibration Tag. Set the Tag power switch to USB and check its firmware/port.')
        except BaseException:self.close();raise

    def _read(self):
        while not self.stopped.is_set():
            try:raw=self.handle.readline()
            except Exception:return
            text=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',raw).decode('utf-8',errors='replace')
            start=text.find('{"v":1,')
            if start<0:continue
            try:value=json.JSONDecoder().raw_decode(text[start:])[0]
            except ValueError:continue
            if value.get('kind') in ('hello','survey_status'):
                try:self.messages.put_nowait(value)
                except queue.Full:pass

    async def set_mode(self,mode,*,request,peer='0000000000000000',session=0,lease_ms=0):
        def send():
            from .survey_protocol import command
            command(mode,request,peer,session,lease_ms)  # Same validation as BLE.
            text=f'UBP CAL {request:x} {mode} {peer} {session:x} {lease_ms}\n'.encode('ascii')
            self.handle.write(b'\n');self.handle.flush();time.sleep(.02)
            # Pacing avoids overflowing the EVK console while the radio is busy.
            for value in text:
                self.handle.write(bytes([value]));self.handle.flush();time.sleep(.003)
            end=time.monotonic()+10
            while time.monotonic()<end:
                try:value=self.messages.get(timeout=.2)
                except queue.Empty:continue
                if value.get('kind')=='survey_status' and value.get('request')==request:
                    if value.get('status') or value.get('mode')!=mode or value.get('session')!=session:
                        raise ValueError('Tag rejected calibration command: '+str(value))
                    return value
            raise TimeoutError('Tag calibration acknowledgement missing; its radio lease will expire')
        return await asyncio.to_thread(send)

    def close(self):
        self.stopped.set()
        if self.thread:self.thread.join(timeout=1)
        if self.handle and self.handle.is_open:self.handle.close()
