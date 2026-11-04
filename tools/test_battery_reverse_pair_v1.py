"""Diagnostic role reversal: battery Tag initiates, selected anchor responds."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v10'),str(ROOT/'app/battery_calibration/v1'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_protocol import ranging
from uwb_board_programmer.survey_geometry import estimate_range
from uwb_board_programmer.ble_controller import run_ble
from uwb_battery_calibration.ble_tag import BleSurveyTag

async def capture(anchor):
    profile=Profile.for_mode('tdoa_4');bindings=survey_bindings(profile)
    target=next(b for b in bindings if b.anchor_id.endswith(anchor))
    async with BleSurveyTag(profile.tag_mac,lambda line:print(line,flush=True)) as tag:
        async with SurveyNetwork([b for b in bindings if b.role=='master' or b.anchor_id==target.anchor_id],lambda line:print(line,flush=True)) as network:
            for aid in network.clients:await network.set_mode(aid,1,lease_ms=30000)
            while not network.queue.empty():network.queue.get_nowait()
            request=secrets.randbelow(0xfffffffe)+1;session=secrets.randbelow(0x7ffffffe)+1;records=[];seen=set()
            try:
                await network.set_mode(target.anchor_id,2,request=request,peer=tag.mac,session=session,lease_ms=30000)
                await tag.set_mode(3,request=request,peer=target.mac,session=session,lease_ms=30000)
                end=time.monotonic()+20
                while time.monotonic()<end:
                    try:received,aid,raw=await asyncio.wait_for(network.queue.get(),.25)
                    except TimeoutError:continue
                    if aid!=target.anchor_id or time.monotonic()-received>.5:continue
                    try:value=ranging(raw,request=request,session=session)
                    except ValueError:continue
                    if value['index'] not in seen:seen.add(value['index']);records.append(value)
            finally:
                try:await tag.set_mode(0,request=secrets.randbelow(0xfffffffe)+1)
                finally:restored=await network.restore()
        try:estimate=estimate_range(records);quality_error=None
        except ValueError as error:estimate=None;quality_error=str(error)
    return dict(records=records,estimate=estimate,quality_error=quality_error,anchor_restore_acknowledged=restored,
                tag_restore_acknowledged=True,tag_initiator=True,anchor=target.anchor_id,simulated=False,usb_opened=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--anchor',choices=['A1','A2','A3','A4'],default='A4');args=parser.parse_args()
    folder=ROOT/'verification'/('battery-role-reverse-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(args.anchor))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    with (folder/'report.json').open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(folder/'report.json'),estimate=value.get('estimate'),records=len(value.get('records',[])),error=value.get('error'),quality_error=value.get('quality_error'))),flush=True)
