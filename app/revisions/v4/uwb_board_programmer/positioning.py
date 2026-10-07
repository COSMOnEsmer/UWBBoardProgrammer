from collections import deque
import math, time
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from .models import TICK_S,C_M_S

class ClockFit:
    def __init__(self): self.samples=deque(maxlen=40); self.last=0; self.rms_s=float('inf'); self.slope=1.; self.x0=0; self.y0=0; self.offset=0.
    def add(self, rx, master_tx, flight_m, rx_bias_m=0):
        self.samples.append((rx,master_tx,flight_m/(C_M_S*TICK_S)))
        self.last=time.monotonic()
        if len(self.samples)<6: return
        self.x0=self.samples[0][0]; self.y0=self.samples[0][1]
        x=np.array([s[0]-self.x0 for s in self.samples],float)
        y=np.array([s[1]-self.y0+s[2] for s in self.samples],float)
        xc=x-x.mean(); yc=y-y.mean()
        if np.ptp(x)*TICK_S<1: return
        slope=np.dot(xc,yc)/np.dot(xc,xc); offset=y.mean()-slope*x.mean()
        residual=y-(slope*x+offset)
        self.rms_s=float(np.sqrt(np.mean(residual**2))*TICK_S)
        self.slope=float(slope); self.offset=float(offset)
    def ready(self): return len(self.samples)>=6 and time.monotonic()-self.last<2.5 and self.rms_s<2e-9 and abs(self.slope-1)<200e-6
    def correct(self, rx, bias_m=0):
        if not self.ready(): raise ValueError('Clock synchronization not ready/fresh')
        return self.y0+round(self.slope*(rx-self.x0)+self.offset-bias_m/(C_M_S*TICK_S))

def bearing(az,el):
    a,e=np.radians([az,el]); return np.array([math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e)])
def wrap(angle): return (angle+180)%360-180

