import queue,threading,time
import numpy as np
import requests,socketio
from .models import utc
BASE='https://api-uwb.mangosgo.com'

def pull_config(token,base=BASE):
    if not token.strip():raise ValueError('Enter gateway bearer token (dashboard password is not a gateway token)')
    response=requests.get(base+'/api/v1/edge/config',headers={'Authorization':'Bearer '+token.strip()},timeout=(5,15))
    if response.status_code==401:raise ValueError('Gateway token invalid/revoked')
    response.raise_for_status();body=response.json()
    if not body.get('ok') or not isinstance(body.get('data'),dict):raise ValueError('Invalid edge/config response')
    return body['data']

def validate_scope(profile,config):
    if config.get('site',{}).get('id')!=profile.site_id:raise ValueError('Gateway belongs to another site')
    if profile.floor_id not in {f['id'] for f in config.get('floors',[])}:raise ValueError('Gateway floor scope does not match profile')
    anchors={a['id']:a for a in config.get('anchors',[])}
    for a in profile.anchors:
        remote=anchors.get(a.id)
        if not remote:raise ValueError('Provision anchor '+a.id+' on RTLS first')
        if remote.get('floorId')!=profile.floor_id:raise ValueError(a.id+' floor mismatch')
        if remote.get('role')!=a.role:raise ValueError(a.id+' role mismatch')
        xyz=[remote.get('posXM'),remote.get('posYM'),remote.get('posZM')]
        if a.position is None or any(x is None for x in xyz) or not np.allclose(xyz,a.position,rtol=0,atol=.01):raise ValueError(a.id+' surveyed position differs from RTLS (>1 cm)')
    return True

def position_payload(fix,gateway_id):
    keys=['site_id','floor_id','tag_id','x_m','y_m','z_m','accuracy_m','num_anchors_used','residual','time']
    return {**{k:fix[k] for k in keys},'engine_id':gateway_id}

class CloudClient:
    def __init__(self,profile,token,gateway_id,log,health,base=BASE):
        if not gateway_id.strip():raise ValueError('Gateway ID is required')
        self.profile=profile;self.token=token.strip();self.gateway_id=gateway_id.strip();self.log=log;self.health=health;self.base=base
        self.queue=queue.Queue(256);self.stop_event=threading.Event();self.refresh=threading.Event();self.connected=False;self.ready=False;self.ack_ok=0;self.ack_error=0;self.dropped=0
        self.started=time.monotonic();self.sio=None;self.thread=threading.Thread(target=self.run,daemon=True,name='rtls-cloud')
    def start(self):self.thread.start()
    def enqueue(self,event,payload):
        # No backfill: record locally, discard while disconnected or outside the freshness budget.
        if not self.connected or not self.ready:self.dropped+=1;return
        try:self.queue.put_nowait((time.monotonic(),event,payload))
        except queue.Full:self.dropped+=1
    def publish_fix(self,fix):self.enqueue('edge:position',position_payload(fix,self.gateway_id))
    def publish_raw(self,payload):self.enqueue('edge:rawMeasurement',payload)
    def ack(self,event,payload):
        result=self.sio.call(event,payload,namespace='/edge',timeout=5)
        if not isinstance(result,dict) or result.get('ok') is not True:
            self.ack_error+=1;self.log(event+' rejected: '+str(result));return False
        self.ack_ok+=1;return True
    def close(self):
        self.stop_event.set()
        if self.sio:
            try:self.sio.disconnect()
            except Exception:pass
        self.thread.join(timeout=3)
    def run(self):
        backoff=2
        while not self.stop_event.is_set():
            try:
                cfg=pull_config(self.token,self.base);validate_scope(self.profile,cfg);self.config=cfg;self.ready=True
                self.sio=socketio.Client(reconnection=False,request_timeout=10,logger=False,engineio_logger=False)
                self.sio.on('edge:configChanged',lambda *_:self.refresh.set(),namespace='/edge')
                self.sio.on('edge:error',lambda data:self.log('RTLS edge error '+str(data)),namespace='/edge')
                self.sio.on('disconnect',lambda *_:setattr(self,'connected',False),namespace='/edge')
                self.sio.connect(self.base,auth={'token':self.token},namespaces=['/edge'],wait_timeout=15)
                self.connected=True;backoff=2;self.log('RTLS connected; config '+str(cfg.get('configVersion')))
                heartbeat=0;status_at=0;config_at=time.monotonic()
                while not self.stop_event.is_set() and self.connected:
                    now=time.monotonic()
                    if self.refresh.is_set() or now-config_at>300:
                        self.ready=False;cfg=pull_config(self.token,self.base);validate_scope(self.profile,cfg);self.config=cfg;self.ready=True;self.refresh.clear();config_at=now
                    state=self.health()
                    if now-heartbeat>=20:
                        accepted=self.ack('edge:heartbeat',{'gateway_id':self.gateway_id,'site_id':self.profile.site_id,'timestamp':utc(),'clock_status':state.get('clock_status','unknown'),'uptime_seconds':int(now-self.started),'software_version':'UWBBoardProgrammer/2.0.0'})
                        if heartbeat==0 and not accepted:raise ValueError('Initial heartbeat rejected: check gateway ID/token')
                        heartbeat=now
                    if now-status_at>=30:
                        for row in state.get('devices',[]):
                            self.ack('edge:deviceStatus',{'site_id':self.profile.site_id,'floor_id':self.profile.floor_id,'timestamp':utc(),**row})
                        status_at=now
                    try:born,event,payload=self.queue.get(timeout=.1)
                    except queue.Empty:continue
                    if now-born>2:self.dropped+=1;continue
                    self.ack(event,payload)
            except Exception as e:
                # Never include the token, request headers, or dashboard password in logs.
                message=str(e).replace(self.token,'[redacted]');self.log('RTLS: '+message)
            finally:
                self.connected=False;self.ready=False
                if self.sio:
                    try:self.sio.disconnect()
                    except Exception:pass
                while True:
                    try:self.queue.get_nowait();self.dropped+=1
                    except queue.Empty:break
            self.stop_event.wait(backoff);backoff=min(60,backoff*2)
