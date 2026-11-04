"""Passively record a USB-powered Tag UART; no writes, ROM queries or reset."""
from datetime import datetime,timezone
from pathlib import Path
import argparse
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app/revisions/v10'))
from uwb_board_programmer.standalone_flashing import _identity
if __name__=='__main__':
    import serial
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True)
    parser.add_argument('--seconds',type=int,default=150);args=parser.parse_args()
    if not 1<=args.seconds<=180:parser.error('Bounded passive capture only')
    _identity(args.port,args.serial)
    folder=ROOT/'verification'/('tag-usb-console-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    handle=serial.Serial(port=None,baudrate=3000000,timeout=.1);handle.port=args.port;handle.rts=False;handle.dtr=False
    count=0
    with handle,(folder/'uart.bin').open('xb') as out:
        print(json.dumps(dict(recording=True,port=args.port,folder=str(folder))),flush=True)
        end=time.monotonic()+args.seconds
        while time.monotonic()<end:
            raw=handle.read(min(handle.in_waiting or 1,4096));out.write(raw);count+=len(raw)
    with (folder/'report.json').open('x',encoding='utf8') as out:json.dump(dict(port=args.port,bytes=count,writes=0,reset_requested=False),out,indent=2)
    print(json.dumps(dict(report=str(folder/'report.json'),bytes=count)),flush=True)
