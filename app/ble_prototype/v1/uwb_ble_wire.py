"""Pilot wire contract; not enabled in the released 2.0.1 application."""
from collections import OrderedDict,deque
import struct,time,uuid,zlib
SERVICE_UUID=str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/COSMOnEsmer/UWBBoardProgrammer/ble/v1/service'))
INFO_UUID=str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/COSMOnEsmer/UWBBoardProgrammer/ble/v1/info'))
DATA_UUID=str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/COSMOnEsmer/UWBBoardProgrammer/ble/v1/data'))
WIRE=struct.Struct('<2sBBIIBBBBIBBBB8sQQhhBBBBII')
FRAGMENT=struct.Struct('<BBHBBH')
assert WIRE.size==64 and FRAGMENT.size==8

def encode(*,boot,sequence,role,rx_bits,tx_bits,frame_type,frame_number,
           status=0,message_control=0,peer_mac,rx,tx=0,az_q7=0,el_q7=0,
           az_fom=0,el_fom=0,nlos=0,dropped=0):
    mac=bytes.fromhex(peer_mac)
    if len(mac) not in (2,8):raise ValueError('MAC length')
    raw=WIRE.pack(b'UB',1,1,boot,sequence,role,rx_bits,tx_bits,frame_type,
        frame_number,status,message_control,len(mac),0,mac.ljust(8,b'\0'),rx,tx,
        az_q7,el_q7,az_fom,el_fom,nlos,0,dropped,0)
    raw=raw[:-4]+struct.pack('<I',zlib.crc32(raw[:-4])&0xffffffff)
    decode(raw)
    return raw

def decode(raw):
    if len(raw)!=WIRE.size:raise ValueError('Wire length')
    values=WIRE.unpack(raw)
    (magic,version,kind,boot,seq,role,rxb,txb,frame,number,status,control,
     mac_len,reserved,mac,rx,tx,az,el,azf,elf,nlos,reserved2,dropped,crc)=values
    if magic!=b'UB' or version!=1 or kind!=1:raise ValueError('Wire protocol')
    if reserved or reserved2 or mac_len not in (2,8):raise ValueError('Reserved/MAC field')
    if role not in (0,1) or frame not in (0,1):raise ValueError('Role/frame type')
    if rxb not in (40,64) or txb not in (0,40,64):raise ValueError('Timestamp width')
    if rx>=1<<rxb or (txb and tx>=1<<txb) or (not txb and tx):raise ValueError('Timestamp overflow')
    if mac[mac_len:]!=b'\0'*(8-mac_len):raise ValueError('MAC padding')
    if zlib.crc32(raw[:-4])&0xffffffff!=crc:raise ValueError('Wire CRC')
    return {'v':1,'kind':'rx','boot':f'{boot:08x}','transport_sequence':seq,
        'anchor_role':'master' if role else 'slave','peer_mac':mac[:mac_len].hex().upper(),
        'frame_type':'BLINK' if frame==0 else 'SYNC','frame_number':str(number),
        'status':status,'message_control':control,'timestamp_bits':rxb,
        'tx_timestamp_bits':txb,'rx_timestamp_hex':f'{rx:016x}',
        'tx_timestamp_hex':f'{tx:016x}' if txb else None,
        'azimuth_deg':None if az in (-32768,32767) else az/128,
        'elevation_deg':None if el in (-32768,32767) else el/128,
        'az_fom':azf if azf<=100 else 0,'el_fom':elf if elf<=100 else 0,
        'nlos':nlos,'dropped':dropped}

def fragments(raw,att_payload=20):
    record=decode(raw);chunk=att_payload-FRAGMENT.size
    if chunk<2:raise ValueError('ATT payload too small')
    count=(len(raw)+chunk-1)//chunk
    if count>32:raise ValueError('Too many fragments')
    return [FRAGMENT.pack(1,1,record['transport_sequence']&0xffff,i,count,len(raw))+
            raw[i*chunk:(i+1)*chunk] for i in range(count)]

class Reassembler:
    def __init__(self,*,ttl_s=1,max_pending=8):
        self.ttl=ttl_s;self.limit=max_pending;self.pending=OrderedDict();self.seen=deque(maxlen=256)
    def reset(self):self.pending.clear();self.seen.clear()
    def accept(self,data,now=None):
        now=time.monotonic() if now is None else now
        for key in list(self.pending):
            if now-self.pending[key]['born']>self.ttl:self.pending.pop(key)
        if len(data)<=FRAGMENT.size:raise ValueError('Fragment length')
        version,kind,seq,index,count,total=FRAGMENT.unpack(data[:FRAGMENT.size])
        if version!=1 or kind!=1 or not 1<=count<=32 or index>=count or total!=64:
            raise ValueError('Fragment header')
        payload=data[FRAGMENT.size:]
        if len(payload)>total:raise ValueError('Fragment overflow')
        if seq not in self.pending:
            if len(self.pending)>=self.limit:self.pending.popitem(last=False)
            self.pending[seq]={'born':now,'count':count,'total':total,'chunks':{}}
        group=self.pending[seq]
        if (group['count'],group['total'])!=(count,total):
            self.pending.pop(seq);raise ValueError('Conflicting fragment metadata')
        prior=group['chunks'].get(index)
        if prior is not None and prior!=payload:
            self.pending.pop(seq);raise ValueError('Conflicting duplicate fragment')
        group['chunks'][index]=payload
        if sum(map(len,group['chunks'].values()))>total:
            self.pending.pop(seq);raise ValueError('Reassembly overflow')
        if len(group['chunks'])!=count:return None
        self.pending.pop(seq)
        raw=b''.join(group['chunks'][i] for i in range(count));record=decode(raw)
        if record['transport_sequence']&0xffff!=seq:raise ValueError('Sequence mismatch')
        key=(record['boot'],record['transport_sequence'])
        if key in self.seen:return None
        self.seen.append(key);return record
