"""Continue a real stationary-origin capture across powered anchor subsets.

Use --previous only when the Tag and all antenna positions have stayed fixed.
No Flash, cloud traffic, geometry fabrication or quality-gate changes.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v8'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.survey_tag import UsbSurveyTag
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_geometry import estimate_range
from uwb_board_programmer.ble_controller import run_ble

async def capture(port,serial_number,folder,previous,seconds=5):
    if not 1<=seconds<=20:raise ValueError('Capture duration must be 1..20 seconds within the radio lease')
    profile=Profile.for_mode('tdoa_4');bindings=survey_bindings(profile)
    previous=previous or {}
    if previous:
        hello=previous.get('tag_hello',{})
        if (previous.get('simulated') is not False or previous.get('known_position')!=[0.,0.,0.] or
            hello.get('model')!='Type2DK' or hello.get('mac')!=profile.tag_mac or
            not set(previous.get('ranges',{})).issubset({b.anchor_id for b in bindings})):
            raise ValueError('Previous report is not a compatible real stationary-origin capture')
    tag=UsbSurveyTag(port,serial_number,profile.tag_mac);await asyncio.to_thread(tag.open)
    ranges=dict(previous.get('ranges',{}));captures=list(previous.get('captures',[]))
    errors=dict(previous.get('errors',{}));quality=dict(previous.get('quality',{}));info=dict(previous.get('board_info',{}))
    reused=list(ranges)
    try:
        async with SurveyNetwork(bindings,lambda line:print(line,flush=True),allow_partial=True) as network:
            info.update(network.info)
            for aid in network.clients:
                if aid in ranges:
                    print('Retained stationary-origin range: '+aid,flush=True);continue
                began=datetime.now(timezone.utc).isoformat()
                value=await network.measure_tag(aid,tag,seconds)
                value.update(started_utc=began,finished_utc=datetime.now(timezone.utc).isoformat(),capture_seconds=seconds)
                save_new(folder,'tag-range',value);captures.append(value)
                if not network.last_restore_acknowledged:raise ValueError('Standalone restoration not acknowledged')
                rows=value['records']
                quality[aid]=dict(samples=len(rows),successful=sum(r['status']==0 for r in rows),
                                  los=sum(r['status']==0 and not r['nlos'] for r in rows),
                                  nlos=sum(r['status']==0 and r['nlos'] for r in rows))
                try:ranges[aid]=estimate_range(rows);errors.pop(aid,None)
                except ValueError as error:errors[aid]=str(error)
                print(json.dumps(dict(anchor=aid,quality=quality[aid],accepted=ranges.get(aid),error=errors.get(aid))),flush=True)
        missing=[a.id for a in profile.anchors if a.id not in ranges]
        return dict(known_position=[0.,0.,0.],complete=not missing,ranges=ranges,captures=captures,
                    errors=errors,missing=missing,tag_hello=tag.hello,board_info=info,quality=quality,
                    reused_anchor_ranges=reused,capture_seconds=seconds,capture_purpose='link-diagnostics-only',
                    survey_geometry_verified=False,restore_acknowledged=True,simulated=False,cloud_connected=False)
    finally:tag.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True)
    parser.add_argument('--previous',type=Path);parser.add_argument('--seconds',type=float,default=5);args=parser.parse_args()
    previous=json.loads(args.previous.read_text(encoding='utf8')) if args.previous else None
    folder=ROOT/'verification'/('auto-survey-tag-subsets-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(args.port,args.serial,folder,previous,args.seconds))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    if args.previous:value['previous_report']=str(args.previous.resolve())
    report=folder/'report.json'
    with report.open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(report),ranges=value.get('ranges'),missing=value.get('missing'),quality=value.get('quality'),error=value.get('error'))),flush=True)
