"""Real 1.5.1 diagnostics: retain both Anchor ranges and Tag RF counters."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v11'),str(ROOT/'app/battery_calibration/v2'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_geometry import estimate_range
from uwb_board_programmer.ble_controller import run_ble
from uwb_battery_calibration.ble_tag import BleSurveyTag

async def capture(folder,args):
    profile=Profile.for_mode('tdoa_4');bindings=survey_bindings(profile);results=[]
    with (folder/'transcript.txt').open('x',encoding='utf8') as transcript:
        def log(line):transcript.write(line+'\n');transcript.flush();print(line,flush=True)
        async with BleSurveyTag(profile.tag_mac,log) as tag:
            if tag.info['firmware']!='1.5.1-pilot':raise ValueError('Expected identified recovery candidate, not the released 1.5.0 image')
            snapshot=dict(tag.info);save_new(folder,'tag-connected',snapshot)
            if args.hold_ms:
                await tag.set_mode(1,request=secrets.randbelow(0xfffffffe)+1,lease_ms=30000)
                await asyncio.sleep(args.hold_ms/1000)
                await tag.set_mode(0,request=secrets.randbelow(0xfffffffe)+1)
                save_new(folder,'after-hold',await tag.diagnostic())
            for suffix in args.order:
                target=next(b for b in bindings if b.anchor_id.endswith(suffix))
                before=await tag.diagnostic()
                async with SurveyNetwork([b for b in bindings if b.role=='master' or b.anchor_id==target.anchor_id],log,
                                         tag_initiator_first=args.initiator_first) as network:
                    value=await network.measure_tag(target.anchor_id,tag,args.seconds)
                    if not network.last_restore_acknowledged:raise ValueError('Anchor restoration unacknowledged')
                after=await tag.diagnostic();raw=save_new(folder,'pair',value)
                try:estimate=estimate_range(value['records']);error=None
                except ValueError as failure:estimate=None;error=str(failure)
                row=dict(anchor=target.anchor_id,tag_before=before,tag_after=after,
                         status_counts=dict(Counter(r['status'] for r in value['records'])),
                         los=sum(r['status']==0 and not r['nlos'] for r in value['records']),
                         nlos=sum(r['status']==0 and r['nlos'] for r in value['records']),
                         estimate=estimate,quality_error=error,raw_report=str(raw))
                results.append(row);save_new(folder,'completed-pair',row);log(json.dumps(row))
    return dict(tag_info=snapshot,results=results,usb_opened=False,simulated=False,
                hold_ms=args.hold_ms,capture_seconds=args.seconds,power_source_reported=args.power_source,
                startup_order='anchor-first' if args.initiator_first else 'tag-first',
                all_restores_acknowledged=True,xyz_computed=False,cloud_connected=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--order',nargs='+',choices=['A1','A2','A3','A4'],default=['A4','A1','A2','A3','A4'])
    parser.add_argument('--seconds',type=int,default=15);parser.add_argument('--hold-ms',type=int,default=0)
    parser.add_argument('--initiator-first',action='store_true')
    parser.add_argument('--power-source',choices=['unknown','usb','cr2032'],default='unknown');args=parser.parse_args()
    if not 5<=args.seconds<=20 or not 0<=args.hold_ms<=5000:parser.error('Duration/hold out of bounds')
    folder=ROOT/'verification'/('battery-recovery-sequence-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(folder,args))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    with (folder/'report.json').open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(folder/'report.json'),results=value.get('results'),error=value.get('error'))),flush=True)
