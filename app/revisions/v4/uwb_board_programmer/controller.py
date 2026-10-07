import queue,threading,time
from .engine import Pipeline
from .recording import Recorder
from .serial_io import SerialReader
from .models import Observation,utc

class Controller:
    def __init__(self,root,profile,log,fix,diagnostic=False):
        self.profile=profile;self.log=log;self.fix=fix;self.diagnostic=diagnostic;self.queue=queue.Queue(2048);self.end=threading.Event()
        self.record=Recorder(root,profile);self.cloud=None;self.publish_raw=False;self.publish_position=False
        self.pipe=Pipeline(profile,record=self.record.write,fix=self.on_fix,raw=self.on_raw,compute=not diagnostic)
        self.readers={a.id:SerialReader(a,profile.baud,self.on_serial,log) for a in profile.anchors}
        self.hello={};self.states={};self.configured=set();self.starting=False;self.running=False;self.latest={};self.last_tag=0
        self.thread=threading.Thread(target=self.process,daemon=True,name='rf-engine');self.thread.start()
        for reader in self.readers.values():reader.start()
        self.log('Recording '+str(self.record.path))
    def on_serial(self,anchor,item):
        try:self.queue.put_nowait(('serial',anchor,item))
        except queue.Full:self.log('Input queue overflow; stopping to avoid stale frame association');self.command('stop')
    def command(self,command):self.queue.put((command,None,None),timeout=1)
    def on_fix(self,fix):
        self.fix(fix)
        if self.cloud and self.publish_position and not self.diagnostic:self.cloud.publish_fix(fix)
    def on_raw(self,raw):
        if self.cloud and self.publish_raw:self.cloud.publish_raw(raw)
    def start_radios(self):
        missing=[]
        for a in self.profile.anchors:
            hello=self.hello.get(a.id,{})
            if hello.get('model')!='Type2BP' or hello.get('role')!=a.role or hello.get('version')!='1.0.0':missing.append(a.id+' firmware/model/role not verified')
            if self.states.get(a.id) not in ('ready','stopped'):missing.append(a.id+' radio not ready (reset/reconnect if needed)')
        if missing:raise ValueError('; '.join(missing))
        self.running=False;self.starting=True;self.configured.clear();self.start_deadline=time.monotonic()+10
        for a in self.profile.anchors:self.readers[a.id].send(f'E2E CONFIG {a.mac.upper()} 500')
    def stop_radios(self):
        self.running=False;self.starting=False
        for reader in self.readers.values():
            if reader.connected:reader.send('E2E STOP')
        for a in self.profile.anchors:self.pipe.reset(a.id)
        self.log('STOP sent; check stopped acknowledgements for every anchor')
    def process(self):
        while not self.end.is_set():
            if self.starting and time.monotonic()>self.start_deadline:self.stop_radios();self.log('Start/config timeout')
            try:kind,aid,item=self.queue.get(timeout=.1)
            except queue.Empty:
                self.pipe.expire()
                if self.starting and time.monotonic()>self.start_deadline:self.stop_radios();self.log('Start/config timeout')
                continue
            try:
                if kind=='start':self.start_radios();continue
                if kind=='stop':self.stop_radios();continue
                if isinstance(item,Observation):
                    self.latest[aid]=item
                    if item.frame_type=='BLINK' and item.peer_mac==self.profile.tag_mac.upper():self.last_tag=time.monotonic()
                    if self.running:self.pipe.accept(item)
                    else:self.record.write('unprocessed_observation',item.__dict__)
                    continue
                self.record.write('board_message',{'anchor_id':aid,**item})
                a=next(a for a in self.profile.anchors if a.id==aid)
                if item['kind']=='hello':
                    previous=self.hello.get(aid)
                    if previous and previous.get('boot')!=item.get('boot') and self.running:self.stop_radios()
                    self.hello[aid]=item
                    if item.get('state') in ('ready','running','stopped'):self.states[aid]=item['state']
                    if not previous or previous.get('boot')!=item.get('boot'):self.pipe.reset(aid)
                    self.log(aid+' '+item['model']+' '+item['role']+' MAC '+item['mac'])
                    if self.starting and aid in self.configured and item.get('mac')!=a.mac.upper():self.stop_radios();raise ValueError('Anchor MAC not acknowledged')
                elif item['kind']=='status':
                    state=item.get('state');self.log(aid+' '+str(state)+' code '+str(item.get('code')))
                    if item.get('code')!=0:self.states[aid]=state;self.stop_radios();continue
                    if state=='configured_restart_required' and self.starting:
                        self.configured.add(aid)
                        if len(self.configured)==len(self.profile.anchors):
                            # CONFIG status precedes HELLO on the same UART. START uses the current persisted MAC.
                            for reader in self.readers.values():reader.send('E2E START')
                    elif state in ('ready','running','stopped'):
                        self.states[aid]=state
                        if self.starting and all(self.states.get(a.id)=='running' for a in self.profile.anchors):self.starting=False;self.running=True;self.log('All anchors running; wait for clock SYNC')
                    else:self.states[aid]=state
                elif item['kind']=='disconnected':
                    self.hello.pop(aid,None);self.states[aid]='disconnected';self.pipe.reset(aid)
                    if self.running or self.starting:self.stop_radios()
            except Exception as e:self.log('RF: '+str(e))
    def snapshot(self):
        return {**self.pipe.snapshot(),'running':self.running,'starting':self.starting,'states':dict(self.states),'hello':dict(self.hello),'diagnostic':self.diagnostic}
    def health(self):
        now=time.monotonic();devices=[]
        for a in self.profile.anchors:
            age=now-self.pipe.last_rx.get(a.id,0)
            status='online' if self.running and age<3 else ('warning' if self.readers[a.id].connected and self.running else 'offline')
            devices.append({'device_id':a.id,'device_type':'anchor','status':status})
        # Never auto-register an unseen tag by sending an invented presence report.
        if self.last_tag:devices.append({'device_id':self.profile.tag_id,'device_type':'tag','status':'online' if now-self.last_tag<max(3,3*self.profile.blink_interval_ms/1000) else 'lost'})
        return {'clock_status':self.pipe.clock_status(),'devices':devices}
    def close(self):
        self.command('stop');time.sleep(.4)
        for reader in self.readers.values():reader.close()
        self.end.set();self.thread.join(timeout=3);self.record.close()
