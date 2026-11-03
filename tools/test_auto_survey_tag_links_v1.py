"""Real Tag link-quality diagnostic; retain all raw samples and no invented XYZ."""
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

async def capture(port,serial_number,folder):
    profile=Profile.for_mode('tdoa_4');tag=UsbSurveyTag(port,serial_number,profile.tag_mac)
    await asyncio.to_thread(tag.open)
    ranges={};captures=[];errors={};quality={}
    try:
        async with SurveyNetwork(survey_bindings(profile),lambda line:print(line,flush=True),allow_partial=True) as network:
            for aid in network.clients:
                value=await network.measure_tag(aid,tag,5);save_new(folder,'tag-range',value);captures.append(value)
                if not network.last_restore_acknowledged:raise ValueError('Standalone restoration not acknowledged')
                rows=value['records']
                quality[aid]=dict(samples=len(rows),successful=sum(r['status']==0 for r in rows),
                                  los=sum(r['status']==0 and not r['nlos'] for r in rows),
                                  nlos=sum(r['status']==0 and r['nlos'] for r in rows))
                try:ranges[aid]=estimate_range(rows)
                except ValueError as error:errors[aid]=str(error)
                print(json.dumps(dict(anchor=aid,quality=quality[aid],accepted=ranges.get(aid),error=errors.get(aid))),flush=True)
            info=dict(network.info)
        missing=[a.id for a in profile.anchors if a.id not in ranges]
        return dict(known_position=[0.,0.,0.],complete=not missing,ranges=ranges,captures=captures,
                    errors=errors,missing=missing,tag_hello=tag.hello,board_info=info,quality=quality,
                    restore_acknowledged=True,simulated=False,cloud_connected=False)
    finally:tag.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True);args=parser.parse_args()
    folder=ROOT/'verification'/('auto-survey-tag-links-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(args.port,args.serial,folder))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    report=folder/'report.json';report.write_text(json.dumps(value,indent=2),encoding='utf8')
    print(json.dumps(dict(report=str(report),ranges=value.get('ranges'),missing=value.get('missing'),quality=value.get('quality'),error=value.get('error'))),flush=True)
