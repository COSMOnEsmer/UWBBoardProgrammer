from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import json, math, uuid
import numpy as np
from scipy.spatial.transform import Rotation

TICK_S = 1.0 / (499_200_000 * 128)
C_M_S = 299_792_458.0
SITE_ID = 'ca29a1a6-76c5-48ed-9c9a-e4615fcb4d09'
FLOOR_ID = '58afbe99-a0a9-4fd2-ba69-4bf9acc96f6a'

def utc(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
def unique_path(folder, prefix, suffix):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    return folder / f'{prefix}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{uuid.uuid4().hex[:6]}{suffix}'
def save_new(folder, prefix, data):
    p = unique_path(folder, prefix, '.json')
    with p.open('x', encoding='utf-8') as out: json.dump(data, out, ensure_ascii=False, indent=2, allow_nan=False)
    return p

@dataclass
class Anchor:
    id: str
    mac: str
    role: str
    port: str = ''
    position: list | None = None
    yaw: float = 0
    pitch: float = 0
    roll: float = 0
    rx_bias_m: float = 0
    aoa_verified: bool = False
    def rotation(self): return Rotation.from_euler('xyz', [self.roll,self.pitch,self.yaw], degrees=True).as_matrix()

@dataclass
class Profile:
    name: str = 'KMUTNB - Murata hardware'
    site_id: str = SITE_ID
    floor_id: str = FLOOR_ID
    anchors: list = field(default_factory=lambda:[Anchor(f'KMUTNB-RF-A{i}', f'020000000000000{i}', 'master' if i == 1 else 'slave') for i in range(1,4)])
    tag_id: str = 'KMUTNB-RF-T1'
    tag_mac: str = '0200000000000101'
    tag_port: str = ''
    baud: int = 3_000_000
    blink_interval_ms: int = 1000
    bounds: list = field(default_factory=lambda:[[0,0,0],[40,16,5]])
    aoa_sigma_deg: float = 3.0
    tdoa_sigma_m: float = 0.30
    min_fom: int = 50
    max_z_uncertainty_m: float = 1.0
    max_horizontal_uncertainty_m: float = 2.0
    mode: str = 'hybrid_3'
    @classmethod
    def for_mode(cls, mode):
        if mode not in ('hybrid_3', 'tdoa_4'): raise ValueError('Unknown positioning mode')
        p = cls(mode=mode)
        if mode == 'tdoa_4': p.anchors.append(Anchor('KMUTNB-RF-A4','0200000000000004','slave'))
        return p
    @property
    def anchor_count(self): return len(self.anchors)
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data.setdefault('mode', 'tdoa_4' if len(data['anchors']) == 4 else 'hybrid_3')
        data['anchors'] = [Anchor(**a) for a in data['anchors']]
        return cls(**data)
    def validate(self, require_ports=False, require_aoa=True):
        if self.mode not in ('hybrid_3','tdoa_4'): raise ValueError('Unknown positioning mode')
        count=3 if self.mode=='hybrid_3' else 4
        if len(self.anchors)!=count or sum(a.role=='master' for a in self.anchors)!=1:
            raise ValueError(f'The selected mode requires {count} anchors with exactly one master.')
        if len({a.id for a in self.anchors})!=count or len({a.mac.upper() for a in self.anchors})!=count:
            raise ValueError('Anchor IDs and MAC addresses must be unique.')
        ports=[a.port.upper() for a in self.anchors]
        if require_ports and (not all(ports) or len(set(ports))!=count):
            raise ValueError('Assign a different COM port to every anchor.')
        for a in self.anchors:
            if len(bytes.fromhex(a.mac))!=8: raise ValueError('MAC addresses must contain 8 bytes (16 hexadecimal digits).')
            if a.position is None or len(a.position)!=3 or not all(math.isfinite(float(v)) for v in a.position):
                raise ValueError(f'Enter the surveyed coordinates for {a.id}')
            if not all(math.isfinite(v) for v in [a.yaw,a.pitch,a.roll,a.rx_bias_m]): raise ValueError('Enter valid orientation and RX bias values.')
        xyz=np.asarray([a.position for a in self.anchors],float)
        rank=np.linalg.matrix_rank(xyz[1:]-xyz[0],tol=1e-5)
        if self.mode=='tdoa_4' and rank<3: raise ValueError('Four-anchor 3D TDoA requires non-coplanar anchors. Install at least one anchor at a different height.')
        if rank<2: raise ValueError('The anchors must not lie on a straight line.')
        if not 100<=self.blink_interval_ms<=10000: raise ValueError('BLINK interval 100..10000 ms')
        if any(v<=0 or not math.isfinite(v) for v in [self.aoa_sigma_deg,self.tdoa_sigma_m,self.max_z_uncertainty_m,self.max_horizontal_uncertainty_m]): raise ValueError('Noise / uncertainty thresholds must be positive')
        if any(a.role not in ('master','slave') for a in self.anchors): raise ValueError('Invalid anchor role')
        if self.tag_mac.upper() in {a.mac.upper() for a in self.anchors}: raise ValueError('Tag and anchor MAC must differ')
        if self.mode=='hybrid_3' and require_aoa and not any(a.aoa_verified for a in self.anchors):
            raise ValueError('Verify the azimuth and elevation axes of at least one anchor before starting acquisition.')
        lo,hi=np.asarray(self.bounds,float)
        if not np.all(np.isfinite([lo,hi])) or not np.all(lo<hi): raise ValueError('Enter valid workspace bounds.')
        if not self.site_id or not self.floor_id or not self.tag_id: raise ValueError('Site, floor and tag IDs are required.')
        if len(bytes.fromhex(self.tag_mac))!=8: raise ValueError('Enter a valid tag MAC address.')

@dataclass
class Observation:
    anchor_id: str
    peer_mac: str
    frame_type: str
    frame_number: int
    rx: int
    tx: int | None
    bits: int
    az: float | None
    el: float | None
    az_fom: int
    el_fom: int
    nlos: bool
    boot: str
    status: int = 0
    received_utc: str = field(default_factory=utc)
    tx_bits: int = 0
    def raw_payload(self, profile):
        d={'site_id':profile.site_id,'floor_id':profile.floor_id,'anchor_id':self.anchor_id,'tag_id':profile.tag_id if self.frame_type=='BLINK' else None,'frame_type':self.frame_type,'frame_number':str(self.frame_number),'rx_timestamp_raw':str(self.rx),'time':self.received_utc,'nlos':bool(self.nlos)}
        if self.frame_type=='SYNC' and self.tx is not None: d['tx_timestamp_raw']=str(self.tx)
        if self.az is not None: d['aoa_azimuth_deg']=self.az; d['aoa_azimuth_fom']=self.az_fom
        if self.el is not None: d['aoa_elevation_deg']=self.el; d['aoa_elevation_fom']=self.el_fom
        return d
