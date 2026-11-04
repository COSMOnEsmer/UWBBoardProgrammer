"""Read-only RF check after calibration restoration; never opens Tag COM."""
import asyncio
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v10'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.ble_transport import Central
from uwb_board_programmer.ble_controller import run_ble

async def capture(folder):
    profile=Profile.for_mode('tdoa_4');counts=Counter();errors=[];info={}
    with (folder/'events.jsonl').open('x',encoding='utf8') as out:
        def emit(aid,kind,data):
            if kind=='raw_ble':return
            out.write(json.dumps(dict(anchor=aid,kind=kind,data=data))+'\n');out.flush()
            if kind=='connected':info[aid]=data
            if kind=='error':errors.append(dict(anchor=aid,**data))
            if kind=='observation' and data.get('status')==0:
                if data.get('frame_type')=='SYNC':counts[aid+' SYNC']+=1
                elif data.get('peer_mac')==profile.tag_mac:counts[aid+' Tag BLINK']+=1
        central=Central(survey_bindings(profile),emit,scan_mode='active');task=asyncio.create_task(central.run())
        try:await asyncio.sleep(40)
        finally:central.stop.set();await task
    return dict(counts=dict(counts),board_info=info,errors=errors,simulated=False,usb_opened=False,cloud_connected=False)

if __name__=='__main__':
    folder=ROOT/'verification'/('post-survey-blink-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(folder))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    with (folder/'report.json').open('x',encoding='utf8') as out:json.dump(value,out,indent=2)
    print(json.dumps(dict(report=str(folder/'report.json'),**value)),flush=True)
