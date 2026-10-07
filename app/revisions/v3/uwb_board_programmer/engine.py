"""Real RF timing pipeline; USB arrival time is only a freshness/timeout clock."""
from dataclasses import asdict
import math, time
from datetime import datetime,timezone
import numpy as np
from .models import TICK_S,C_M_S,utc
from .positioning import ClockFit,Solver
from .protocol import Counter

class Pipeline:
    def __init__(self,profile,record=lambda *a:None,fix=lambda *a:None,raw=lambda *a:None,compute=True,allow_history=False):
        profile.validate(require_aoa=compute);self.compute=compute;self.allow_history=allow_history;self.profile=profile;self.record=record;self.on_fix=fix;self.on_raw=raw
        self.anchors={a.id:a for a in profile.anchors};self.master=next(a for a in profile.anchors if a.role=='master')
        self.solver=Solver(profile);self.clocks={a.id:ClockFit() for a in profile.anchors if a.role=='slave'}
        self.counters={a.id:Counter() for a in profile.anchors};self.master_epoch=None;self.boots={};self.pending=[]
        self.last_rx={};self.last_blink={};self.latest_angles={};self.fix_count=0;self.rejected=0;self.reason='Waiting for SYNC'
        self.gate=math.ceil((max(np.linalg.norm(np.array(a.position)-b.position) for a in profile.anchors for b in profile.anchors)+6*profile.tdoa_sigma_m)/(C_M_S*TICK_S))+10
    def reset(self,anchor_id):
        self.pending.clear();self.counters[anchor_id]=Counter();self.solver.previous=None
        if anchor_id==self.master.id:
            self.master_epoch=None;self.clocks={i:ClockFit() for i in self.clocks}
        elif anchor_id in self.clocks:self.clocks[anchor_id]=ClockFit()
        self.reason='Clock reset — waiting for fresh SYNC';self.record('reset',{'anchor_id':anchor_id})
    def master_time(self,raw,bits):
        if self.master_epoch is None:value=raw
        else:
            m=1<<bits;value=raw+((self.master_epoch-raw+m//2)//m)*m
        if self.master_epoch is None or value>self.master_epoch:self.master_epoch=value
        return value
    def clock_status(self):return 'synced' if all(c.ready() for c in self.clocks.values()) else ('drifting' if any(c.samples for c in self.clocks.values()) else 'unknown')
    def expire(self):
        now=time.monotonic();old=len(self.pending)
        self.pending=[g for g in self.pending if now-g['born']<2]
        if old!=len(self.pending):self.reject('Missing matching BLINK from configured anchors')
    def reject(self,reason):
        self.rejected+=1;self.reason=reason;self.record('rejected',{'reason':reason,'time':utc()})
    def accept(self,o):
        self.record('observation',asdict(o));self.expire()
        if not self.allow_history and (datetime.now(timezone.utc)-datetime.fromisoformat(o.received_utc.replace('Z','+00:00'))).total_seconds()>2:self.reject('RF input older than 2 seconds');return
        if o.anchor_id not in self.anchors:self.reject('Unknown anchor');return
        if o.anchor_id in self.boots and self.boots[o.anchor_id]!=o.boot:self.reset(o.anchor_id)
        prior_rx=self.last_rx.get(o.anchor_id)
        if prior_rx is not None and time.monotonic()-prior_rx>7 and o.bits==40:self.reset(o.anchor_id)
        self.boots[o.anchor_id]=o.boot;self.last_rx[o.anchor_id]=time.monotonic()
        if o.status:self.reject('Radio status '+str(o.status));return
        if o.frame_type=='SYNC':
            if o.anchor_id==self.master.id or o.peer_mac!=self.master.mac.upper() or o.tx is None:return
            if o.tx_bits!=64:self.reject('Master SYNC must carry 64-bit TX timestamp');return
            local=self.counters[o.anchor_id].unwrap(o.rx,o.bits);master_tx=self.master_time(o.tx,o.tx_bits)
            distance=float(np.linalg.norm(np.array(self.anchors[o.anchor_id].position)-self.master.position))
            self.clocks[o.anchor_id].add(local,master_tx,distance)
            self.on_raw(o.raw_payload(self.profile));self.reason='SYNC '+self.clock_status();return
        if o.peer_mac!=self.profile.tag_mac.upper():return
        self.last_blink[o.anchor_id]=time.monotonic();self.latest_angles[o.anchor_id]=o
        self.on_raw(o.raw_payload(self.profile))
        if not self.compute:self.reason='Diagnostic: collecting RF angles; no position computed';return
        if self.clock_status()!='synced':self.reason='Waiting for at least 6 fresh SYNC samples at every slave';return
        if o.anchor_id==self.master.id:
            corrected=self.master_time(o.rx,o.bits)-round(self.master.rx_bias_m/(C_M_S*TICK_S))
        else:corrected=self.clocks[o.anchor_id].correct(self.counters[o.anchor_id].unwrap(o.rx,o.bits),self.anchors[o.anchor_id].rx_bias_m)
        matches=[g for g in self.pending if abs(g['ref']-corrected)<=self.gate]
        if len(matches)>1:
            self.pending=[g for g in self.pending if g not in matches];self.reject('Ambiguous BLINK association');return
        if matches:
            group=matches[0]
            if o.anchor_id in group['observations']:
                prior=group['observations'][o.anchor_id]
                if prior.rx==o.rx:return
                self.pending.remove(group);self.reject('Two BLINKs in one association gate');return
        else:
            group={'born':time.monotonic(),'ref':corrected,'observations':{},'times':{}};self.pending.append(group)
        group['observations'][o.anchor_id]=o;group['times'][o.anchor_id]=corrected
        if len(self.pending)>256:self.pending.pop(0);self.reject('Pending frame queue overflow')
        if len(group['observations'])!=len(self.anchors):return
        self.pending.remove(group)
        try:fix=self.solver.solve(group['observations'],group['times'],clock_sigmas_m={i:c.rms_s*C_M_S for i,c in self.clocks.items()})
        except ValueError as e:self.reject(str(e));return
        fix.update(time=max(x.received_utc for x in group['observations'].values()),tag_id=self.profile.tag_id,site_id=self.profile.site_id,floor_id=self.profile.floor_id,engine_id='UWBBoardProgrammer/2.0.0')
        fix['frame_numbers']={i:str(x.frame_number) for i,x in group['observations'].items()}
        self.fix_count+=1;self.reason='Valid 3D fix';self.record('fix',fix);self.on_fix(fix)
    def snapshot(self):
        return {'clock_status':self.clock_status(),'fixes':self.fix_count,'rejected':self.rejected,'reason':self.reason,
            'clocks':{i:{'samples':len(c.samples),'ready':c.ready(),'drift_ppm':(c.slope-1)*1e6,'rms_ns':c.rms_s*1e9 if math.isfinite(c.rms_s) else None} for i,c in self.clocks.items()}}
