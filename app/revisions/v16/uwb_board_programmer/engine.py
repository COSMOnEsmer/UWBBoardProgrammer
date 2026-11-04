"""Real RF timing pipeline; USB arrival time is only a freshness/timeout clock."""
from dataclasses import asdict
import math, time
from datetime import datetime,timezone
import numpy as np
from .models import TICK_S,C_M_S,utc
from .positioning import ClockFit,Solver
from .protocol import Counter
from .continuity import ContinuousDisplay
from .clock_recovery import InterpolatedClockFit,AwaitingSync

class Pipeline:
    def __init__(self,profile,record=lambda *a:None,fix=lambda *a:None,raw=lambda *a:None,compute=True,allow_history=False):
        profile.validate(require_aoa=compute);self.compute=compute;self.allow_history=allow_history;self.profile=profile;self.record=record;self.on_fix=fix;self.on_raw=raw
        self.anchors={a.id:a for a in profile.anchors};self.master=next(a for a in profile.anchors if a.role=='master')
        self.interpolated=profile.transport=='ble'
        self.clock_factory=InterpolatedClockFit if self.interpolated else ClockFit
        self.continuity=ContinuousDisplay(profile);self.continuous_display=True;self.solver=Solver(profile);self.clocks={a.id:self.clock_factory() for a in profile.anchors if a.role=='slave'}
        self.deferred=[];self.transport_gaps={}
        self.counters={a.id:Counter() for a in profile.anchors};self.master_epoch=None;self.boots={};self.pending=[]
        self.last_rx={};self.last_blink={};self.latest_angles={};self.fix_count=0;self.rejected=0;self.reason='Waiting for SYNC'
        self.rejection_counts={};self.last_rejection=None;self.last_solver_rejection=None;self.solver_attempts=0;self.preview=None
        self.gate=math.ceil((max(np.linalg.norm(np.array(a.position)-b.position) for a in profile.anchors for b in profile.anchors)+6*profile.tdoa_sigma_m)/(C_M_S*TICK_S))+10
    def reset(self,anchor_id):
        self.continuity.reset(anchor_id)
        self.preview=None;self.pending.clear();self.deferred.clear();self.counters[anchor_id]=Counter();self.solver.previous=None
        if anchor_id==self.master.id:
            self.master_epoch=None;self.clocks={i:self.clock_factory() for i in self.clocks}
        elif anchor_id in self.clocks:self.clocks[anchor_id]=self.clock_factory()
        self.reason='Clock reset — waiting for fresh SYNC';self.record('reset',{'anchor_id':anchor_id})
    def transport_gap(self,anchor_id,reason):
        # Lost BLE reports do not reset a still-running hardware clock. CRC,
        # exact sequence/boot checks, RF freshness and bracket bounds still apply.
        key=anchor_id+':'+reason;self.transport_gaps[key]=self.transport_gaps.get(key,0)+1
        self.record('transport_gap',dict(anchor_id=anchor_id,reason=reason,clock_epoch_retained=True))
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
        old=len(self.deferred);self.deferred=[item for item in self.deferred if now-item[0]<2]
        if old!=len(self.deferred):self.reject('BLINK expired while waiting for a valid RF SYNC bracket')
    def reject(self,reason,details=None):
        self.rejected+=1;self.reason=reason
        self.rejection_counts[reason]=self.rejection_counts.get(reason,0)+1
        self.last_rejection={'reason':reason,'time':utc(),'details':details or {}}
        self.record('rejected',self.last_rejection)
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
            self.continuity.sync(o.anchor_id,local,master_tx,distance)
            self.clocks[o.anchor_id].add(local,master_tx,distance)
            self.on_raw(o.raw_payload(self.profile));self.reason='SYNC '+self.clock_status()
            if self.compute:self.flush_deferred()
            return
        if o.peer_mac!=self.profile.tag_mac.upper():return
        self.last_blink[o.anchor_id]=time.monotonic();self.latest_angles[o.anchor_id]=o
        self.on_raw(o.raw_payload(self.profile))
        if not self.compute:self.reason='Diagnostic: collecting RF angles; no position computed';return
        if self.interpolated and not self.profile.survey_verified:
            self.reason='Clock diagnostics only: measured anchor coordinates are not confirmed';return
        if self.continuous_display and self.profile.mode=='tdoa_4':
            local=self.master_time(o.rx,o.bits)-round(self.master.rx_bias_m/(C_M_S*TICK_S)) if o.anchor_id==self.master.id else self.counters[o.anchor_id].unwrap(o.rx,o.bits)-round(self.anchors[o.anchor_id].rx_bias_m/(C_M_S*TICK_S))
            self.continuity.blink(o,local)
        if self.clock_status()!='synced':self.reason='Waiting for at least 6 fresh SYNC samples at every slave';return
        self.process_blink(o)
    def flush_deferred(self):
        waiting=self.deferred;self.deferred=[]
        for born,o in waiting:
            if time.monotonic()-born<2:self.process_blink(o,born)
    def process_blink(self,o,born=None):
        if self.interpolated and not self.profile.survey_verified:return
        if born is None:born=time.monotonic()
        if o.anchor_id==self.master.id:
            corrected=self.master_time(o.rx,o.bits)-round(self.master.rx_bias_m/(C_M_S*TICK_S))
        else:
            try:corrected=self.clocks[o.anchor_id].correct(self.counters[o.anchor_id].unwrap(o.rx,o.bits),self.anchors[o.anchor_id].rx_bias_m)
            except AwaitingSync:
                if len(self.deferred)>=256:self.deferred.pop(0);self.reject('Deferred RF queue overflow')
                self.deferred.append((born,o));self.reason='Waiting for a later RF SYNC to bracket BLINK';return
            except ValueError as error:self.reject(str(error));return
        if self.clock_status()!='synced':return
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
            group={'born':born,'ref':corrected,'observations':{},'times':{}};self.pending.append(group)
        group['observations'][o.anchor_id]=o;group['times'][o.anchor_id]=corrected
        if len(self.pending)>256:self.pending.pop(0);self.reject('Pending frame queue overflow')
        if len(group['observations'])!=len(self.anchors):return
        self.pending.remove(group)
        self.solver_attempts+=1
        try:fix=self.solver.solve(group['observations'],group['times'],clock_sigmas_m={i:c.rms_s*C_M_S for i,c in self.clocks.items()})
        except ValueError as e:
            candidate=self.solver.last_diagnostic.get('candidate')
            self.preview={**candidate,'warning':str(e),'accepted':False,'born':time.monotonic()} if candidate else None
            self.reject(str(e),dict(self.solver.last_diagnostic));self.last_solver_rejection=self.last_rejection
            return
        fix.update(time=max(x.received_utc for x in group['observations'].values()),tag_id=self.profile.tag_id,site_id=self.profile.site_id,floor_id=self.profile.floor_id,engine_id='UWBBoardProgrammer/2.8.0')
        fix['frame_numbers']={i:str(x.frame_number) for i,x in group['observations'].items()}
        self.preview={**fix,'accepted':True,'born':time.monotonic()}
        self.fix_count+=1;self.reason='Valid 3D fix';self.last_solver_rejection=None;self.record('fix',fix);self.on_fix(fix)
    def snapshot(self):
        strict=self.preview if self.preview and time.monotonic()-self.preview['born']<3 else None
        loose=self.continuity.latest if self.continuous_display else None
        if loose and time.monotonic()-loose['born']>=3:loose=None
        display=strict if strict and strict.get('accepted') else loose or strict
        return {'preview':display,'continuous_estimates':self.continuity.count,'clock_status':self.clock_status(),'fixes':self.fix_count,'rejected':self.rejected,'reason':self.reason,
            'solver_attempts':self.solver_attempts,'rejection_counts':dict(self.rejection_counts),
            'last_rejection':self.last_rejection,'last_solver_rejection':self.last_solver_rejection,
            'clock_method':'bounded RF interpolation' if self.interpolated else 'linear regression',
            'deferred_blinks':len(self.deferred),'transport_gaps':dict(self.transport_gaps),
            'clocks':{i:{'samples':len(c.samples),'ready':c.ready(),'drift_ppm':(c.slope-1)*1e6,'rms_ns':c.rms_s*1e9 if math.isfinite(c.rms_s) else None,
                         'not_ready_reason':c.not_ready_reason() if hasattr(c,'not_ready_reason') else ('' if c.ready() else 'Clock synchronization not ready/fresh')} for i,c in self.clocks.items()}}
