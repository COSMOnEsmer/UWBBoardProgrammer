"""Display-only estimates. These never call the accepted-fix/cloud callback."""
from collections import deque
from itertools import product
import math,time
import numpy as np
from scipy.optimize import least_squares
from .models import TICK_S,C_M_S

class PreviewClock:
    def __init__(self):self.samples=deque(maxlen=16);self.last=0
    def add(self,rx,tx,flight):
        if self.samples and (rx<=self.samples[-1][0] or tx<=self.samples[-1][1]):return
        if self.samples and (rx-self.samples[-1][0])*TICK_S>5:self.samples.clear()
        self.samples.append((rx,tx,flight/(C_M_S*TICK_S)));self.last=time.monotonic()
    def correct(self,rx):
        if len(self.samples)<2 or time.monotonic()-self.last>2:raise ValueError('Preview needs two recent RF SYNC samples')
        pairs=list(zip(self.samples,list(self.samples)[1:]))
        left,right=next(((a,b) for a,b in pairs if a[0]<=rx<=b[0]),pairs[-1])
        if rx<left[0] or (rx-right[0])*TICK_S>1:raise ValueError('Preview clock extrapolation exceeds one second')
        span=right[0]-left[0];slope=(right[1]-left[1])/span
        if span*TICK_S>5 or abs(slope-1)>200e-6:raise ValueError('Preview RF clock invalid')
        return left[1]+round((rx-left[0])*slope+left[2])

class ContinuousDisplay:
    def __init__(self,profile):
        self.profile=profile;self.master=next(a for a in profile.anchors if a.role=='master')
        self.clocks={a.id:PreviewClock() for a in profile.anchors if a.role=='slave'}
        self.groups={};self.previous=None;self.latest=None;self.count=0
    def reset(self,aid):
        self.groups.clear();self.latest=None;self.previous=None
        if aid==self.master.id:self.clocks={key:PreviewClock() for key in self.clocks}
        elif aid in self.clocks:self.clocks[aid]=PreviewClock()
    def sync(self,aid,rx,tx,flight):self.clocks[aid].add(rx,tx,flight)
    def blink(self,o,local):
        now=time.monotonic();self.groups={k:g for k,g in self.groups.items() if now-g['born']<1.5}
        group=self.groups.setdefault(o.frame_number,dict(born=now,observations={},times={}))
        try:corrected=local if o.anchor_id==self.master.id else self.clocks[o.anchor_id].correct(local)
        except ValueError:return
        group['observations'][o.anchor_id]=o;group['times'][o.anchor_id]=corrected
        if len(group['times'])!=len(self.profile.anchors):return
        del self.groups[o.frame_number]
        anchors=self.profile.anchors;ids=[a.id for a in anchors if a.id!=self.master.id]
        positions={a.id:np.asarray(a.position,float) for a in anchors}
        delta=np.array([(group['times'][aid]-group['times'][self.master.id])*TICK_S*C_M_S for aid in ids])
        if not np.all(np.isfinite(delta)):return
        max_baseline=max(np.linalg.norm(positions[aid]-positions[self.master.id]) for aid in ids)
        if np.max(np.abs(delta))>max(5,3*max_baseline):return
        lo,hi=np.asarray(self.profile.bounds,float)
        def residual(x):
            reference=np.linalg.norm(x-positions[self.master.id])
            return np.array([np.linalg.norm(x-positions[aid])-reference for aid in ids])-delta
        starts=[(lo+hi)/2]+[lo+(hi-lo)*np.array(f) for f in product((.2,.8),repeat=3)]
        if self.previous is not None:starts.insert(0,self.previous)
        fits=[least_squares(residual,np.clip(start,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=60) for start in starts]
        fits=[fit for fit in fits if fit.success and np.all(np.isfinite(fit.x))]
        if not fits:return
        costs=[float(np.dot(residual(fit.x),residual(fit.x))) for fit in fits];best=min(costs)
        contenders=[fit for fit,cost in zip(fits,costs) if cost<=best+1e-4]
        fit=min(contenders,key=lambda f:np.linalg.norm(f.x-self.previous)) if self.previous is not None else contenders[0]
        self.previous=fit.x.copy();self.count+=1
        self.latest=dict(x_m=float(fit.x[0]),y_m=float(fit.x[1]),z_m=float(fit.x[2]),born=now,
                         time=max(v.received_utc for v in group['observations'].values()),accepted=False,
                         warning='Continuous estimate: approximate RF clock / 3D accuracy unverified',
                         display_only=True,residual_m=math.sqrt(best/len(ids)))
