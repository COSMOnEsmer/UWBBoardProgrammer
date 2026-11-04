"""Diagnose peer-order behavior while Tag remains on battery and one BLE epoch."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v10'),str(ROOT/'app/battery_calibration/v1'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_geometry import estimate_range
from uwb_board_programmer.ble_controller import run_ble
from uwb_battery_calibration.ble_tag import BleSurveyTag

class SettledTag(BleSurveyTag):
    def __init__(self,*args,hold_ms=0,**kwargs):
        super().__init__(*args,**kwargs);self.hold_ms=hold_ms
    async def set_mode(self,mode,**kwargs):
        if mode>=2 and self.hold_ms:
            import secrets
            await super().set_mode(1,request=secrets.randbelow(0xfffffffe)+1,lease_ms=30000)
            self.log('Tag hold acknowledged; settling '+str(self.hold_ms)+' ms')
            await asyncio.sleep(self.hold_ms/1000)
        return await super().set_mode(mode,**kwargs)

async def capture(folder,order,seconds,hold_ms):
    profile=Profile.for_mode('tdoa_4');bindings=survey_bindings(profile);results=[]
    async with SettledTag(profile.tag_mac,lambda line:print(line,flush=True),hold_ms=hold_ms) as tag:
        tag_snapshot=tag.info
        for suffix in order:
            target=next(b for b in bindings if b.anchor_id.endswith(suffix))
            selected=[b for b in bindings if b.role=='master' or b.anchor_id==target.anchor_id]
            print('Sequence target '+target.anchor_id,flush=True)
            async with SurveyNetwork(selected,lambda line:print(line,flush=True)) as network:
                value=await network.measure_tag(target.anchor_id,tag,seconds)
                if not network.last_restore_acknowledged:raise ValueError('Anchor restoration unacknowledged')
                record_file=save_new(folder,'pair',value)
            try:estimate=estimate_range(value['records']);quality_error=None
            except ValueError as error:estimate=None;quality_error=str(error)
            row=dict(anchor=target.anchor_id,status_counts=dict(Counter(r['status'] for r in value['records'])),
                     los=sum(r['status']==0 and not r['nlos'] for r in value['records']),
                     nlos=sum(r['status']==0 and r['nlos'] for r in value['records']),
                     estimate=estimate,quality_error=quality_error,raw_report=str(record_file))
            results.append(row);save_new(folder,'completed-pair',row);print(json.dumps(row),flush=True)
    return dict(tag_info=tag_snapshot,results=results,hold_ms=hold_ms,capture_seconds=seconds,all_restores_acknowledged=True,usb_opened=False,
                simulated=False,xyz_computed=False,cloud_connected=False,
                note='Operator confirmed stationary Tag/anchors and CR2032. Diagnostic order only.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--order',nargs='+',choices=['A1','A2','A3','A4'],default=['A1','A2','A3','A4'])
    parser.add_argument('--seconds',type=int,default=20);parser.add_argument('--hold-ms',type=int,default=0);args=parser.parse_args()
    if not 5<=args.seconds<=20 or not 0<=args.hold_ms<=5000:parser.error('Duration/hold out of bounds')
    folder=ROOT/'verification'/('battery-peer-sequence-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(folder,args.order,args.seconds,args.hold_ms))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    with (folder/'report.json').open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(folder/'report.json'),results=value.get('results'),error=value.get('error'))),flush=True)
