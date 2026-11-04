import json,queue,threading,time
import serial
from serial.tools import list_ports
from .protocol import parse_line
from .models import Observation

def ports():return [{'port':p.device,'description':p.description,'serial_number':p.serial_number,'vid':p.vid,'pid':p.pid} for p in list_ports.comports()]

def open_port(port,baud,timeout=.1):
    handle=serial.Serial(port=None,baudrate=baud,timeout=timeout,write_timeout=1,rtscts=False,dsrdtr=False)
    handle.port=port;handle.dtr=False;handle.rts=False
    handle.open();return handle

class SerialReader:
    def __init__(self,anchor,baud,on_line,on_log):
        self.anchor=anchor;self.baud=baud;self.on_line=on_line;self.log=on_log;self.stop_event=threading.Event();self.out=queue.Queue(32)
        self.handle=None;self.thread=threading.Thread(target=self.run,daemon=True,name='serial-'+anchor.id);self.connected=False
    def start(self):self.thread.start()
    def send(self,command):
        if '\n' in command or '\r' in command:raise ValueError('One command per call')
        self.out.put_nowait((command+'\n').encode('ascii'))
    def close(self):
        self.stop_event.set()
        if self.handle:
            try:self.handle.cancel_read()
            except (AttributeError,OSError):pass
        self.thread.join(timeout=2)
    def run(self):
        while not self.stop_event.is_set():
            try:
                with open_port(self.anchor.port,self.baud) as h:
                    self.handle=h;h.dtr=False;h.rts=False;self.connected=True;self.log(self.anchor.id+' connected '+self.anchor.port)
                    h.write(b'E2E HELLO\n');buffer=bytearray()
                    while not self.stop_event.is_set():
                        try:h.write(self.out.get_nowait())
                        except queue.Empty:pass
                        data=h.read(h.in_waiting or 1)
                        if not data:continue
                        buffer.extend(data)
                        if len(buffer)>16384:buffer.clear();self.log(self.anchor.id+' oversized serial line rejected');continue
                        while b'\n' in buffer:
                            line,_,rest=buffer.partition(b'\n');buffer=bytearray(rest)
                            try:parsed=parse_line(line,self.anchor.id)
                            except (ValueError,KeyError,TypeError) as e:self.log(self.anchor.id+' parse: '+str(e));continue
                            if parsed is not None:self.on_line(self.anchor.id,parsed)
                            elif line.strip():self.log(self.anchor.id+' '+line.decode(errors='replace')[:240])
            except (serial.SerialException,OSError) as e:
                self.connected=False;self.on_line(self.anchor.id,{'kind':'disconnected','reason':str(e)});self.log(self.anchor.id+' '+str(e))
                self.stop_event.wait(2)
            finally:self.handle=None;self.connected=False

def exchange(port,baud,command,predicate,timeout=8):
    with open_port(port,baud) as h:
        h.dtr=False;h.rts=False;h.write((command+'\n').encode('ascii'));deadline=time.monotonic()+timeout;buffer=bytearray()
        while time.monotonic()<deadline:
            buffer.extend(h.read(h.in_waiting or 1))
            if len(buffer)>16384:buffer.clear()
            while b'\n' in buffer:
                line,_,rest=buffer.partition(b'\n');buffer=bytearray(rest)
                try:d=parse_line(line,'setup')
                except (ValueError,KeyError,TypeError):continue
                if isinstance(d,dict) and predicate(d):return d
        raise TimeoutError('Board did not acknowledge '+command.split()[1])

def configure_tag(port,baud,mac,interval):
    hello=exchange(port,baud,'E2E HELLO',lambda d:d.get('kind')=='hello')
    if hello.get('model')!='Type2DK' or hello.get('role')!='tag':raise ValueError('Expected Type2DK setup firmware')
    result=exchange(port,baud,f'E2E CONFIG {mac.upper()} {interval}',lambda d:d.get('kind')=='status' and d.get('state') in ('configured_restart_required','config_save_failed','invalid_config','invalid_mac'))
    if result.get('code')!=0:raise ValueError('Tag configuration failed '+str(result))
    hello=exchange(port,baud,'E2E HELLO',lambda d:d.get('kind')=='hello')
    if hello.get('mac')!=mac.upper() or hello.get('interval_ms')!=interval:raise ValueError('Tag persistent configuration not confirmed')
    return hello
