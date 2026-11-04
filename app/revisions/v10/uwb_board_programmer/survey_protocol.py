"""Auto Survey v1. Separate from the existing 64-byte TDoA wire protocol."""
import struct
import uuid
import zlib

def _uuid(kind):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/COSMOnEsmer/UWBBoardProgrammer/ble/v1/survey/'+kind))

CONTROL_UUID=_uuid('control')
STATUS_UUID=_uuid('status')
TWR_UUID=_uuid('data')
COMMAND=struct.Struct('<BBI8sIH')
STATUS=struct.Struct('<BBHII8sI')
TWR=struct.Struct('<BBIHIBBHI')

def command(mode,request,peer='0000000000000000',session=0,lease_ms=0):
    mac=bytes.fromhex(peer)
    if len(mac)!=8 or mode not in (0,1,2,3) or not 0<request<=0xffffffff:raise ValueError('Survey command identity')
    if mode and not 1000<=lease_ms<=30000:raise ValueError('Survey command lease must be 1..30 seconds')
    if mode>=2 and (not 0<session<=0xffffffff or not any(mac)):raise ValueError('TWR peer/session required')
    return COMMAND.pack(1,mode,request,mac,session,lease_ms)

def _checked(raw,size):
    raw=bytes(raw)
    if len(raw)!=size:raise ValueError('Survey record length')
    if zlib.crc32(raw[:-4])&0xffffffff!=int.from_bytes(raw[-4:],'little'):raise ValueError('Survey record CRC')
    return raw

def status(raw):
    version,mode,code,request,session,peer,crc=STATUS.unpack(_checked(raw,STATUS.size))
    if version!=1 or mode not in (0,1,2,3):raise ValueError('Survey status protocol')
    return dict(mode=mode,status=code,request=request,session=session,peer=peer.hex().upper())

def ranging(raw,*,request,session):
    version,kind,req,index,millimetres,code,nlos,session_low,crc=TWR.unpack(_checked(raw,TWR.size))
    if version!=1 or kind!=0x54 or nlos not in (0,1):raise ValueError('Survey ranging protocol')
    if req!=request or session_low!=(session&0xffff):raise ValueError('Old or unrelated survey request')
    if not index:raise ValueError('Survey sample index')
    return dict(request=req,index=index,distance_m=millimetres/1000.,status=code,nlos=bool(nlos))
