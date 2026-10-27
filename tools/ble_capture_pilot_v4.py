"""Read-only real BLE pilot capture. Does not flash, control radios, or publish.

Example: python tools/ble_capture_pilot_v1.py --anchor A1,0200000000000001,master
The experimental firmware is required; stock/2.0.1 firmware has no such service.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.coinit_flags = 0
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app/ble_prototype/v1'))
from uwb_ble_receiver_v4 import Binding, Central


async def main(args):
    bindings = [Binding(*value.split(',')) for value in args.anchor]
    folder = ROOT/'verification'/('ble-capture-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(exist_ok=False)
    counts = {}
    with (folder/'events.jsonl').open('x', encoding='utf8') as output:
        def emit(aid, kind, data):
            key = aid+'/'+kind
            counts[key] = counts.get(key, 0)+1
            output.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),
                                         anchor_id=aid, kind=kind, data=data))+'\n')
            output.flush()
            if kind not in ('raw_ble', 'observation'):
                print(aid, kind, json.dumps(data), flush=True)
        central = Central(bindings, emit)
        task = asyncio.create_task(central.run())
        timer = asyncio.create_task(asyncio.sleep(args.seconds))
        try:
            await asyncio.wait([task, timer], return_when=asyncio.FIRST_COMPLETED)
        finally:
            central.stop.set()
            timer.cancel()
            await task
    with (folder/'summary.json').open('x', encoding='utf8') as output:
        json.dump(dict(duration_limit_s=args.seconds, counts=counts,
                       radio_control_writes=0, cloud_messages_sent=0), output, indent=2)
    print('CAPTURE', folder, json.dumps(counts), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anchor', action='append', required=True, metavar='ID,UWB_MAC,ROLE')
    parser.add_argument('--seconds', type=float, default=20)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('Capture duration must be 1..3600 seconds')
    asyncio.run(main(args))