class Solver:
    def __init__(self,profile): self.profile=profile; self.previous=None
    def solve(self, observations, corrected,clock_sigmas_m=None):
        p=self.profile; p.validate()
        anchors={a.id:a for a in p.anchors}; master=next(a for a in p.anchors if a.role=='master')
        if set(observations)!=set(anchors): raise ValueError('Need matching BLINK from every configured anchor')
        if any(o.status for o in observations.values()): raise ValueError('Radio measurement status is not OK')
        ids=[a.id for a in p.anchors if a.id!=master.id]
        positions={a.id:np.asarray(a.position,float) for a in p.anchors}
        dr={i:(corrected[i]-corrected[master.id])*TICK_S*C_M_S for i in ids}
        for i in ids:
            if abs(dr[i])>np.linalg.norm(positions[i]-positions[master.id])+3*p.tdoa_sigma_m: raise ValueError('TDoA violates physical anchor baseline')
        sigmas={i:math.hypot(p.tdoa_sigma_m*(4 if observations[i].nlos or observations[master.id].nlos else 1),(clock_sigmas_m or {}).get(i,0)) for i in ids}
        # TDoA-only mode deliberately ignores angles, including verified ones.
        angles=[] if p.mode=='tdoa_4' else [i for i,o in observations.items() if anchors[i].aoa_verified and o.az is not None and o.el is not None and min(o.az_fom,o.el_fom)>=p.min_fom]
        if p.mode=='hybrid_3' and not angles: raise ValueError('No valid calibrated 3D AoA')
        lo,hi=np.asarray(p.bounds,float)
        def residual(x):
            distance={i:np.linalg.norm(x-positions[i]) for i in positions}
            out=[(distance[i]-distance[master.id]-dr[i])/sigmas[i] for i in ids]
            for i in angles:
                o=observations[i]; local=anchors[i].rotation().T@(x-positions[i]); norm=np.linalg.norm(local)
                if norm<0.02: out.extend([100,100]); continue
                az=math.degrees(math.atan2(local[1],local[0])); el=math.degrees(math.atan2(local[2],np.hypot(local[0],local[1])))
                sigma=p.aoa_sigma_deg*(4 if o.nlos else 1)*max(1,80/max(1,min(o.az_fom,o.el_fom)))
                out.extend([wrap(az-o.az)/sigma,(el-o.el)/sigma])
            return np.asarray(out)
        starts=[(lo+hi)/2,np.mean(list(positions.values()),axis=0)]
        if self.previous is not None: starts.insert(0,self.previous)
        for i in angles: starts.append(positions[i]+anchors[i].rotation()@bearing(observations[i].az,observations[i].el)*min(5,np.linalg.norm(hi-lo)/3))
        if p.mode=='tdoa_4':
            # Four receivers can yield two physical 3D roots. Seed both analytic
            # roots; workspace bounds and the ambiguity check determine validity.
            reference=positions[master.id]
            b=2*np.vstack([positions[i]-reference for i in ids])
            delta=np.array([dr[i] for i in ids])
            u=np.linalg.solve(b,np.array([np.dot(positions[i],positions[i])-np.dot(reference,reference)-dr[i]**2 for i in ids]))
            v=np.linalg.solve(b,-2*delta);w=u-reference
            quadratic=[np.dot(v,v)-1,2*np.dot(v,w),np.dot(w,w)]
            roots=np.roots(quadratic if abs(quadratic[0])>1e-10 else quadratic[1:])
            for root in roots:
                if abs(root.imag)<1e-7 and root.real>=0 and np.all(root.real+delta>=0):starts.append(u+v*root.real)
            # Additional bounded starts handle noisy, near-boundary data.
            from itertools import product
            starts.extend(lo+(hi-lo)*np.array(f) for f in product((.15,.5,.85),repeat=3))
        candidates=[]
        for start in starts:
            fit=least_squares(residual,np.clip(start,lo+1e-6,hi-1e-6),bounds=(lo,hi),loss='huber',f_scale=1.5,max_nfev=150)
            if fit.success: candidates.append(fit)
        if not candidates: raise ValueError('Solver did not converge')
        candidates.sort(key=lambda f:float(np.sum(residual(f.x)**2))); fit=candidates[0]
        if np.linalg.matrix_rank(fit.jac)<3 or np.linalg.cond(fit.jac)>1e4: raise ValueError('3D geometry is poorly conditioned')
        rms=float(np.sqrt(np.mean(residual(fit.x)**2)))
        if rms>3: raise ValueError('Measurements disagree / high residual')
        for other in candidates[1:]:
            if np.linalg.norm(other.x-fit.x)>.5 and np.sum(residual(other.x)**2)-np.sum(residual(fit.x)**2)<1: raise ValueError('Ambiguous 3D fix')
        covariance=np.linalg.inv(fit.jac.T@fit.jac)*max(1,rms**2)
        h95=2.448*math.sqrt(max(np.linalg.eigvalsh(covariance[:2,:2])))
        z95=1.96*math.sqrt(covariance[2,2])
        if h95>p.max_horizontal_uncertainty_m or z95>p.max_z_uncertainty_m: raise ValueError('Fix uncertainty exceeds threshold')
        self.previous=fit.x.copy()
        tdoa_rms=float(np.sqrt(np.mean([(np.linalg.norm(fit.x-positions[i])-np.linalg.norm(fit.x-positions[master.id])-dr[i])**2 for i in ids])))
        return {'x_m':float(fit.x[0]),'y_m':float(fit.x[1]),'z_m':float(fit.x[2]),'accuracy_m':h95,'z_uncertainty_m':z95,'residual':tdoa_rms,'num_anchors_used':len(p.anchors),'normalized_rms':rms,'aoa_anchors_used':angles}

def calibrate_rotation(anchor,rows):
    if len(rows)<3: raise ValueError('Use at least 3 non-collinear reference directions')
    if anchor.position is None: raise ValueError('Survey anchor position first')
    world=np.array([np.asarray(r['position'],float)-anchor.position for r in rows]);
    norms=np.linalg.norm(world,axis=1)
    if np.any(norms<.1): raise ValueError('Reference tag too close to anchor')
    world/=norms[:,None]
    local=np.array([bearing(r['az'],r['el']) for r in rows])
    if np.linalg.matrix_rank(local)<2: raise ValueError('Reference directions do not constrain orientation')
    rotation,rssd=Rotation.align_vectors(world,local)
    roll,pitch,yaw=rotation.as_euler('xyz',degrees=True)
    return {'yaw':float(yaw),'pitch':float(pitch),'roll':float(roll),'rms_direction':float(rssd/math.sqrt(len(rows)))}
