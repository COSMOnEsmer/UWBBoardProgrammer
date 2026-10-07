import json, math
from .models import Observation

def parse_line(line, anchor_id):
    text = line.decode('utf-8',errors='replace').strip() if isinstance(line,bytes) else line.strip()
    if not text.startswith('{'): return None
    d=json.loads(text)
    if d.get('v')!=1: raise ValueError('Unsupported firmware telemetry version')
    if d.get('kind')!='rx': return d
    def integer(key):
        value=d[key]
        if isinstance(value,float) or isinstance(value,bool): raise ValueError('Raw counters must be exact integers/strings')
        return int(value)
    def angle(key):
        value=d.get(key)
        if value is None: return None
        value=float(value)
        if not math.isfinite(value) or abs(value)>180: raise ValueError('Invalid AoA')
        return value
    bits=int(d.get('timestamp_bits',40))
    if bits not in (40,64): raise ValueError('Timestamp width must be 40 or 64 bits')
    rx=int(d['rx_timestamp_hex'],16) if 'rx_timestamp_hex' in d else integer('rx_timestamp_raw')
    tx=int(d['tx_timestamp_hex'],16) if d.get('tx_timestamp_hex') is not None else (integer('tx_timestamp_raw') if d.get('tx_timestamp_raw') is not None else None)
    tx_bits=int(d.get('tx_timestamp_bits',64 if tx is not None else 0))
    if tx_bits not in (0,40,64) or (tx is not None and tx_bits==0): raise ValueError('Invalid TX timestamp width')
    if tx is not None and not 0<=tx<(1<<tx_bits): raise ValueError('TX outside timestamp width')
    frame=d.get('frame_type')
    if frame not in ('SYNC','BLINK'): raise ValueError('Unknown UWB frame type')
    if not 0<=rx<(1<<bits) or (tx is not None and not 0<=tx<(1<<64)): raise ValueError('Timestamp outside width')
    return Observation(anchor_id,d['peer_mac'].upper(),frame,integer('frame_number'),rx,tx,bits,angle('azimuth_deg'),angle('elevation_deg'),int(d.get('az_fom',0)),int(d.get('el_fom',0)),bool(d.get('nlos',False)),str(d.get('boot','unknown')),int(d.get('status',0)),tx_bits=tx_bits)

class Counter:
    def __init__(self): self.last=None; self.bits=None
    def unwrap(self, raw, bits):
        if self.bits is not None and self.bits!=bits: raise ValueError('Timestamp width changed; reset clock domain')
        self.bits=bits
        if self.last is None: value=raw
        else:
            modulus=1<<bits; value=raw+((self.last-raw+modulus//2)//modulus)*modulus
        if self.last is None or value>self.last: self.last=value
        return value
