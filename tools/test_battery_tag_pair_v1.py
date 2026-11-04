"""Experimental real GATT Tag control + anchor TWR. Does not open COM or Flash."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/battery_calibration/v1'),str(ROOT/'app/revisions/v9'),
              str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_geometry import estimate_range
from uwb_board_programmer.ble_controller import run_ble
from uwb_battery_calibration.ble_tag import BleSurveyTag

async def capture(anchor,seconds,folder,power_source='unknown',require_master=False):
    profile=Profile.for_mode('tdoa_4');bindings=survey_bindings(profile)
    target=next(b for b in bindings if b.anchor_id.endswith(anchor))
    # At most three GATT links: Tag + master + selected slave. Other slaves only
    # receive UL radio frames; the master is held to silence its SYNC transmitter.
    selected=[b for b in bindings if b.role=='master' or b.anchor_id==target.anchor_id]
    async with BleSurveyTag(profile.tag_mac,lambda line:print(line,flush=True)) as tag:
        async with SurveyNetwork(selected,lambda line:print(line,flush=True),allow_partial=not require_master) as network:
            if target.anchor_id not in network.clients:raise ValueError('Selected anchor is not advertising')
            value=await network.measure_tag(target.anchor_id,tag,seconds);save_new(folder,'tag-range',value)
            if not network.last_restore_acknowledged:raise ValueError('Anchor restoration not acknowledged')
            tag_snapshot=tag.info;boards=dict(network.info)
        try:estimate=estimate_range(value['records']);quality_error=None
        except ValueError as error:estimate=None;quality_error=str(error)
    return dict(tag_info=tag_snapshot,board_info=boards,capture=value,estimate=estimate,quality_error=quality_error,
                anchor_restore_acknowledged=True,tag_restore_acknowledged=True,usb_opened=False,simulated=False,
                power_source_reported=power_source,battery_power_source_confirmed_by_operator=power_source=='cr2032',
                battery_runtime_validated=False,cloud_connected=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--anchor',choices=['A1','A2','A3','A4'],default='A1')
    parser.add_argument('--seconds',type=int,default=20);parser.add_argument('--power-source',choices=['unknown','usb','cr2032'],default='unknown');parser.add_argument('--require-master',action='store_true');args=parser.parse_args()
    if not 5<=args.seconds<=20:parser.error('Capture must be 5..20 seconds')
    folder=ROOT/'verification'/('battery-tag-pair-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture(args.anchor,args.seconds,folder,args.power_source,args.require_master))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    report=folder/'report.json'
    with report.open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(report),estimate=value.get('estimate'),error=value.get('error'),quality_error=value.get('quality_error'))))
