"""Real BLE -> surveyed four-anchor TDoA -> session recording (no cloud writes).

Use runtime with Bleak, NumPy, and SciPy. Existing profile files are read only.
Rejects incomplete/coplanar geometry before opening any BLE connections.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
sys.coinit_flags = 0
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v4'), str(ROOT/'app/ble_prototype/v1')]
from uwb_board_programmer.models import Profile
from uwb_board_programmer.recording import Recorder
from uwb_ble_receiver_v4 import Central
from uwb_ble_pipeline_v2 import CorrelatedLivePipeline


async def main(args):
    profile=Profile.from_dict(json.loads(args.profile.read_text(encoding='utf8')))
    profile.validate(require_ports=False, require_aoa=False)
    recorder=Recorder(ROOT, profile)
    try:
        def fix(value):
            print(json.dumps(dict(kind='fix', **value)), flush=True)
        pipeline=CorrelatedLivePipeline(profile, recorder.write, fix)
        central=Central(pipeline.bindings(), pipeline.event)
        run=asyncio.create_task(central.run())
        try:
            for _ in range(args.seconds):
                if run.done():
                    await run
                    break
                await asyncio.sleep(1)
                pipeline.engine.expire()
                print(json.dumps(pipeline.snapshot()), flush=True)
        finally:
            central.stop.set()
            await run
    finally:
        recorder.close()
    print('SESSION', recorder.path, flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=60)
    args=parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('Duration must be 1..3600 seconds')
    asyncio.run(main(args))
