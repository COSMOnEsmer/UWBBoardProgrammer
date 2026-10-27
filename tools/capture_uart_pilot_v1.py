"""Passively record one identified EVK; never reset or send radio commands."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

import serial
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--expected-usb-serial', required=True)
    parser.add_argument('--seconds', type=float, default=60)
    args=parser.parse_args()
    if not 1<=args.seconds<=3600:parser.error('Duration must be 1..3600 seconds')
    found=[p for p in list_ports.comports() if p.device.upper()==args.port.upper()]
    if len(found)!=1 or found[0].serial_number!=args.expected_usb_serial or (found[0].vid,found[0].pid)!=(0x0403,0x6015):
        raise ValueError('Expected physical Murata USB interface not present')
    folder=ROOT/'verification'/('uart-capture-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(exist_ok=False)
    handle=serial.Serial(port=None, baudrate=3_000_000, timeout=.1)
    handle.port=args.port;handle.rts=False;handle.dtr=False
    counts={};pending=bytearray()
    with (folder/'uart.bin').open('xb') as raw, (folder/'decoded.jsonl').open('x',encoding='utf8') as decoded, handle:
        deadline=time.monotonic()+args.seconds
        while time.monotonic()<deadline:
            chunk=handle.read(min(handle.in_waiting or 1,4096))
            raw.write(chunk);pending.extend(chunk)
            while b'\n' in pending:
                line,_,pending=pending.partition(b'\n')
                line=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',line)
                begin=line.find(b'{"v":1,')
                if begin<0:continue
                try:message=json.JSONDecoder().raw_decode(line[begin:].decode('utf8'))[0]
                except (ValueError,UnicodeError):continue
                kind=message.get('kind','unknown');counts[kind]=counts.get(kind,0)+1
                decoded.write(json.dumps(message)+'\n');decoded.flush()
            if len(pending)>65536:raise ValueError('Unbounded UART line rejected')
    report=dict(port=args.port,seconds=args.seconds,counts=counts,commands_sent=0,radio_resets=0)
    with (folder/'summary.json').open('x',encoding='utf8') as output:json.dump(report,output,indent=2)
    print(json.dumps(dict(folder=str(folder),**report)))


if __name__=='__main__':main()
